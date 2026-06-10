# Этап 4: Админ-панель владельца — Карта паттернов

**Составлено:** 2026-06-07
**Файлов проанализировано:** 6 (новых/изменяемых)
**Аналогов найдено:** 5 / 6

---

## Классификация файлов

| Новый / изменяемый файл | Роль | Поток данных | Ближайший аналог | Качество совпадения |
|-------------------------|------|--------------|------------------|---------------------|
| `uploader/admin.py` | controller + service | request-response + CRUD | `uploader/app.py` | точное |
| `uploader/app.py` (расширение) | controller | request-response | `uploader/app.py` (сам себя) | точное |
| `scripts/sheet_helper.py` (новый) | utility | CRUD (Google Sheets) | `scripts/upload.py` `load_edit_memory` / `upload_to_google_sheet` | role-match |
| `scripts/cloudinary_helper.py` (новый) | utility | file-I/O | `scripts/upload_photos.py` | точное |
| `scripts/upload.py` (расширение: тип `name`) | service | CRUD | сам себя (`apply_edit_memory`) | точное |
| `uploader/.env.example` (расширение) | config | — | `uploader/.env.example` | точное |

---

## Паттерны по файлам

### `uploader/admin.py` — новый Flask-модуль AdminPanel

**Аналог:** `uploader/app.py`

**Паттерн импортов** (строки 1–37):
```python
import os
import re
import sys
import hmac
import json
import logging
import threading
import subprocess
from pathlib import Path
from flask import Flask, request, jsonify, abort
```
Примечание: `admin.py` добавит импорт `gspread` и `cloudinary.uploader` —
первый раз, когда эти пакеты входят в Flask-приложение напрямую
(раньше использовались только через шелл-аут `_run_py`).

**Паттерн авторизации** (строки 401–411):
```python
def check(token: str) -> None:
    # Постоянное по времени сравнение — защита от таймингового подбора секрета
    if not APP_SECRET or not hmac.compare_digest(token, APP_SECRET):
        abort(404)

@app.get("/<token>")
def index(token: str):
    check(token)
    return PAGE.replace("__TOKEN__", token)
```
Для `admin.py`: заменить `APP_SECRET` на `ADMIN_SECRET` (новая env-переменная);
маршруты `/<ADMIN_SECRET>/` и `/<ADMIN_SECRET>/item/<normalized_name>`.

**Паттерн PROCESS_LOCK + фоновой обработки** (строки 82–84, 466–506):
```python
# Глобальный замок для защиты от двойного запуска обработки (gunicorn -w 1)
PROCESS_LOCK = threading.Lock()

@app.post("/<token>/update")
def update(token: str):
    if not PROCESS_LOCK.acquire(blocking=False):
        return jsonify(ok=False, message="Обработка уже идёт, подождите.")
    try:
        thread = threading.Thread(target=_process_async, args=(entry_id,), daemon=True)
        thread.start()
    except Exception:
        PROCESS_LOCK.release()
        return jsonify(ok=False, message="Не удалось запустить обработку.")
    return jsonify(ok=True, message="Файлы отправлены, обработка идёт.")
```
Для кнопки «Применить сейчас»: `admin.py` импортирует тот же `PROCESS_LOCK`
из `app.py` (или использует общий модуль), чтобы не дублировать замок.
При отсутствии `LAST_BATCH_DIR` — возвращать `{"ok": false, message: "Прайсы ещё не загружались."}`.

**Паттерн шелл-аута в Python-скрипты** (строки 286–295):
```python
def _run_py(script: Path, *args) -> tuple[int, str]:
    """Запустить python-скрипт, вернуть (код возврата, объединённый вывод)."""
    proc = subprocess.run(
        [PYTHON_BIN, str(script), *args],
        cwd=str(script.parent),   # чтобы нашлись category_map.json, .env и т.п.
        capture_output=True,
        text=True,
        timeout=UPLOAD_TIMEOUT,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
```
Использовать для вызова `sheet_helper.py` и `cloudinary_helper.py`
из `admin.py` — минимальный риск: Flask-процесс не тянет новые зависимости напрямую.

**Паттерн обработки ошибок** (строки 229–247):
```python
    except Exception as exc:
        log.exception("Необработанное исключение в _process_async: %s", exc)
        try:
            notify("error", f"❌ Непредвиденная ошибка: {exc}")
        except Exception:
            pass
    finally:
        PROCESS_LOCK.release()   # освобождаем замок — всегда
```

**Паттерн одностраничного HTML (`PAGE`)** (строки 528–803):
```python
PAGE = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Вкусный Дом — Панель управления</title>
<!-- Подключаем Tabler CSS вместо inline-стилей (D-03) -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/core@1.x/dist/css/tabler.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.x/tabler-icons.min.css">
<style>
  /* Переиспользуем переменные цветов из загрузчика — только кастомные переопределения */
  body { background: #f3f4f6; }
  .status.ok  { background:#ecfdf5; color:#065f46; }
  .status.err { background:#fef2f2; color:#991b1b; }
  .status.info{ background:#eff6ff; color:#1e40af; }
</style>
</head>
<body>
<div class="container-sm py-3">   <!-- max-width 640px, mobile-first -->
  ...
</div>
<script>
const TOKEN = "__TOKEN__";
...
</script>
</body>
</html>"""
```
Шаблон: `PAGE.replace("__TOKEN__", token)` — тот же способ,
Tabler подключается только как CSS (не JS), чтобы не добавлять CDN-JS риски.

**Паттерн функции `show(kind, text)`** (строки 630–633):
```javascript
function show(kind, text) {
  status.className = "status " + kind;
  status.textContent = text;
}
```
Переиспользовать без изменений. Семантика `kind`: `ok` / `err` / `info`.

---

### `uploader/app.py` — расширение (монтирование admin-блюпринта)

**Аналог:** сам файл, строки 407–524

Добавить в конец `app.py` перед `main()`:
```python
# Подключить admin-панель как Blueprint (изоляция маршрутов)
from admin import admin_bp
app.register_blueprint(admin_bp)
```
Альтернатива (если не blueprint): просто добавить `import admin` в конец —
`admin.py` при импорте регистрирует маршруты на тот же `app`.
Выбор между blueprint и прямым импортом — на усмотрение исполнителя;
blueprint чище изолирует маршруты.

---

### `scripts/sheet_helper.py` — утилита чтения/записи Google Sheet

**Аналог:** `scripts/upload.py` строки 254–401 (`load_current_groups`, `load_edit_memory`, `upload_to_google_sheet`)

**Паттерн авторизации gspread** (строки 260–281 `upload.py`):
```python
def _get_spreadsheet():
    """Авторизоваться в Google Sheets и вернуть объект Spreadsheet."""
    import gspread
    from google.oauth2.service_account import Credentials

    creds_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "")
    if not creds_path:
        for d in (SCRIPT_DIR, PROJECT_ROOT):
            c = d / "credentials.json"
            if c.exists():
                creds_path = str(c)
                break
    sheets_id = os.environ.get("GOOGLE_SHEETS_ID", "")
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    return gspread.authorize(creds).open_by_key(sheets_id)
```

**Паттерн чтения вкладки с graceful-fallback** (строки 302–401 `upload.py`):
```python
def load_products() -> list[dict]:
    """Прочитать лист «Товары» → список товаров. Graceful-fallback: [] при ошибке."""
    try:
        ss = _get_spreadsheet()
        values = ss.worksheet("Товары").get_all_values()
    except Exception as e:
        log.warning("Не удалось прочитать лист «Товары»: %s", e)
        return []
    if not values:
        return []
    header = values[0]
    # ... парсинг строк по индексам ...
    return products
```

**Паттерн записи строки в «Правки»** (схема по `load_edit_memory`, строки 302–401):
```python
def append_edit(product_key: str, edit_type: str, value: str) -> None:
    """Добавить строку в вкладку «Правки» (Товар | Тип | Значение).

    Создаёт вкладку при отсутствии. Graceful: ошибка логируется, не поднимается.
    Схема: product_key = normalize_name(name), edit_type = group|photo|description|name
    """
    try:
        ss = _get_spreadsheet()
        try:
            ws = ss.worksheet("Правки")
        except gspread.exceptions.WorksheetNotFound:
            ws = ss.add_worksheet(title="Правки", rows=1000, cols=3)
            ws.append_row(["Товар", "Тип", "Значение"])
        ws.append_row([product_key, edit_type, value])
        log.info("Правка записана: %s | %s | %s", product_key, edit_type, value[:40])
    except Exception as e:
        log.warning("Не удалось записать правку: %s", e)
        raise   # пробрасываем — вызывающий сформирует HTTP 500
```

**Паттерн интерфейса командной строки** (строки 711–728 `upload.py`):
```python
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Утилита управления данными каталога")
    parser.add_argument("action", choices=["list", "append_edit", "load_edits"])
    # ... аргументы ...
    args = parser.parse_args()
```
`sheet_helper.py` вызывается либо напрямую (тесты/отладка), либо через `_run_py`
из `admin.py`.

---

### `scripts/cloudinary_helper.py` — утилита загрузки фото

**Аналог:** `scripts/upload_photos.py` строки 56–183

**Паттерн load_env** (строки 60–76 `upload_photos.py`):
```python
def load_env() -> None:
    """Загрузить переменные из .env (как в upload.py и upload_photos.py)."""
    for search_dir in [PROJECT_ROOT, SCRIPT_DIR]:
        env_path = search_dir / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip().strip("'\""))
            return
```

**Паттерн инициализации Cloudinary** (строки 156–183 `upload_photos.py`):
```python
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME", ""),
    api_key=os.environ.get("CLOUDINARY_API_KEY", ""),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET", ""),
    secure=True,
)
```

**Паттерн получения public_id** (строки 102–109 `upload_photos.py`):
```python
def get_public_id(file_name: str, folder: str) -> str:
    """«faradella.jpg» + «presenter» → «presenter/faradella» (без расширения)."""
    stem = Path(file_name).stem
    return f"{folder}/{stem}"
```

**Паттерн загрузки одного файла** (строки 274–298 `upload_photos.py`):
```python
result = cloudinary.uploader.upload(
    file_bytes_or_path,         # bytes из request.files или str-путь
    public_id=get_public_id(original_name, "presenter"),
    overwrite=True,             # замена фото → всегда overwrite
    resource_type="image",
    eager=[{"format": "webp", "quality": "auto"}],
    eager_async=True,
)
url = result["secure_url"]     # → записать в вкладку «Правки» как тип «photo»
```

**Паттерн формата привязки фото** (из `scripts/photo_overrides.json`):
```json
"Акконд фас. кор. конфеты Болетто 225г": "akkond/001.png"
```
Формат значения в вкладке «Правки»:
- Тип = `"photo"`
- Значение = `"presenter/<stem>.<ext>"` (всегда папка `presenter/` для фото из панели)

Ключ записи = `normalize_name(product_name)` — как в `load_edit_memory`.

---

### `scripts/upload.py` — расширение: тип правки `name`

**Аналог:** сам файл — `load_edit_memory` (строки 302–401) и `apply_edit_memory` (строки 429–458)

**Место изменения 1: ALLOWED_TYPES** (строка 371):
```python
# До:
ALLOWED_TYPES = {"group", "photo", "description"}
# После (добавить "name"):
ALLOWED_TYPES = {"group", "photo", "description", "name"}
```

**Место изменения 2: apply_edit_memory** (строки 429–458):
```python
def apply_edit_memory(products, edit_memory):
    new_for_memory = 0
    for p in products:
        key = normalize_name(p["name"])
        edit = edit_memory.get(key)
        if edit:
            if "group" in edit:
                p["display_group"] = edit["group"]
            if "photo" in edit:
                p["photo_override"] = edit["photo"]
            if "description" in edit:
                p["desc_override"] = edit["description"]
            # НОВОЕ: применение правки названия (D-05, этап 4)
            # Ключ сопоставления — нормализованное имя из прайса (не меняется)
            # Отображаемое имя заменяется; p["name"] остаётся ключом для normalize_name
            if "name" in edit:
                p["display_name"] = edit["name"]
        else:
            new_for_memory += 1
    return new_for_memory
```

**Место изменения 3: products_to_rows** (строки 561–599):
```python
# В строке формирования данных — брать display_name если есть, иначе name:
displayed_name = p.get("display_name") or p["name"]
rows.append([
    displayed_name,        # ← было: p["name"]
    p["price"],
    ...
])
```

---

### `uploader/.env.example` — расширение

**Аналог:** `uploader/.env.example` (сам файл)

Добавить в конец файла:
```dotenv
# --- Админ-панель владельца (этап 4) ---
# Отдельный секрет для панели управления — НЕ тот же, что APP_SECRET.
# Сгенерировать: python -c "import secrets; print(secrets.token_urlsafe(32))"
ADMIN_SECRET=

# Переменные Cloudinary (для загрузки фото из панели).
# Сейчас хранятся в корневом .env проекта — скопировать сюда для uploader/.env.
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# Путь к credentials.json (Service Account Google) — уже должен быть на сервере.
# Если не задан — ищется в scripts/ и корне проекта автоматически.
GOOGLE_CREDENTIALS_PATH=/opt/apps/catalog/scripts/credentials.json
GOOGLE_SHEETS_ID=
```

---

## Общие (cross-cutting) паттерны

### Авторизация секретом в URL
**Источник:** `uploader/app.py` строки 401–404
**Применять к:** всем маршрутам `admin.py`
```python
def check_admin(token: str) -> None:
    # hmac.compare_digest — защита от timing-атаки (как в check() загрузчика)
    if not ADMIN_SECRET or not hmac.compare_digest(token, ADMIN_SECRET):
        abort(404)
```

### Обработка ошибок: JSON-ответы
**Источник:** `uploader/app.py` строки 432–455, 466–506
**Применять к:** всем POST-эндпоинтам `admin.py`
```python
try:
    result = do_something()
    return jsonify(ok=True, data=result)
except Exception as exc:
    log.warning("Ошибка операции: %s", exc)
    return jsonify(ok=False, message="Не удалось выполнить операцию."), 500
```
Трассировки и технические детали — только в `log`, не в ответ клиенту.

### Graceful-fallback при отсутствии данных
**Источник:** `scripts/upload.py` строки 302–401 (`load_edit_memory`)
**Применять к:** `sheet_helper.py`, `cloudinary_helper.py`
```python
# Если вкладки нет / ошибка доступа / нет credentials — возвращаем [],
# скрипт продолжает работу без ошибок
except gspread.exceptions.WorksheetNotFound:
    log.info("Вкладка «Правки» не найдена — память правок пуста")
    return {}
except Exception as e:
    log.warning("Не удалось прочитать данные: %s", e)
    return {}
```

### Паттерн normalize_name как ключ сопоставления
**Источник:** `scripts/upload.py` строки 213–215
**Применять к:** всем местам в `admin.py` и `sheet_helper.py`, где ключ правки
записывается / читается из вкладки «Правки»
```python
def normalize_name(name: str) -> str:
    """Ключ сопоставления: нижний регистр + убрать хвостовую единицу + сжать пробелы."""
    return re.sub(r"\s+", " ", re.sub(r",\s*[А-Яа-яA-Za-z.]+\s*$", "", name)).strip().lower()
```
В `admin.py`: вызывать через `_run_py(sheet_helper, "normalize", name)` или
копировать функцию напрямую (она без зависимостей, 2 строки).

### Логирование
**Источник:** `uploader/app.py` строки 41–47, `scripts/upload.py` строки 37–42
**Применять к:** всем новым Python-файлам
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("admin")   # имя модуля
```

### Цвета и состояния баннера (CSS)
**Источник:** `uploader/app.py` строки 562–564
**Применять к:** HTML-шаблону `PAGE` в `admin.py`
```css
.status.ok   { background:#ecfdf5; color:#065f46; }
.status.err  { background:#fef2f2; color:#991b1b; }
.status.info { background:#eff6ff; color:#1e40af; }
```

### JavaScript: fetch + show(kind, text)
**Источник:** `uploader/app.py` строки 630–633, 762–778
**Применять к:** всем fetch-запросам из JS в `admin.py`
```javascript
async function apiCall(url, opts = {}) {
  try {
    const r = await fetch(url, { method: "POST", ...opts });
    const d = await r.json();
    show(d.ok ? "ok" : "err", d.message);
    return d;
  } catch (e) {
    show("err", "Ошибка соединения. Попробуйте ещё раз.");
    return null;
  }
}
```

### JavaScript: живой поиск с debounce
**Источник:** нет прямого аналога в кодовой базе (первое использование debounce)
**Применять к:** полю поиска на главном экране панели
**Паттерн (из RESEARCH / стандартный):**
```javascript
let searchTimer = null;
searchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => filterProducts(searchInput.value), 300);
});
function filterProducts(query) {
  const q = query.trim().toLowerCase();
  document.querySelectorAll(".product-card").forEach(card => {
    const name = card.dataset.name || "";
    card.style.display = (q === "" || name.includes(q)) ? "" : "none";
  });
}
```

---

## Без аналога в кодовой базе

| Файл | Роль | Поток данных | Причина |
|------|------|--------------|---------|
| Tabler CSS-компоненты (nav-tabs, badge, card, dropzone) | UI-шаблон | — | В проекте нет Tabler; аналог — inline-стили `app.py`, но Tabler-классы берутся из CDN-документации |
| Живой фильтр-поиск с debounce | JS-утилита | event-driven | В `app.py` поиска нет; паттерн стандартный, не требует аналога |

**Для плановика:** эти два элемента реализуются по документации Tabler
(https://preview.tabler.io/cards.html, /badges.html, /nav.html)
и стандартному debounce-паттерну, а не по кодовой базе.

---

## Карта аналогов (сводная)

**Область поиска:** `uploader/`, `scripts/`
**Файлов просмотрено:** 4 (`app.py`, `upload.py`, `upload_photos.py`, `.env.example`)
**Дата составления:** 2026-06-07

---

*Этап: 04 — Админ-панель владельца*
*Карта паттернов составлена: 2026-06-07*
