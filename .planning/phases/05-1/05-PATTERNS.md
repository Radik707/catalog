# Phase 5: Структура данных двухуровневой навигации — Pattern Map

**Mapped:** 2026-06-09
**Files analyzed:** 2 (1 новый + 1 модифицируемый)
**Analogs found:** 2 / 2

---

## File Classification

| Новый / изменяемый файл | Роль | Data Flow | Ближайший аналог | Качество совпадения |
|-------------------------|------|-----------|-----------------|---------------------|
| `scripts/structure_map.json` | config / data | batch (читается Python-скриптом однократно при старте) | `scripts/category_map.json` | role-match (плоский → вложенный, смысл тот же) |
| `scripts/upload.py` (модификация) | utility / ETL pipeline | batch, transform | сам файл (расширяем существующие функции) | exact |

---

## Pattern Assignments

### `scripts/structure_map.json` (config, batch)

**Аналог:** `scripts/category_map.json`

**Реальная форма аналога** (весь файл, 133 строки):

```json
{
  "Кока-Кола": "Напитки",
  "Пепси": "Напитки",
  "Спрайт": "Напитки",
  "Let's Be": "Напитки",
  "Продако": "Напитки",
  "Квас": "Напитки",
  "Энергетик  Берн": "Энергетики",
  "СэнСой Соусы": "Стоевъ и Сэнсой",
  "Стоевъ Кетчуп/соусы/пасты/горчица": "Стоевъ и Сэнсой",
  "Стоевъ Консервация овощная": "Стоевъ и Сэнсой",
  "Стоевъ Консервация фруктовая": "Стоевъ и Сэнсой",
  "Стоевъ Сок": "Стоевъ и Сэнсой",
  "Стоевъ Уксус": "Стоевъ и Сэнсой",
  "Сладонеж": "Конфеты и печенье",
  "Коробочные": "Коробочные конфеты",
  "Мистраль Крупы варпак": "Крупы и бакалея",
  "...": "..."
}
```

Полная форма: плоский объект `{ "КлючКатегории": "НазваниеГруппы" }`, 117 ключей, значения — 14 групп. Ключи совпадают с `source_category` из прайса дословно (используются как есть, без нормализации).

**Целевая форма `structure_map.json`** (вложенная, по D-01 / D-02):

```json
{
  "Сладкое": {
    "Шоколад и батончики": [
      "Батончик Твикс", "Батончик Баунти", "Батончик КитКат",
      "Батончик Натс", "Батончик Пикник", "Батончик Сникерс",
      "Батончики",
      "Шоколад Бабаевский", "Шоколад Красный Октябрь",
      "Шоколад Милка", "Милка импорт", "Лотте", "Шоколад",
      "Киндер", "Шок. паста", "Паста шок.",
      "Драже Скитлс", "Драже М&М's"
    ],
    "Конфеты": [
      "Весовые конфеты", "Вес. конфеты",
      "Конфеты в коробке", "Леденцы", "Драже",
      "Ментос", "Пакеты конфет", "Акконд",
      "Коробочные", "Подарки", "Торты",
      "Набор конфет ЛЮСИ", "Набор конфет МВН",
      "Набор конфет Сонуар", "Фас. кор. конфеты"
    ],
    "Печенье и вафли": [
      "Печенье фас, бисквиты, кексы",
      "Вес. печенье", "Фас. печенье",
      "Сладонеж"
    ],
    "Детское": [
      "Детское", "Чупа-Чупсы", "Вес. драже Арахис"
    ]
  },
  "Напитки": {
    "Воды и газировки": [
      "Кока-Кола", "Пепси", "Спрайт", "Фанта", "Вода",
      "Let's Be", "Продако", "Квас"
    ],
    "Соки": [
      "Добрый", "Добрый сок", "Фреш Бар",
      "Стоевъ Сок"
    ],
    "Чай и кофе": [
      "Чай Гринфилд", "Чай Кертис", "Чай Лисма",
      "Чай Майский", "Чай Принцесса Нури", "чай Ричард",
      "Кофе Лебо", "Кофе Жардин", "Кофе Жокей",
      "Кофе зерновой", "Кофе Нескафе", "Кофе Фейс", "Кофе Якобс"
    ],
    "Энергетики": [
      "Энергетик  Берн", "Энергетик Ред Булл",
      "Энергетик Адреналин", "Энергетик Инвок",
      "Энергетик Лит Энерджи", "Энергетик Флеш", "Энергетики"
    ]
  },
  "Крупы, лапша, бакалея": {
    "Крупы и бакалея": [
      "Знатные", "Пастерони",
      "Мистраль Крупы", "Мистраль Крупы варпак",
      "Мистраль Разное", "Мистраль Хлебцы"
    ],
    "Лапша и каши б/п": [
      "Доширак", "Биг Ланч", "Роллтон",
      "Мистраль Каши", "Мистраль Хлопья",
      "СэнСой Б/П", "СэнСой Лапша"
    ]
  },
  "Соусы и консервация": {
    "Соусы/кетчуп/майонез/приправы": [
      "Разные соусы", "Царска приправа",
      "Царский Кетчуп", "Царский Майонез",
      "Царский HoReCa Майонез", "Царский",
      "Др. Бейкерс", "Пасты", "Аджика АМЦА",
      "СэнСой Соусы", "СэнСой Соусы Соевые", "СэнСой Разное",
      "Стоевъ", "Стоевъ Кетчуп/соусы/пасты/горчица",
      "Стоевъ Приправа", "Стоевъ Уксус"
    ],
    "Консервация": [
      "Консервация мясная", "Консервация овощная", "Консервация рыбная",
      "Стоевъ Консервация овощная", "Стоевъ Консервация фруктовая"
    ]
  },
  "Снэки и прикассовое": {
    "Чипсы/сухарики/орехи/крекеры": [
      "Орехи", "Чипсы", "Гренкино",
      "Кукурузные снэки", "Крекеры", "Джинн"
    ],
    "Жвачка/Холс/цикорий": [
      "Орбит", "Ж/р Орбит", "Холс",
      "Ж/р Ментос", "Цикорий"
    ]
  }
}
```

**Примечания по содержимому:**
- Ключи массивов — точные строки из `category_map.json` (те же, что попадают в `product["source_category"]`)
- Порядок в массивах = порядок отображения (D-02); переставить строку = изменить позицию кластера
- «Коробочные конфеты» (7 категорий: Коробочные, Подарки, Торты, Набор конфет ЛЮСИ, Набор конфет МВН, Набор конфет Сонуар, Фас. кор. конфеты) идут последними в «Конфеты» — это реализует кластер «Подарочные кучей» (D-06)
- «Энергетики» идут последними в «Напитки» (D-05)
- «Стоевъ Нектар…» категорий в `category_map.json` нет явно под этим ключом — при сверке D-13 исполнитель должен проверить реальные `source_category` новинок Стоевъ в прайсе и добавить при необходимости
- Итого по разделам: Сладкое (31 кат.) · Напитки (24 кат.) · Крупы (13 кат.) · Соусы (16 кат.) · Снэки (11 кат.) — сумма ~95; оставшиеся ~22 категории требуют верификации по реальному прайсу при D-13

---

### `scripts/upload.py` — точки модификации

#### 1. Новая функция `load_structure_map()` (добавить после строки 89)

**Образец:** `load_category_map()` (строки 82–89, точное совпадение)

```python
def load_category_map() -> dict:
    """Загрузить маппинг категорий из category_map.json."""
    map_path = SCRIPT_DIR / "category_map.json"
    if not map_path.exists():
        log.warning("Файл category_map.json не найден: %s", map_path)
        return {}
    with open(map_path, "r", encoding="utf-8") as f:
        return json.load(f)
```

**Копировать дословно, заменив имена:**

```python
def load_structure_map() -> dict:
    """Загрузить карту двухуровневой структуры из structure_map.json.

    Формат: { "Раздел": { "Подгруппа": ["КатегорияА", "КатегорияБ", ...] } }
    При отсутствии файла возвращает пустой словарь — скрипт работает без ошибок.
    """
    map_path = SCRIPT_DIR / "structure_map.json"
    if not map_path.exists():
        log.warning("Файл structure_map.json не найден: %s — поля Подгруппа/Раздел не будут заполнены", map_path)
        return {}
    with open(map_path, "r", encoding="utf-8") as f:
        return json.load(f)
```

---

#### 2. Новая функция `build_category_index()` — вспомогательная

После `load_structure_map()`. Строит обратный индекс `{ "КатегорияA": ("Раздел", "Подгруппа", раздел_idx, подгр_idx, кат_idx) }` для O(1)-поиска при обходе товаров:

```python
def build_category_index(structure_map: dict) -> dict:
    """Построить обратный индекс категорий для быстрого поиска раздела/подгруппы.

    Возвращает: { "НазваниеКатегории": (раздел, подгруппа, idx_раздела, idx_подгруппы, idx_кат) }
    Порядковые индексы используются для сортировки товаров (D-05).
    """
    index = {}
    for sec_idx, (section, subgroups) in enumerate(structure_map.items()):
        for sub_idx, (subgroup, categories) in enumerate(subgroups.items()):
            for cat_idx, category in enumerate(categories):
                index[category] = (section, subgroup, sec_idx, sub_idx, cat_idx)
    return index
```

---

#### 3. Новая функция `apply_structure_mapping()` (добавить рядом с `apply_group_mapping()`, строка ~427)

**Образец:** `apply_group_mapping()` (строки 404–426)

```python
def apply_group_mapping(products: list[dict], category_map: dict) -> list[dict]:
    """Добавить поле display_group на основе маппинга категорий из category_map.json."""
    unmapped = set()
    for product in products:
        cat = product["source_category"]
        group = category_map.get(cat)
        if group is None:
            unmapped.add(cat)
            group = "Другое"
        product["display_group"] = group
    if unmapped:
        log.warning("Категории без маппинга (попадут в 'Другое'):")
        for cat in sorted(unmapped):
            log.warning("  - %s", cat)
    return products
```

**Копировать структуру, дополнив логикой D-12 (fallback с предупреждением):**

```python
def apply_structure_mapping(
    products: list[dict],
    category_index: dict,
) -> list[dict]:
    """Добавить поля display_subgroup и display_section из карты structure_map.json.

    Каждый товар получает:
      - p["display_subgroup"] — подгруппа (второй уровень)
      - p["display_section"]  — раздел (первый уровень)
      - p["_sort_key"]        — кортеж (idx_раздела, idx_подгруппы, idx_кат) для сортировки (D-05)

    Категории, не найденные в карте, попадают в fallback «Прочее»/«Прочее»
    с предупреждением в лог — ничего не теряется молча (D-12).
    """
    FALLBACK_SECTION  = "Прочее"
    FALLBACK_SUBGROUP = "Прочее"
    FALLBACK_SORT     = (9999, 9999, 9999)

    unmapped = set()
    for product in products:
        cat = product["source_category"]
        entry = category_index.get(cat)
        if entry is None:
            unmapped.add(cat)
            product["display_section"]  = FALLBACK_SECTION
            product["display_subgroup"] = FALLBACK_SUBGROUP
            product["_sort_key"]        = FALLBACK_SORT
        else:
            section, subgroup, sec_idx, sub_idx, cat_idx = entry
            product["display_section"]  = section
            product["display_subgroup"] = subgroup
            product["_sort_key"]        = (sec_idx, sub_idx, cat_idx)

    if unmapped:
        log.warning("Категории без структурного маппинга (попадут в «Прочее»):")
        for cat in sorted(unmapped):
            log.warning("  ! %s", cat)

    return products
```

---

#### 4. Строка заголовка Sheet (строка 645) — добавить два новых поля

**Текущий код (строка 645):**

```python
header = ["Наименование", "Цена", "Остаток", "Категория", "Группа", "Поставщик", "Badge", "ImageUrl", "Description"]
```

**Изменить на (D-04 — старые колонки нетронуты, новые добавлены в конец):**

```python
header = [
    "Наименование", "Цена", "Остаток", "Категория",
    "Группа",           # старое поле — не трогаем (D-04)
    "Поставщик", "Badge", "ImageUrl", "Description",
    "Подгруппа",        # новое поле этапа 5
    "Раздел",           # новое поле этапа 5
]
```

**В блоке формирования строки товара (строки 666–676) добавить в конец `rows.append([...])` два новых значения:**

```python
rows.append([
    displayed_name,
    p["price"],
    p["stock"],
    p["source_category"],
    p["display_group"],         # старое поле — нетронуто
    p["supplier_file"],
    badge,
    image_url,
    description,
    p.get("display_subgroup", ""),   # новое поле
    p.get("display_section", ""),    # новое поле
])
```

---

#### 5. Сортировка товаров по структуре (добавить в `main()`, строка ~853)

**Образец паттерна** — статистика групп в `main()` (строки 884–891):

```python
# Статистика по группам
groups = {}
for p in all_products:
    g = p["display_group"]
    groups[g] = groups.get(g, 0) + 1
log.info("Распределение по группам:")
for g in sorted(groups, key=groups.get, reverse=True):
    log.info("  %s: %d товаров", g, groups[g])
```

**Новый блок сортировки** (вставить после `apply_structure_mapping()`, перед `products_to_rows()`):

```python
# Сортировать товары по структуре: раздел → подгруппа → категория (D-05)
# _sort_key проставлен apply_structure_mapping(); товары без структуры уходят в конец
all_products.sort(key=lambda p: p.get("_sort_key", (9999, 9999, 9999)))
log.info("Товары отсортированы по двухуровневой структуре")
```

---

#### 6. Валидация покрытия D-12 — «Новинки» fallback как образец

**Образец паттерна изоляции нераспознанных (строки 860–874):**

```python
if new_format_used:
    current_groups = load_current_groups()
    if not current_groups:
        log.error("Новый формат, но не удалось прочитать текущие группы каталога — "
                  "обновление прервано (иначе все товары попали бы в «Новинки»).")
        sys.exit(1)
    new_count = 0
    for p in all_products:
        if p["source_category"] == "":  # пришёл из нового формата
            g = current_groups.get(normalize_name(p["name"]))
            if g and g != "Новинки":
                p["display_group"] = g
            else:
                p["display_group"] = "Новинки"
                new_names.add(p["name"])
                new_count += 1
    log.info("Новых товаров (в «Новинки»): %d", new_count)
```

**D-12 реализуется через** `apply_structure_mapping()` (см. п.3 выше): все непокрытые категории логируются с `log.warning("  ! %s", cat)` — ни одна не теряется молча. Дополнительный итог после вызова:

```python
# D-12: сводка покрытия структурным маппингом
uncovered = [p for p in all_products if p.get("display_section") == "Прочее"]
if uncovered:
    uncovered_cats = sorted({p["source_category"] for p in uncovered})
    log.warning("D-12: %d товаров из %d категорий не покрыты structure_map.json — попали в «Прочее»:",
                len(uncovered), len(uncovered_cats))
    for cat in uncovered_cats:
        log.warning("  ! непокрыто: %s", cat)
```

---

#### 7. Порядок вызовов в `main()` (строки 789–905, финальная схема)

**Текущий порядок шагов** (строки 852–882):

```python
# строка 853: Применить маппинг групп (старый)
all_products = apply_group_mapping(all_products, category_map)

# строки 858–874: Новый формат → «Новинки» fallback
if new_format_used:
    ...

# строка 878: Наложить память правок
new_for_memory = apply_edit_memory(all_products, edit_memory)

# строка 882: Подготовить строки для Sheet
rows = products_to_rows(all_products, badges, photo_data, new_names, url_index)
```

**Новый порядок** (изменения минимальны — добавляем блоки, не сдвигаем существующие):

```python
# [без изменений] Применить маппинг групп (старый — D-04)
all_products = apply_group_mapping(all_products, category_map)

# [без изменений] Новый формат → «Новинки» fallback
if new_format_used:
    ...

# [БЕЗ ИЗМЕНЕНИЙ] Наложить память правок
new_for_memory = apply_edit_memory(all_products, edit_memory)

# [НОВОЕ] Загрузить карту структуры и применить раздел/подгруппу
structure_map = load_structure_map()
if structure_map:
    category_index = build_category_index(structure_map)
    all_products = apply_structure_mapping(all_products, category_index)
    # Сортировка по структуре (D-05)
    all_products.sort(key=lambda p: p.get("_sort_key", (9999, 9999, 9999)))
    log.info("Товары отсортированы по двухуровневой структуре")
    # D-12: сводка непокрытых категорий
    uncovered = [p for p in all_products if p.get("display_section") == "Прочее"]
    if uncovered:
        uncovered_cats = sorted({p["source_category"] for p in uncovered})
        log.warning("D-12: %d товаров (%d кат.) не покрыты structure_map.json → «Прочее»",
                    len(uncovered), len(uncovered_cats))
        for cat in uncovered_cats:
            log.warning("  ! %s", cat)
else:
    log.info("structure_map.json не загружен — поля Подгруппа/Раздел будут пустыми")

# [без изменений] Подготовить строки (уже с новыми полями)
rows = products_to_rows(all_products, badges, photo_data, new_names, url_index)
```

---

#### 8. Preview / dry-run механизм (D-13) — существующий паттерн

**Аналог уже встроен в `upload.py`:** флаг `--dry-run` (строки 799–803, 893–901).

```python
# Объявление флага (строки 799–803):
parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Только парсинг, без записи в Google Sheet",
)

# Использование флага (строки 893–901):
if args.dry_run:
    log.info("--dry-run: запись в Google Sheet пропущена")
    # Вывести первые 5 строк как пример
    print("\nПример данных (первые 5 товаров):")
    print("-" * 100)
    for row in rows[:6]:  # заголовок + 5 товаров
        print(" | ".join(str(x) for x in row))
    print("-" * 100)
    print(f"Всего строк (без заголовка): {len(rows) - 1}")
else:
    upload_to_google_sheet(rows, num_files=len(xlsx_files))
```

**D-13 реализуется расширением блока `--dry-run`** — в `if args.dry_run:` добавить вывод предпросмотра структуры (вместо отдельного скрипта):

```python
if args.dry_run:
    log.info("--dry-run: запись в Google Sheet пропущена")

    # D-13: человекочитаемый предпросмотр структуры (раздел → подгруппа → категории + счётчики)
    if structure_map:
        print("\n" + "=" * 70)
        print("ПРЕДПРОСМОТР ДВУХУРОВНЕВОЙ СТРУКТУРЫ (для сверки владельцем)")
        print("=" * 70)
        # Собрать счётчики по разделу/подгруппе
        counters: dict[tuple, int] = {}
        for p in all_products:
            key = (p.get("display_section", "Прочее"), p.get("display_subgroup", "Прочее"))
            counters[key] = counters.get(key, 0) + 1
        for section, subgroups in structure_map.items():
            total_section = sum(counters.get((section, sg), 0) for sg in subgroups)
            print(f"\n[{section}]  — итого: {total_section} товаров")
            for subgroup, categories in subgroups.items():
                count = counters.get((section, subgroup), 0)
                print(f"  {subgroup}  ({count} товаров)")
                for cat in categories:
                    cat_count = sum(
                        1 for p in all_products
                        if p["source_category"] == cat
                    )
                    if cat_count:
                        print(f"    · {cat}: {cat_count}")
        uncovered_section = counters.get(("Прочее", "Прочее"), 0)
        if uncovered_section:
            print(f"\n[Прочее]  — {uncovered_section} товаров (не покрыты structure_map.json)")
        print("=" * 70)
    else:
        # Старый dry-run вывод
        print("\nПример данных (первые 5 товаров):")
        print("-" * 100)
        for row in rows[:6]:
            print(" | ".join(str(x) for x in row))
        print("-" * 100)
        print(f"Всего строк (без заголовка): {len(rows) - 1}")
```

**Использование для D-13:**
```
python scripts/upload.py --dry-run
```

---

## Shared Patterns

### Загрузка JSON-конфигов (применяется ко всем новым `load_*()`)

**Источник:** `scripts/upload.py`, строки 52–59 (`load_badges`) и 82–89 (`load_category_map`)

```python
# Паттерн: graceful-fallback при отсутствии файла, явный warn в лог
def load_XXXXX() -> dict:
    path = SCRIPT_DIR / "XXXXX.json"
    if not path.exists():
        log.warning("Файл XXXXX.json не найден: %s", path)
        return {}  # или подходящий пустой тип
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
```

Применяется к `load_structure_map()` без изменений.

### Логирование предупреждений о непокрытых элементах

**Источник:** `apply_group_mapping()`, строки 411–425

```python
if unmapped:
    log.warning("Категории без маппинга (попадут в 'Другое'):")
    for cat in sorted(unmapped):
        log.warning("  - %s", cat)
```

Применяется в `apply_structure_mapping()` с аналогичной структурой (`log.warning("  ! %s", cat)`).

### SCRIPT_DIR для путей

**Источник:** строка 45

```python
SCRIPT_DIR = Path(__file__).resolve().parent
```

Все JSON-файлы загружаются через `SCRIPT_DIR / "имя.json"` — путь не зависит от рабочей директории при запуске.

---

## No Analog Found

Файлов без аналога нет. Оба целевых файла хорошо покрыты существующими паттернами.

---

## Metadata

**Область поиска аналогов:** `scripts/`, `.planning/codebase/`
**Файлов прочитано:** 7 (`upload.py`, `category_map.json`, `badges.json`, `CONTEXT.md`, `ARCHITECTURE.md`, `STRUCTURE.md`)
**Верификация номеров строк:** проведена — все цитированные номера (`82`, `104`, `404`, `645`, `789`, `860`, `893`) подтверждены против актуального кода
**Дата маппинга:** 2026-06-09
