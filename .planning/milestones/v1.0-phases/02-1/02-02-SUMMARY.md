---
phase: 02-1
plan: "02"
subsystem: uploader
tags: [deploy, daniella, e2e-verification, async, telegram, production]
dependency_graph:
  requires: [async-update, history-endpoint, double-launch-guard]
  provides: [production-async-uploader]
  affects: [uploader/app.py (на сервере), служба catalog-uploader]
tech_stack:
  added: []
  patterns: [git pull --ff-only, systemctl restart, curl e2e checks, sysadmin subagent]
key_files:
  modified: [.gitignore]
decisions:
  - "Деплой через git pull --ff-only (не scp): хеш рабочего app.py на сервере совпал с origin/main, force/reset не понадобился"
  - "Все серверные операции — через субагента sysadmin, не прямой ssh (правило проекта server-via-sysadmin)"
  - "uploader/history.json добавлен в .gitignore — рантайм-журнал с именами файлов не должен попадать в публичный репозиторий"
  - "Контрольный прогон — реальный, с записью (решение владельца на checkpoint): честная сквозная проверка под защитой бэкапа"
metrics:
  completed: "2026-06-07"
  tasks_completed: 4
  files_modified: 1
---

# Этап 2, План 2: Деплой на daniella + боевая сквозная проверка

**Суть:** Переделанный в Wave 1 загрузчик доставлен на боевой сервер daniella через субагента sysadmin, служба перезапущена, асинхронный сценарий подтверждён сквозной проверкой с реальной записью в каталог. Владелец подтвердил работу с телефона.

## Что сделано

### Checkpoint 1 (human-verify): подтверждение обстановки
Владелец подтвердил: 02-01 закоммичен, sysadmin доступен, оператор не активен. Режим проверки выбран — **реальный прогон с записью** (под защитой бэкапа).

### Task 1: Деплой через sysadmin
- `cd /opt/apps/catalog && git pull --ff-only` → чисто до `17e361f` (включает `441da13` с переделкой). На сервере была локальная правка `scripts/upload.py`, но её хеш совпал с `origin/main` — безопасный `git checkout` + ff-pull, без потери контента, без force/reset.
- `py_compile` серверного `app.py` → OK.
- `grep _process_async` = 5, `grep acquire(blocking=False)` = 1 — новая версия на сервере.
- `systemctl restart catalog-uploader` → `active`, gunicorn слушает 127.0.0.1:8000.
- Страница: верный токен → HTTP 200 (loopback и публичный HTTPS), неверный токен / корень → 404.

### Task 2: Сквозная проверка (реальный прогон)
- Пустая папка: `POST /update` → `ok=false, "Нет файлов для обновления."`
- `GET /history` → `{history: [...]}`, поля записи `id, ts, status, count, result_text, files`; неверный токен → 404.
- Реальный прогон (партия из last_batch): `POST /update` → ответ за **0.0056 с**, `ok=true, "Файлы отправлены, обработка идёт."`, без числа товаров.
- Двойной запуск: второе нажатие → `ok=false, "Обработка уже идёт, подождите."`; в journalctl **один** «Запуск upload.py» — второй upload.py не стартовал.
- История: `processing` (count=null) → финал `ok` (count=**871**, «Загружено 871 товаров»), тот же `id`.
- Персистентность: после `systemctl restart` запись в `/history` сохранилась (history.json на диске, mode 600).
- Безопасность каталога: число товаров после прогона = 871 (не обрушилось); лист «Товары_BACKUP» (942) на месте, бэкап делается ДО записи.
- Telegram: `OWNER_CHAT_ID` привязан, фоновый `notify("plain", ...)` ушёл владельцу; канал подтверждён живым через SOCKS5-прокси.

### Попутная правка (senior decision)
`uploader/history.json` не был в `.gitignore` — добавлен (коммит `061d4d1`). Файл создаётся новым кодом 02-01 и содержит имена загруженных файлов; без игнора при `git add --all` история могла уехать в публичный репозиторий.

### Checkpoint 2 (human-verify): подтверждение владельца
Владелец проверил с телефона по секретной ссылке — «всё работает».

## Deviations from Plan

### git pull вместо возможного scp
План допускал scp как запасной путь. Реально хватило `git pull --ff-only` — локальная правка на сервере оказалась идентична будущему коммиту (сверка хешем), что позволило чистый fast-forward.

### Дополнительная правка .gitignore
Вне исходного списка задач, но прямо вытекает из новой фичи (history.json). Закрыто сразу как очевидный и безопасный риск утечки.

## Verification Evidence

```
git pull --ff-only                                  → 17e361f (включает 441da13)
py_compile (сервер)                                 → OK
grep _process_async (сервер)                        → 5
grep acquire(blocking=False) (сервер)               → 1
systemctl is-active catalog-uploader                → active
HTTP верный токен / неверный токен                  → 200 / 404
POST /update пустая папка                           → ok=false «Нет файлов»
POST /update с файлами, время ответа                → 0.0056 с, ok=true «Файлы отправлены»
POST /update двойной (journalctl «Запуск upload.py»)→ 1
/history: processing → ok (count=871)               → подтверждено
персистентность после restart                       → запись сохранилась
sheet_tool.py count после прогона                   → 871 (бэкап «Товары_BACKUP» 942)
Telegram владельцу (notify plain)                   → доставлено
```

## Commits

| Задача | Коммит | Описание |
|--------|--------|----------|
| Попутная правка | `061d4d1` | fix(этап-2): добавлен uploader/history.json в .gitignore |
| Деплой/проверка | — | серверные операции (git pull/restart на daniella) не дают коммитов в этом репозитории; зафиксированы в inventory сисадмином (`93b7da6` в /opt/infra) |

## Known Stubs

Нет. Сценарий подтверждён в бою end-to-end.

## Threat Flags

- T-02b-02 (раскрытие секретов): закрыто — токен/`.env`/`credentials.json` не читались и не выводились (плейсхолдер `<TOKEN>`).
- T-02b-04 (прямой ssh в обход правил): закрыто — всё через субагента sysadmin.
- Новое: `Товары_NEW` (11 строк) — отложенная партия от прошлых тестов (stash_new), не от этого прогона; при желании удаляется вручную. Не блокирует.

## Self-Check: PASSED

- Серверный `uploader/app.py` содержит `_process_async` + `acquire(blocking=False)`: FOUND
- Служба `active` после рестарта: PASSED
- Сквозной сценарий (мгновенный отклик, фон, двойной запуск, история, персистентность): PASSED
- Telegram владельцу: PASSED
- Каталог цел (871, бэкап есть): PASSED
- Владелец подтвердил с телефона: PASSED
