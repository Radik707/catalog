---
phase: 04-1-admin-panel
plan: 04
subsystem: admin-panel
tags: [deploy, daniella, systemd, nginx, cloudinary, env, sysadmin]
dependency_graph:
  requires: [04-1-admin-panel-03]
  provides: [admin_panel_live, env_documented]
  affects: [uploader/.env.example]
tech_stack:
  added: [cloudinary 1.44.2 (на сервере)]
  patterns: [git-pull-deploy, systemd-EnvironmentFile, additive-env-write, clean-backup-restore]
key_files:
  created: []
  modified:
    - uploader/.env.example
decisions:
  - D-01: панель развёрнута боевым образом на daniella в составе приложения загрузчика (один процесс catalog-uploader, отдельный секрет ADMIN_SECRET), а не как отдельный сайт
key-decisions:
  - D-01 подтверждён на проде — панель живёт внутри загрузчика, доступ по отдельному ADMIN_SECRET
metrics:
  duration: "~деплой-сессия"
  completed: "2026-06-07"
  tasks_completed: 2
  tasks_pending: 1
  files_created: 0
  files_modified: 1
---

# 04-04 — Боевой запуск админ-панели на daniella

## Что сделано

### Task 1 — `uploader/.env.example` (готово, коммит 2cedd26)
Документированы новые переменные панели с пустыми значениями: `ADMIN_SECRET`
(с подсказкой генерации и пометкой «не равен APP_SECRET»), `CLOUDINARY_CLOUD_NAME`,
`CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, `GOOGLE_SHEETS_ID`,
`GOOGLE_CREDENTIALS_PATH`. Реальные секреты в git не попадают.

### Task 2 — Деплой на сервере daniella (готово, проверено)
Развёрнуто через серверные операции (часть — субагент sysadmin, финальная запись
секретов — владельцем-санкционированная команда из-за защиты среды от утечки ключей):

- `git pull --ff-only`: сервер обновлён `93ae7f4 → 2cedd26` (весь код этапа 4).
- `pip install`: установлен `cloudinary 1.44.2` (требовалось ≥1.40) в `/opt/apps/catalog/.venv`.
- `uploader/.env` (0600, EnvironmentFile службы): аддитивно добавлены `ADMIN_SECRET`
  (свежий token_urlsafe(32), отдельный от APP_SECRET), `CLOUDINARY_*` (из корневого
  окружения проекта), `GOOGLE_SHEETS_ID` (из scripts/.env), `GOOGLE_CREDENTIALS_PATH`.
  APP_SECRET и Telegram-блок не тронуты. Сделан бэкап перед правкой.
- `systemctl restart catalog-uploader` → служба `active`.

**Проверки со стороны сервера (все зелёные):**
- Панель по верному секрету → HTTP 200
- Неверный секрет → HTTP 404 (раздельный доступ от загрузчика)
- `CLOUDINARY_*` в .env → 3 строки; `ADMIN_SECRET` задан
- Служба `catalog-uploader` → active (регрессии загрузчика нет — тот же процесс поднялся)

URL панели: `https://uploader.zhukoleg.ru/<ADMIN_SECRET>/` (секрет хранится только в
`uploader/.env` на сервере и у владельца; в git и артефакты не записывается).

## Что осталось (Task 3 — приёмка владельцем)

Сквозная проверка на живом телефоне владельца (7 пунктов): список «требуют внимания»,
404 на неверный секрет, смена группы → строка group в «Правках», правка названия →
строка name, привязка фото с камеры → строка photo + отклонение не-картинки,
«Применить сейчас» → пересборка и PROCESS_LOCK. Это ручная приёмка — выполняется
владельцем, после неё этап закрывается окончательно.

## Заметки
- Среда Claude Code блокирует автоматическую запись значений API-ключей на удалённый
  хост (анти-утечка) — финальную команду записи секретов выполнял владелец/координатор
  по явному разрешению. Учесть в будущих деплоях с секретами.
- SSH на daniella выдаёт предупреждение об отсутствии post-quantum обмена ключами
  (старый OpenSSH) — косметика, кандидат в todo на апгрейд.
- Раскладка конфигов: корневого `.env` на сервере нет; `GOOGLE_SHEETS_ID` в
  `scripts/.env`; Cloudinary-ключи теперь и в `uploader/.env`.
