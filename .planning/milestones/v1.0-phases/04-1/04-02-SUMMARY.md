---
phase: 04-1-admin-panel
plan: 02
subsystem: admin-panel
tags: [flask, upload, google-sheets, admin, edit-memory, display-name]
dependency_graph:
  requires: [04-1-admin-panel-01]
  provides: [upload_name_type, admin_name_field, server_normalize]
  affects: [scripts/upload.py, uploader/admin.py]
tech_stack:
  added: []
  patterns: [edit-memory-extension, display-name-override, server-side-normalize]
key_files:
  created: []
  modified:
    - scripts/upload.py
    - uploader/admin.py
decisions:
  - D-05: тип правки name реализован; ключ сопоставления normalize_name(p["name"]) не меняется
  - D-07: цена не редактируется; PLAN_02_ALLOWED_TYPES = {"group", "name"} — явный белый список
metrics:
  duration: "~8 мин"
  completed: "2026-06-07"
  tasks_completed: 2
  files_created: 0
  files_modified: 2
---

# Этап 04-1, План 02: правка отображаемого названия товара (тип name)

**Одной строкой:** Тип правки `name` добавлен в upload.py и admin.py — владелец исправляет кривое название из прайса в панели, каталог отображает новое имя, ключ сопоставления normalize_name остаётся неизменным.

## Что сделано

### Task 1: scripts/upload.py — поддержка типа правки `name`

Три точечных изменения по карте паттернов:

1. **ALLOWED_TYPES** (строка 371): добавлен `"name"` к `{"group", "photo", "description"}` — строка с типом `name` во вкладке «Правки» больше не отвергается как неизвестный тип.

2. **apply_edit_memory**: добавлен блок `if "name" in edit: p["display_name"] = edit["name"]` с комментарием. Ключ сопоставления `normalize_name(p["name"])` не меняется — правка затрагивает только поле `display_name` (D-05).

3. **products_to_rows**: первая колонка «Наименование» теперь = `p.get("display_name") or p["name"]`. Функции `get_badge`, `get_photo_url`, `get_photo_description` по-прежнему получают `p["name"]` — ключ из прайса не подменён.

### Task 2: uploader/admin.py — поле «Отображаемое название» + /save type=name

1. **normalize_name()** добавлена прямо в admin.py (без зависимостей, 2 строки) — копия из upload.py. Теперь ключ правки нормализуется на сервере в `/save` для обоих типов (T-04-06, D-05).

2. **PLAN_02_ALLOWED_TYPES = {"group", "name"}** — заменил PLAN_01_ALLOWED_TYPES. Цена сознательно отсутствует (D-07).

3. **Экран 2 (форма правки)**: добавлено поле `<input id="edit-display-name">` с меткой «Отображаемое название» и hint «Оставьте пустым, чтобы использовать название из прайса» — над полем «Группа».

4. **showEditScreen**: предзаполнение `display_name` из объекта товара; функция `checkChanged` активирует кнопку «Сохранить правку» при изменении любого из двух полей (или обоих).

5. **saveEdit**: последовательная отправка правок — сначала `type: "name"` (если изменилось название), затем `type: "group"` (если изменилась группа). Обновляет `allProducts` в памяти после успешного сохранения. Сообщение успеха из UI-SPEC.

## Критерии приёмки — все PASS

| Критерий | Статус |
|----------|--------|
| ALLOWED_TYPES содержит "name" | PASS |
| apply_edit_memory: `p["display_name"] = edit["name"]` | PASS |
| products_to_rows: `p.get("display_name") or p["name"]` в первой колонке | PASS |
| get_badge/get_photo_url/get_photo_description по-прежнему с p["name"] | PASS |
| ast.parse upload.py → ok | PASS |
| uploader/admin.py: «Отображаемое название» + hint | PASS |
| /save белый список включает "name" | PASS |
| normalize_name на сервере применяется к ключу правки | PASS |
| ast.parse admin.py → ok | PASS |

## Отклонения от плана

Нет — план выполнен точно как написан.

## Покрытие решений

| Решение | Реализовано |
|---------|-------------|
| D-05: ключ сопоставления не меняется при правке name | upload.py (normalize_name остаётся по p["name"]) + admin.py (normalize на сервере) |
| D-07: цена не редактируется в панели | PLAN_02_ALLOWED_TYPES = {"group", "name"} — без price |

## Угрозы — все смягчены

| Угроза | Митигация |
|--------|-----------|
| T-04-06 Tampering: подмена ключа через правку name | apply_edit_memory меняет только display_name; normalize_name(p["name"]) — ключ неизменен |
| T-04-07 Tampering: мусорный type в «Правки» | ALLOWED_TYPES в upload.py + PLAN_02_ALLOWED_TYPES в admin.py /save |
| T-04-08 Injection: значение в лист «Товары» | значение пишется как данные; риск принят (accepted в threat model) |

## Следующий план

**04-03**: загрузка фото через Cloudinary из панели (тип `photo`, экран 3).

## Self-Check: PASS

- `python -c "import ast; ast.parse(open('scripts/upload.py',encoding='utf-8').read())"` → ok
- `python -c "import ast; ast.parse(open('uploader/admin.py',encoding='utf-8').read())"` → ok
- display_name, тип "name" присутствуют в обоих файлах — проверено
- Коммиты: dffd4b6 (upload.py), 637a1ad (admin.py) — существуют в git log
