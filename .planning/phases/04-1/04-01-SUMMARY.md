---
phase: 04-1-admin-panel
plan: 01
subsystem: admin-panel
tags: [flask, google-sheets, admin, auth, blueprint]
dependency_graph:
  requires: []
  provides: [sheet_helper_cli, admin_blueprint, admin_routes_mounted]
  affects: [uploader/app.py, scripts/sheet_helper.py]
tech_stack:
  added: [Flask Blueprint, gspread shell-out, Tabler CSS CDN]
  patterns: [hmac-secret-auth, shell-out-subprocess, graceful-fallback, whitelist-validation, XSS-esc]
key_files:
  created:
    - scripts/sheet_helper.py
    - uploader/admin.py
  modified:
    - uploader/app.py
    - uploader/.env.example
decisions:
  - D-01: панель — Blueprint в Flask-приложении загрузчика, не отдельный сайт
  - D-02: ADMIN_SECRET отдельно от APP_SECRET, hmac.compare_digest → abort(404)
  - D-03: Tabler CSS CDN (только стили), mobile-first, container-sm 640px
  - D-04: главный экран «Требуют внимания» + вкладки-фильтры + debounce-поиск 300ms
  - D-05: правка группы через sheet_helper append_edit, тип group → «Правки»
  - D-08: «Применить сейчас» переиспользует PROCESS_LOCK и LAST_BATCH_DIR из app.py
metrics:
  duration: "~6 мин"
  completed: "2026-06-07"
  tasks_completed: 3
  files_created: 2
  files_modified: 2
---

# Этап 04-1, План 01: sheet_helper + admin.py — первый ломтик панели

**Одной строкой:** Flask Blueprint с авторизацией ADMIN_SECRET, Tabler CSS UI,
shell-out в sheet_helper.py (gspread) для чтения «Товаров» и записи «Правок», кнопка «Применить сейчас» через PROCESS_LOCK.

## Что сделано

Построен сквозной «ломтик» изменения группы товара:

1. **scripts/sheet_helper.py** — data-утилита Google Sheets:
   - `_get_spreadsheet()` — авторизация gspread (GOOGLE_CREDENTIALS_PATH или поиск credentials.json)
   - `load_products()` — читает лист «Товары», поля name/group/image_url/is_new
   - `load_edit_keys()` — множество ключей из «Правок» (для определения is_new, MEM-03)
   - `append_edit()` — запись строки в «Правки», создаёт вкладку при WorksheetNotFound
   - `normalize_name()` — скопировано из upload.py, без зависимостей
   - CLI: `list` / `append_edit --key/--type/--value` / `normalize --name`
   - Graceful-fallback `[]` при отсутствии credentials/gspread/ошибке сети
   - Белый список `ALLOWED_TYPES = {"group","photo","description","name"}` (T-04-02)

2. **uploader/admin.py** — Flask Blueprint admin_bp:
   - `check_admin()` — hmac.compare_digest, ADMIN_SECRET ≠ APP_SECRET (T-04-01, D-02)
   - `GET /<token>/` — одностраничный HTML (Tabler CSS, mobile-first, 640px)
   - `GET /<token>/products` — shell-out в sheet_helper list → jsonify
   - `POST /<token>/save` — тип "group" only (PLAN_01_ALLOWED_TYPES), записывает через shell-out
   - `POST /<token>/apply` — PROCESS_LOCK.acquire(blocking=False), проверка LAST_BATCH_DIR, фоновый поток
   - PAGE: фильтры «Требуют внимания/Новинки/Без группы/Без фото/Все», debounce-поиск, esc() XSS-защита

3. **uploader/app.py** — монтирование Blueprint:
   - `from admin import admin_bp` + `app.register_blueprint(admin_bp)`
   - Русский комментарий; отсутствие ADMIN_SECRET не ломает старт

4. **uploader/.env.example** — добавлены ADMIN_SECRET, Cloudinary, Google переменные этапа 4

## Критерии приёмки — все PASS

| Критерий | Статус |
|----------|--------|
| sheet_helper: `def load_products`, `def append_edit`, `def normalize_name`, `import argparse` | PASS |
| append_edit при WorksheetNotFound: add_worksheet("Правки") + append_row(заголовок) | PASS |
| `python sheet_helper.py list` rc=0, валидный JSON (871 товар) | PASS |
| ALLOWED_TYPES = {"group","photo","description","name"} | PASS |
| admin.py: ADMIN_SECRET, hmac.compare_digest, abort(404), /products /save /apply | PASS |
| /apply при пустом LAST_BATCH_DIR → «Прайсы ещё не загружались» | PASS |
| /apply: PROCESS_LOCK.acquire(blocking=False) | PASS |
| PAGE: Tabler CDN + вкладки «Требуют внимания»/«Без группы»/«Без фото»/«Все» | PASS |
| /save принимает только type="group" | PASS |
| ast.parse admin.py → ok | PASS |
| app.py: import admin_bp + register_blueprint + русский комментарий | PASS |
| ast.parse app.py → ok | PASS |

## Отклонения от плана

### Авто-исправленные проблемы

**1. [Rule 1 - Bug] Кодировка stdout на Windows cp1252**
- **Найдено при:** Task 1, первый запуск `python sheet_helper.py list`
- **Проблема:** `json.dumps` с кириллицей падал с UnicodeEncodeError (Windows консоль cp1252)
- **Исправление:** `sys.stdout.buffer.write(...encode("utf-8"))` вместо `print()`
- **Файлы:** `scripts/sheet_helper.py`

**2. [Rule 2 - Security] Бинарный вывод subprocess в admin.py**
- **Найдено при:** Task 2 (проектирование)
- **Обоснование:** `capture_output=True, text=True` + кириллица в stdout → риск той же UnicodeDecodeError на сервере с нестандартной локалью
- **Исправление:** `text=False` + ручное `.decode("utf-8", errors="replace")`
- **Файлы:** `uploader/admin.py`

**3. [Rule 2 - Security] Парсинг JSON из смешанного stdout/stderr**
- **Найдено при:** Task 2 (анализ sheet_helper output)
- **Обоснование:** sheet_helper пишет INFO-лог в stderr, JSON в stdout; при бинарном режиме они объединяются — нужно найти строку начинающуюся с `[`
- **Исправление:** поиск JSON-строки `[l for l in lines if l.startswith("[")]` перед `json.loads`
- **Файлы:** `uploader/admin.py`

## Покрытие решений

| Решение | Реализовано |
|---------|-------------|
| D-01 (панель в Flask загрузчика) | app.py + Blueprint |
| D-02 (ADMIN_SECRET отдельный) | check_admin() |
| D-03 (Tabler CSS, 640px) | PAGE в admin.py |
| D-04 (экран «Требуют внимания» + фильтры + поиск) | PAGE JS |
| D-05 (правка группы через «Правки») | /save + sheet_helper |
| D-08 (PROCESS_LOCK + LAST_BATCH_DIR) | /apply |

## Угрозы — все смягчены (T-04-01..T-04-05)

| Угроза | Митигация |
|--------|-----------|
| T-04-01 Spoofing | hmac.compare_digest(token, ADMIN_SECRET) → abort(404) |
| T-04-02 Tampering | ALLOWED_TYPES белый список в sheet_helper + PLAN_01_ALLOWED_TYPES в /save |
| T-04-03 DoS | PROCESS_LOCK.acquire(blocking=False) переиспользован из app.py |
| T-04-04 Info Disclosure | технические детали только в log, клиенту нейтральные строки из UI-SPEC |
| T-04-05 XSS | esc() перед каждой вставкой в innerHTML |

## Следующий план

**04-02**: правка отображаемого названия товара (тип `name`, экран 2 расширяется).

## Self-Check: PASS

Проверено командами:
- `python -c "import ast; ast.parse(...)" → ok` для sheet_helper.py, admin.py, app.py
- `python scripts/sheet_helper.py list` → rc=0, 871 товар, валидный JSON
- Коммиты: 70b3685, 0637322, d358171, 58dc1f3 — все существуют в git log
