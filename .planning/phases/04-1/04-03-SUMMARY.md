---
phase: 04-1-admin-panel
plan: 03
subsystem: admin-panel
tags: [flask, cloudinary, photo-upload, admin, dropzone, mobile]
dependency_graph:
  requires: [04-1-admin-panel-02]
  provides: [cloudinary_helper_cli, photo_upload_route, photo_dropzone_ui]
  affects: [scripts/cloudinary_helper.py, uploader/admin.py, uploader/requirements.txt]
tech_stack:
  added: [cloudinary>=1.40, tempfile, FormData multipart]
  patterns: [shell-out-cloudinary, file-validation-before-upload, tmp-file-cleanup, drag-and-drop-ui, mobile-camera-input]
key_files:
  created:
    - scripts/cloudinary_helper.py
  modified:
    - uploader/admin.py
    - uploader/requirements.txt
decisions:
  - D-06: фото грузится с телефона (capture=environment) в Cloudinary presenter/; привязка типа photo в «Правках» в формате presenter/<stem>.<ext>; overwrite=True — замена = та же операция
key-decisions:
  - D-06 реализован полностью — загрузка с телефона через /photo, папка всегда presenter/, overwrite=True
metrics:
  duration: "~10 мин"
  completed: "2026-06-07"
  tasks_completed: 3
  files_created: 1
  files_modified: 2
---

# Этап 04-1, План 03: загрузка фото через Cloudinary из панели (тип photo)

**Одной строкой:** Владелец выбирает фото с телефона в Dropzone-зоне, файл валидируется на клиенте и сервере (JPG/PNG/WebP, ≤10 МБ), загружается в Cloudinary папку presenter/ через cloudinary_helper.py, привязка типа photo записывается в «Правки» — товар показывается с фото при следующей пересборке.

## Что сделано

### Task 1: scripts/cloudinary_helper.py

Новый скрипт-утилита, вызываемый через shell-out из admin.py:

- **load_env()** — загружает .env из PROJECT_ROOT / SCRIPT_DIR (паттерн upload_photos.py)
- **init_cloudinary()** — проверяет наличие всех трёх ключей; при отсутствии → JSON `{ok:false, message:"Cloudinary не настроен"}` и rc=1 (graceful, T-04-11)
- **get_ref(original_name)** → `"presenter/<stem>.<ext>"` — формат привязки для «Правок»
- **get_public_id(original_name)** → `"presenter/<stem>"` — public_id без расширения для Cloudinary
- **upload_file(tmp_path, original_name)** — `cloudinary.uploader.upload()` с `overwrite=True`, `eager=[{"format":"webp","quality":"auto"}]`, `eager_async=True`; JSON `{ok:true, ref, url}` в stdout UTF-8
- **CLI** — `python cloudinary_helper.py upload --path <tmp> --name <original>`
- Ошибки Cloudinary → JSON `{ok:false, message:"Не удалось загрузить фото"}` + rc=1; детали только в stderr-лог (T-04-11)

### Task 2: uploader/admin.py — маршрут /photo + Dropzone

**Новые константы:**
- `CLOUDINARY_HELPER` — путь к scripts/cloudinary_helper.py
- `ALLOWED_PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp"}` — белый список расширений (T-04-09)
- `ALLOWED_PHOTO_MIMES = {"image/jpeg", "image/png", "image/webp"}` — белый список MIME (T-04-09)
- `MAX_PHOTO_BYTES = 10 * 1024 * 1024` — лимит 10 МБ (T-04-09, T-04-10)

**Новый маршрут POST `/<token>/photo`:**
1. Валидация расширения и MIME до чтения файла
2. Читает байты, проверяет размер ≤ 10 МБ — всё до `_run_py` (T-04-09)
3. Сохраняет в `tempfile.NamedTemporaryFile(suffix=ext, delete=False)`
4. `_run_py(CLOUDINARY_HELPER, "upload", "--path", tmp, "--name", orig)` → JSON результат
5. `_run_py(SHEET_HELPER, "append_edit", "--key", key, "--type", "photo", "--value", ref)`
6. `finally: os.unlink(tmp_path)` — удаление при любом исходе (T-04-10)

**Расширение `/save`:** белый список расширен до `{"group", "name", "photo"}`; для photo допускается пустое значение (сброс привязки).

**HTML экрана 2 — зона загрузки:**
- CSS: `.photo-drop` с пунктирной рамкой, drag-over состояние, `.photo-preview`
- `<input type="file" id="photo-input" accept="image/*" capture="environment">` (скрыт, открывается по клику на зону)
- Текст «Нажмите или перетащите фото» + hint «JPG, PNG, WebP — до 10 МБ»
- `<img id="photo-preview">` — превью выбранного/текущего фото
- `<button id="btn-reset-photo">Сбросить фото</button>` — видна при наличии привязки

**JS-логика:**
- `initDropZone()` — drag-and-drop события
- `handlePhotoFile(file)` — клиентская валидация (ext, size) + FileReader превью + FormData POST `/photo` + обновление состояния
- `resetPhoto()` — отправляет пустую photo-правку через `/save`
- `showEditScreen` обёрнута: при открытии экрана правки загружает текущее фото в превью

### Task 3: uploader/requirements.txt

Добавлена строка `cloudinary>=1.40` с русским комментарием. Пакет верифицирован на Task 0 (PyPI, официальный SDK Cloudinary, github.com/cloudinary/pycloudinary).

## Критерии приёмки — все PASS

| Критерий | Статус |
|----------|--------|
| ast.parse scripts/cloudinary_helper.py → ok | PASS |
| cloudinary_helper: cloudinary.uploader.upload, presenter/, eager | PASS |
| cloudinary_helper: graceful JSON ok:false при отсутствии ключей, rc=1 | PASS |
| ast.parse uploader/admin.py → ok | PASS |
| admin.py: маршрут /photo, валидация ext/mime/size ДО Cloudinary | PASS |
| admin.py: input[accept=image/* capture=environment] | PASS |
| admin.py: текст «JPG, PNG, WebP — до 10 МБ» | PASS |
| admin.py: временный файл удаляется в finally | PASS |
| uploader/requirements.txt содержит cloudinary>=1.40 | PASS |

## Отклонения от плана

Нет — план выполнен точно как написан.

## Покрытие решений

| Решение | Реализовано |
|---------|-------------|
| D-06: фото с телефона в presenter/, тип photo, overwrite | cloudinary_helper.py + admin.py /photo |

## Угрозы — все смягчены (T-04-09..T-04-12, T-04-SC)

| Угроза | Митигация |
|--------|-----------|
| T-04-09 Tampering: не-изображение или большой файл | валидация ext+mime+size ДО любого _run_py |
| T-04-10 DoS: диск переполнен tmp-файлами | tempfile + finally os.unlink |
| T-04-11 Info Disclosure: ключи Cloudinary в ответе | ключи только в .env; клиенту нейтральные строки |
| T-04-12 Supply chain: подмена cloudinary | Task 0 — блокирующая проверка PyPI; версия >=1.40 |
| T-04-SC: pip install | Task 0 пройден; установка на сервере — план 04 через sysadmin |

## Следующий план

**04-04**: деплой через субагента sysadmin — установка cloudinary на сервере, перезапуск службы, боевая проверка загрузки фото с телефона.

## Self-Check: PASS

- `python -c "import ast; ast.parse(open('scripts/cloudinary_helper.py',encoding='utf-8').read())"` → ok
- `python -c "import ast; ast.parse(open('uploader/admin.py',encoding='utf-8').read())"` → ok
- `python -X utf8 -c "src=open('scripts/cloudinary_helper.py'...).read(); assert 'cloudinary.uploader.upload' in src and 'presenter/' in src and 'eager' in src"` → ok
- `python -X utf8 -c "src=open('uploader/requirements.txt'...).read(); assert 'cloudinary' in src"` → ok
- Коммиты: d21c8fa, 7d6b963, 895ed24 — все существуют в git log
