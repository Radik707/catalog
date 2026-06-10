---
phase: 02-1
plan: "01"
subsystem: uploader
tags: [async, threading, history, flask, operator-ux]
dependency_graph:
  requires: []
  provides: [async-update, history-endpoint, double-launch-guard]
  affects: [uploader/app.py]
tech_stack:
  added: [threading.Lock, json history persistence, tempfile atomic write, secrets.token_hex]
  patterns: [daemon thread, acquire(blocking=False), atomic temp+os.replace, JS polling]
key_files:
  modified: [uploader/app.py]
decisions:
  - "PROCESS_LOCK через threading.Lock; acquire(blocking=False) — единственный источник правды «идёт обработка»"
  - "Атомарная запись history.json через tempfile.mkstemp + os.replace — защита от повреждения при сбое"
  - "entry_id = secrets.token_hex(8) — уникальный ключ для последующего обновления записи"
  - "Поллинг /history каждые 4 секунды; останавливается когда нет записей со status=processing"
  - "updateBtn разблокируется немедленно после ответа /update — повторный клик получит «Обработка уже идёт»"
metrics:
  duration: "188 секунд (~3 мин)"
  completed: "2026-06-07"
  tasks_completed: 2
  files_modified: 1
---

# Этап 2, План 1: Асинхронный загрузчик — журнал истории и фоновая обработка

**Суть:** Синхронный /update (браузер ждёт несколько минут) заменён на мгновенный нейтральный ответ оператору + фоновый поток с защитой двойного запуска, персистентным журналом истории и поллингом на странице.

## Что реализовано

### Task 1: Журнал истории и фоновая обработка с защитой двойного запуска

Добавлено в `uploader/app.py`:

- Константа `HISTORY_FILE` с env-дефолтом (`SCRIPT_DIR/history.json`)
- Глобальный `PROCESS_LOCK = threading.Lock()` — защита от двойного запуска
- `load_history()` — читает JSON, при отсутствии/битом файле возвращает `[]`
- `append_history(entry)` — вставляет в начало, обрезает до 10, возвращает `entry_id`
- `update_history(entry_id, **fields)` — обновляет запись по id
- `_save_history_atomic()` — `tempfile.mkstemp` + `os.replace` (атомарно)
- `_process_async(entry_id)` — вся оркестровка в фоне: backup → run_upload → warn/stash/rollback → notify → update_history; Lock освобождается в `finally`

### Task 2: Асинхронный /update, endpoint /history и таблица истории на странице

Изменено в `uploader/app.py`:

- `POST /<token>/update` — мгновенно: захватывает Lock без ожидания; если занят — `ok=False, "Обработка уже идёт"`; если свободен — `append_history(processing)` + `Thread(daemon).start()` + немедленный `ok=True, "Файлы отправлены"`
- `GET /<token>/history` — новый endpoint под токеном; отдаёт `{history: [...]}` без трассировок
- `PAGE` (HTML/CSS/JS): добавлена таблица `#history` с колонками «Время · Файлы · Итог»; `loadHistory()` рендерит строки, `processing` → «⏳ обрабатывается…»; поллинг каждые 4 с через `setInterval`, останавливается когда processing исчезла; кнопка «Откатить» не изменена

## Цепочка данных

```
POST /update → acquire(Lock) → append_history(processing) → Thread.start()
                                                               ↓
                            ← jsonify(ok=True, «Файлы отправлены»)

Thread: backup → run_upload → warn/stash/rollback → notify(владелец) → update_history(ok/warn/error)
        ↓ finally: Lock.release()

GET /history → load_history() → [{id, ts, status, count, result_text, files}, ...]
JS loadHistory() → renderHistory() → поллинг 4s пока processing → остановка
```

## Deviations from Plan

### Отклонений от плана нет

Оба задания реализованы в одном Write-вызове, что привело к единому коммиту вместо двух. Поскольку файл был один (`uploader/app.py`) и логика неразрывна (Task 2 использует функции Task 1), разбивка на два коммита потребовала бы промежуточного незаконченного состояния. Все функции Task 1 проверены AST до коммита, все проверки Task 2 прошли после.

## Verification Evidence

```
python -m py_compile uploader/app.py                        → OK
AST: _process_async, load_history, append_history, update_history → FOUND
grep threading.Lock                                          → строка 82
grep os.replace (history)                                   → строка 113
grep "processing"                                           → строки 470, 672, 676, 699
grep result_text                                            → строки 166, 186, 207, 217, 232, 472, 678
grep acquire(blocking=False)                                → строка 461
grep "Файлы отправлены"                                     → строка 481
grep "Обработка уже идёт"                                   → строка 463
grep @app.get.*history                                      → строка 484
grep loadHistory                                            → строки 693, 710, 736, 765
grep /rollback                                              → строки 495-499 (не изменён)
Task 2 automated verify script                              → exit 0
```

## Commits

| Задача | Коммит | Описание |
|--------|--------|----------|
| Task 1 + Task 2 | `441da13` | feat(этап-2): журнал истории и фоновая обработка с защитой двойного запуска |

## Known Stubs

Нет. Все функции подключены к реальной логике. История пустая до первого запуска — это штатное поведение.

## Threat Flags

Нет новой поверхности атаки. Endpoint `/history` защищён через `check(token)` (T-02a-04 из плана). `result_text` не содержит трассировок (T-02a-01).

## Self-Check: PASSED

- `uploader/app.py` существует: FOUND
- Коммит `441da13` существует: FOUND
- Все функции из плана (AST-проверка): PASSED
- py_compile: PASSED
- Task 2 automated verify: PASSED
