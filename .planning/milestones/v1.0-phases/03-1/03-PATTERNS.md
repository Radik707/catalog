# Этап 3: Память правок — Карта паттернов

**Составлено:** 2026-06-07
**Файлов проанализировано:** 1 изменяемый (`scripts/upload.py`) + 1 опциональный новый (CLI-миграция)
**Аналоги найдены:** 5 / 5 (все ключевые куски логики имеют прямой образец в существующем коде)

> Назначение документа: показать планировщику, **с какого существующего кода копировать паттерны** для каждого нового куска логики этапа «Память правок». Все аналоги — в `scripts/upload.py` и `scripts/sheet_tool.py`. Новых интеграций (gspread, Service Account) не требуется — они уже настроены.

---

## Классификация файлов

| Файл (новое/изменяемое) | Роль | Поток данных | Ближайший аналог | Качество совпадения |
|--------------------------|------|--------------|------------------|---------------------|
| `scripts/upload.py` → новая функция `load_edit_memory()` (чтение вкладки «Правки») | data-access / loader | request-response (чтение листа через gspread) | `load_current_groups` (`upload.py:254-299`) | **точное** (тот же лист той же таблицы, тот же Service Account, тот же graceful-fallback `→ {}`) |
| `scripts/upload.py` → fallback при отсутствии вкладки | config-loader | file/sheet-I/O | `load_badges` / `load_category_map` / `load_photo_data` (`upload.py:52-89`, `398-450`) | **точное** (паттерн «нет источника → пустая структура, не падать») |
| `scripts/upload.py` → применение памяти поверх авто-данных (группа/фото/описание) | transform / merge | transform (override поверх авто-маппинга) | блок overrides в `load_photo_data` (`upload.py:437-447`) + `apply_group_mapping`/`apply_product_override` (`upload.py:347-373`) | **точное** (override владельца побеждает авто — D-06) |
| `scripts/upload.py` → ключ сопоставления правки и товара | utility | transform | `normalize_name` (`upload.py:213-215`) | **точное** (та же функция, повторно используется) |
| `scripts/upload.py` → точка интеграции в `main()` | orchestration | pipeline | `main()` блок маппинга групп/фото (`upload.py:676-701`) | **точное** (наложить память после `apply_group_mapping`, перед `products_to_rows`) |
| `scripts/upload.py` → определение «новый товар» (MEM-03, D-05) | utility / detection | transform | блок `new_names` для нового формата (`upload.py:681-698`) | **role-match** (та же идея «имя отсутствует в эталоне → новый», другой эталон: память вместо текущих групп) |
| (опц.) `scripts/migrate_overrides.py` — разовый перенос `PRODUCT_OVERRIDES` во вкладку (D-07) | CLI-tool / migration | batch sheet-write | `sheet_tool.py` (структура CLI + `open_spreadsheet` + `copy_sheet`) | **role-match** (тот же стиль одноразовой утилиты записи в лист) |
| Подушка безопасности вкладки «Правки» (бэкап) — при необходимости | safety / backup | sheet copy | `copy_sheet` + команды backup/rollback (`sheet_tool.py:68-110`) | **точное** (тот же механизм копирования листа в `_BACKUP`) |

---

## Назначения паттернов

### `load_edit_memory()` — чтение вкладки «Правки» (новая функция в `upload.py`)

**Роль:** data-access / loader · **Поток:** чтение листа Google через gspread + Service Account
**Аналог:** `load_current_groups` — `scripts/upload.py:254-299`

Скопировать ЦЕЛИКОМ скелет авторизации и graceful-fallback. Менять только имя листа (`"Товары"` → `"Правки"`), индексы колонок и форму возвращаемого словаря.

**Импорт gspread «лениво», fallback при отсутствии пакета** (`upload.py:260-274`):
```python
def load_current_groups() -> dict:
    """Прочитать текущий каталог (лист «Товары») → {норм_название: группа}."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        return {}
    creds_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "")
    if not creds_path:
        for d in (SCRIPT_DIR, PROJECT_ROOT):
            c = d / "credentials.json"
            if c.exists():
                creds_path = str(c)
                break
    sheets_id = os.environ.get("GOOGLE_SHEETS_ID", "")
    if not creds_path or not sheets_id:
        return {}
```

**Чтение листа + graceful-fallback при недоступности / отсутствии вкладки** (`upload.py:275-293`):
```python
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    try:
        creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        ss = gspread.authorize(creds).open_by_key(sheets_id)
        values = ss.worksheet("Товары").get_all_values()
    except Exception as e:  # noqa: BLE001
        log.warning("Не удалось прочитать текущие группы: %s", e)
        return {}
    if not values:
        return {}
    header = values[0]
    try:
        name_i = header.index("Наименование")
        grp_i = header.index("Группа")
    except ValueError:
        return {}
```

> **Важно для D-01/Discretion «вкладки ещё нет»:** `ss.worksheet("Правки")` бросает `gspread.exceptions.WorksheetNotFound`. Текущий аналог ловит широкий `except Exception → return {}`, что само по себе уже корректно покрывает отсутствие вкладки. Если планировщик захочет различать «вкладки нет» (норма, INFO) и «ошибка доступа» (WARNING) — добавить отдельный `except WorksheetNotFound: log.info(...); return {}` ПЕРЕД широким `except`. Образец точечного `WorksheetNotFound` — `sheet_tool.py:73,81` и `upload.py:597`.

**Сборка словаря по строкам листа** (`upload.py:294-299`) — аналог формы `{норм_имя: значение}`; для памяти ключом остаётся `normalize_name`, но значение — структура правки (тип + значение), а не одна строка:
```python
    mapping = {}
    for r in values[1:]:
        if len(r) > max(name_i, grp_i) and r[name_i] and r[grp_i]:
            mapping[normalize_name(r[name_i])] = r[grp_i]
    log.info("Загружено групп из текущего каталога: %d", len(mapping))
    return mapping
```

**Рекомендуемая форма возврата для памяти** (расширяемая под D-02/D-03 — типы `group`/`photo`/`description`, задел на `price`/`name`):
ключ — `normalize_name(name)`; значение — словарь типов правок, например
`{ "конфеты ромашка": {"group": "...", "photo": "akkond/500.jpg", "description": "..."} }`.
Это позволяет в точке интеграции наложить каждый тип отдельно (см. ниже).

---

### Применение памяти поверх авто-данных (override-merge)

**Роль:** transform / merge · **Поток:** override владельца побеждает авто-маппинг (D-06)
**Аналог:** блок ручных привязок в `load_photo_data` — `scripts/upload.py:437-447`

Это эталон правила D-06 «правка ВСЕГДА побеждает авто-маппинг». Ручные привязки `photo_overrides.json` накладываются ПОВЕРХ авто-маппинга `photo_map.json` точно так же, как память должна лечь поверх авто-данных:
```python
    # Ручные привязки перезаписывают авто-маппинг (description не перезаписывается)
    if overrides_path.exists():
        with open(overrides_path, "r", encoding="utf-8") as f:
            overrides: dict[str, str] = json.load(f)
        for product_name, file_key in overrides.items():
            if file_key in url_index:
                existing = name_to_data.get(product_name.lower(), {})
                name_to_data[product_name.lower()] = {
                    "url": url_index[file_key],
                    "description": existing.get("description", ""),
                }
        log.info("Загружено ручных привязок фото: %d", len(overrides))
```

**Аналог для override группы** — `apply_group_mapping` + `apply_product_override` (`upload.py:347-373`). Сейчас группа переопределяется зашитыми словарями; память должна заместить именно этот источник переопределений (D-07):
```python
def apply_group_mapping(products: list[dict], category_map: dict) -> list[dict]:
    """Добавить поле display_group на основе маппинга категорий и переопределений по товару."""
    ...
    for product in products:
        cat = product["source_category"]
        group = category_map.get(cat)
        if group is None:
            unmapped.add(cat)
            group = "Другое"

        override = apply_product_override(product["name"])  # ← заменяется/дополняется памятью
        if override is not None and override != group:
            group = override
            overridden += 1

        product["display_group"] = group
```

> **Перенос `PRODUCT_OVERRIDES` (D-07):** `apply_product_override` (`upload.py:331-344`) сейчас читает зашитые `PRODUCT_OVERRIDES` (`upload.py:304-322`, поиск по началу строки) и `PRODUCT_CONTAINS_OVERRIDES` (`upload.py:325-328`, поиск по подстроке). Память правок использует **точное совпадение нормализованного имени** (D-04), а старые словари — **частичное** (по префиксу/подстроке). Это семантическое отличие: планировщику решить, как мигрировать (раскрыть каждый префикс в конкретные имена товаров, либо сохранить поле «тип сопоставления» в строке правки). Образец частичного, регистронезависимого поиска для справки:
```python
def apply_product_override(name: str) -> str | None:
    name_lower = name.lower()
    for prefix, group in PRODUCT_OVERRIDES.items():
        if name_lower.startswith(prefix.lower()):
            return group
    for substring, group in PRODUCT_CONTAINS_OVERRIDES:
        if substring.lower() in name_lower:
            return group
    return None
```

---

### Ключ сопоставления правки с товаром (D-04)

**Роль:** utility · **Аналог:** `normalize_name` — `scripts/upload.py:213-215` (переиспользовать как есть, не дублировать):
```python
def normalize_name(name: str) -> str:
    """Нормализовать название для сопоставления (без хвостовой единицы, нижний регистр)."""
    return re.sub(r"\s+", " ", clean_new_name(name)).strip().lower()
```
Этой же функцией нормализуется ключ при чтении вкладки (`load_edit_memory`) и при поиске правки в точке интеграции — ключи гарантированно совпадут (D-04 «точное совпадение нормализованного имени»).

---

### Точка интеграции в `main()` (D-06 — порядок применения)

**Роль:** orchestration · **Аналог:** `main()` — `scripts/upload.py:676-701`

Память накладывается ПОСЛЕ авто-маппинга групп/фото и блока нового формата, ПЕРЕД `products_to_rows`. Текущий порядок, в который встраивается память:
```python
    # Применить маппинг групп (старый формат — по category_map + переопределения)
    all_products = apply_group_mapping(all_products, category_map)      # ← авто-маппинг группы

    # Новый формат: ... берём из текущего каталога по названию ...
    new_names: set = set()
    if new_format_used:
        current_groups = load_current_groups()
        ...
        for p in all_products:
            if p["source_category"] == "":
                g = current_groups.get(normalize_name(p["name"]))
                ...
    # ── ТОЧКА ИНТЕГРАЦИИ ПАМЯТИ ─────────────────────────────────────
    #   edit_memory = load_edit_memory()  (загрузить рядом с photo_data в начале main, ~стр. 659)
    #   for p in all_products:
    #       edit = edit_memory.get(normalize_name(p["name"]))
    #       if edit:
    #           if edit.get("group"):       p["display_group"] = edit["group"]
    #           if edit.get("photo"):       # переопределить URL фото товара
    #           if edit.get("description"): # переопределить описание
    # ────────────────────────────────────────────────────────────────

    # Подготовить строки для Google Sheet
    rows = products_to_rows(all_products, badges, photo_data, new_names)
```

> **Тонкость по фото/описанию:** сейчас фото/описание подставляются ВНУТРИ `products_to_rows` через `get_photo_url`/`get_photo_description` (`upload.py:504-505`, частичное совпадение по `photo_data`). Память правок задаёт URL/описание точечно по нормализованному имени. Два чистых варианта для планировщика: (а) до `products_to_rows` записать правку в поля товара (`p["photo_override"]`, `p["desc_override"]`) и заставить `products_to_rows` отдавать приоритет им; (б) влить правки прямо в словарь `photo_data` по образцу блока overrides из `load_photo_data` (см. выше). Вариант (б) ближе к существующему паттерну.

**Загрузка памяти в начале `main()`** — по образцу строки `photo_data = load_photo_data()` (`upload.py:659`):
```python
    # Загрузить маппинг фото
    photo_data = load_photo_data()
    # ← сюда же:  edit_memory = load_edit_memory()
```

---

### Определение «новый товар» (MEM-03, D-05)

**Роль:** detection · **Аналог:** блок `new_names` для нового формата — `scripts/upload.py:681-698`

Та же идея «имени нет в эталоне → новый», но эталон — память правок, а не текущие группы. Логировать достаточно (в Этапе 3 панели нет):
```python
    new_names: set = set()
    if new_format_used:
        current_groups = load_current_groups()
        ...
        new_count = 0
        for p in all_products:
            if p["source_category"] == "":
                g = current_groups.get(normalize_name(p["name"]))
                if g and g != "Новинки":
                    p["display_group"] = g
                else:
                    p["display_group"] = "Новинки"
                    new_names.add(p["name"])
                    new_count += 1
        log.info("Новых товаров (в «Новинки»): %d", new_count)
```
Аналогично: `товар «новый для памяти» = normalize_name(p["name"]) not in edit_memory`; накопить счётчик и вывести `log.info("Товаров без правок (новые для памяти): %d", n)`.

---

### (Опционально) Разовая миграция `PRODUCT_OVERRIDES` во вкладку (D-07)

**Роль:** CLI-tool / migration · **Аналог:** `scripts/sheet_tool.py` (вся структура файла, особенно `open_spreadsheet` + `copy_sheet` + диспетчер команд в `main`)

Образец одноразовой утилиты записи в лист — авторизация и запись batch'ем:

**Авторизация (точная копия паттерна upload.py)** — `sheet_tool.py:43-65`:
```python
def open_spreadsheet():
    """Авторизация и открытие таблицы по GOOGLE_SHEETS_ID."""
    import gspread
    from google.oauth2.service_account import Credentials
    creds_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "")
    if not creds_path:
        for d in (SCRIPT_DIR, PROJECT_ROOT):
            candidate = d / "credentials.json"
            if candidate.exists():
                creds_path = str(candidate)
                break
    sheets_id = os.environ.get("GOOGLE_SHEETS_ID", "")
    if not creds_path or not sheets_id:
        print("ERROR: нет credentials.json или GOOGLE_SHEETS_ID")
        sys.exit(2)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    return gspread.authorize(creds).open_by_key(sheets_id)
```

**Создать/очистить лист и записать значения** — `sheet_tool.py:68-90` (создание листа, `resize`, `update` с `value_input_option`):
```python
    try:
        dst = ss.worksheet(dst_name)
        dst.clear()
    except WorksheetNotFound:
        cols = len(values[0]) if values else 9
        dst = ss.add_worksheet(title=dst_name, rows=len(values) + 10, cols=cols)
    if dst.row_count < len(values):
        dst.resize(rows=len(values) + 10)
    if values:
        dst.update(values, value_input_option="USER_ENTERED")
```
> Тот же приём создания/ресайза листа есть в `upload.py:591-609` (`upload_to_google_sheet`) — можно ориентироваться на любой из двух.

---

## Подушка безопасности вкладки «Правки» (Discretion — при необходимости)

**Источник:** `scripts/sheet_tool.py:68-110` (`copy_sheet` + команды `backup`/`rollback`)
**Применять к:** вкладке «Правки», если оценка риска покажет угрозу перезаписи.

`copy_sheet` уже умеет копировать любой лист в `<имя>_BACKUP`. Память на вкладке «Правки» upload.py **только читает** (не перезаписывает), поэтому риск её повреждения штатным прогоном низкий — отдельный бэкап в Этапе 3, скорее всего, избыточен. Если планировщик решит добавить — переиспользовать готовый `copy_sheet("Правки", "Правки_BACKUP")` без нового кода:
```python
def copy_sheet(ss, src_name: str, dst_name: str) -> int:
    """Скопировать значения листа src → dst (dst создаётся/очищается)."""
    from gspread.exceptions import WorksheetNotFound
    src = ss.worksheet(src_name)
    values = src.get_all_values()  # включая заголовок
    ...
    return max(0, len(values) - 1)
```

---

## Сквозные конвенции (соблюдать во всём новом коде этапа)

**Источник:** `.planning/codebase/CONVENTIONS.md` (Python) + наблюдаемый стиль `upload.py`/`sheet_tool.py`

1. **Русские комментарии и docstrings на КАЖДОЙ функции** (явное требование проекта). Образец — `upload.py:62-67`.
2. **Логирование через `log.info` / `log.warning` / `log.error`**, не `print` (кроме итоговой сводки в конце скрипта). Формат сообщений — русский: `log.info("Загружено правок: %d", n)`. Образцы — `upload.py:298, 447, 449`.
3. **Graceful-fallback «нет источника → пустая структура, не падать»** для всех загрузчиков правок/конфигов: вкладки нет / gspread недоступен / нет credentials → `return {}` + `log.warning`/`log.info`. Образцы — `load_badges` (`upload.py:52-59`), `load_current_groups` (`upload.py:260-285`).
4. **Override владельца побеждает авто-данные** (D-06) — наложение поверх, не вместо. Образец — `load_photo_data` overrides-блок (`upload.py:437-447`).
5. **`normalize_name` — единственный ключ сопоставления** (D-04). Не вводить вторую нормализацию.
6. **`pathlib.Path`, `SCRIPT_DIR`/`PROJECT_ROOT`** для путей; `encoding="utf-8"` во всех файловых операциях. Образцы — `upload.py:44-46, 416-419`.
7. **Type-аннотации** в сигнатурах (Python 3.10+): `def load_edit_memory() -> dict[str, dict[str, str]]:`. Образец — `upload.py:398`.
8. **Лениво импортировать `gspread`/`google.oauth2`** внутри функции с `except ImportError: return {}`. Образец — `upload.py:260-264`.
9. **Скопы и поиск credentials** строго как в `load_current_groups`/`open_spreadsheet` (env `GOOGLE_CREDENTIALS_PATH` → перебор `SCRIPT_DIR`/`PROJECT_ROOT` → `credentials.json`; env `GOOGLE_SHEETS_ID`). Новых env-переменных не вводить.
10. **`--dry-run`** обязателен для любого нового скрипта, который пишет в лист (если будет создан `migrate_overrides.py`). Образец — `upload.py:629-633`. Фатальные ошибки — `raise SystemExit(1)` / `sys.exit(1)` (в существующем коде встречается оба; новый код — `raise SystemExit(1)` по CONVENTIONS).

---

## Файлы без аналога

Нет. Все требуемые куски логики этапа имеют прямой образец в существующем коде (`upload.py`, `sheet_tool.py`). Планировщику НЕ нужно опираться на абстрактные паттерны из RESEARCH.md — для каждого блока указан конкретный файл, диапазон строк и фрагмент кода.

---

## Метаданные

**Область поиска аналогов:** `scripts/upload.py`, `scripts/sheet_tool.py`, `scripts/` (grep по `description_overrides`)
**Файлов прочитано:** 4 (CONTEXT.md, ARCHITECTURE.md, CONVENTIONS.md, upload.py, sheet_tool.py)
**Дата извлечения паттернов:** 2026-06-07
