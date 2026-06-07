---
phase: 01-1
plan: 02
subsystem: infra
tags: [deploy, scp, dry-run, upload.py, google-sheets, 1c-format]

requires:
  - phase: 01-01
    provides: проверенный 29 тестами upload.py (парсер двух форматов 1С)
provides:
  - Проверенный upload.py доставлен на сервер daniella (/opt/apps/catalog/scripts/upload.py)
  - Dry-run на реальных файлах нового формата подтвердил счёт 871 товара и 139 новинок (16%) без записи в каталог
  - Допуск владельца к боевому прогону (решение proceed)
affects: [01-03]

tech-stack:
  added: []
  patterns:
    - "Серверные операции выполняются через субагента sysadmin, не напрямую"
    - "Скрипты на сервере запускаются через venv /opt/apps/catalog/.venv (системный python3 не видит gspread)"

key-files:
  created: []
  modified:
    - scripts/upload.py (доставлен на сервер; локально без изменений в этом плане)

key-decisions:
  - "Доставка только одного файла через scp (без git pull/push и без боевой пересборки Vercel на этом шаге)"
  - "Боевой прогон допущен: 871 товар в норме, новинок 16% — намного ниже тревожного порога 40%"

patterns-established:
  - "Предполётная проверка сервера (SSH, файлы, нет конфликтующих процессов) перед любым серверным действием"
  - "Dry-run с проверкой count до/после как доказательство отсутствия записи"

requirements-completed: [FMT-05, FMT-02, GRP-01, GRP-02]

duration: ~3min
completed: 2026-06-07
---

# Этап 1 / План 02: Деплой + холостой прогон — Summary

**Проверенный upload.py доставлен на daniella; dry-run на реальных файлах нового формата 1С дал ровно 871 товар и 139 новинок (16%) без записи в каталог — владелец допустил боевой прогон**

## Performance

- **Duration:** ~3 мин (серверные операции через sysadmin)
- **Completed:** 2026-06-07
- **Tasks:** 4 (2 checkpoint + 2 auto)
- **Files modified:** 1 (upload.py доставлен на сервер)

## Accomplishments
- Предполётная проверка сервера пройдена: SSH OK, три файла нового формата 1С в last_batch, конфликтующих обновлений нет
- upload.py доставлен на сервер через scp (31526 байт, COMPILE_OK, parse_new_format присутствует)
- Dry-run на /opt/apps/catalog/uploader/last_batch: **871 товар** из 3 файлов (Ефимова 147, Лазуткина 109, Пелих 615)
- Новинок **139 (~16%)** — устойчивая группировка по названию (загружено 930 текущих групп для сопоставления)
- Запись НЕ произошла: COUNT 931 до = 931 после
- Владелец принял решение **proceed** — допуск к боевому прогону

## Task Commits

Серверные операции (scp, dry-run) не порождают локальных коммитов кода — upload.py локально не менялся в этом плане. Зафиксированы только документация и трекинг этапа:

- **Checkpoint 1 (human-verify):** доступ к серверу подтверждён через sysadmin
- **Task 1 (доставка кода):** scp upload.py → сервер; COMPILE_OK, grep parse_new_format = 2
- **Task 2 (dry-run):** 871 товар / 139 новинок / запись отсутствует
- **Checkpoint 2 (decision):** proceed
- **Plan metadata:** docs-коммит (SUMMARY + STATE + ROADMAP)

## Files Created/Modified
- `scripts/upload.py` — доставлен на сервер в /opt/apps/catalog/scripts/upload.py (локально без изменений)

## Decisions Made
- Доставка одного файла через scp, без git pull/push и без пересборки Vercel на этом шаге (публикация фронтенда — отдельный шаг перед группой 3)
- Боевой прогон допущен по результатам dry-run (счёт в норме, новинок 16%)

## Deviations from Plan

### Auto-fixed Issues

**1. [Окружение] Запуск через venv вместо системного python3**
- **Found during:** Task 2 (dry-run)
- **Issue:** системный `python3` на сервере не видит gspread (ModuleNotFoundError)
- **Fix:** dry-run и sheet_tool.py запускались через `/opt/apps/catalog/.venv/bin/python3` — тот же интерпретатор, что использует служба catalog-uploader
- **Verification:** dry-run отработал, count прочитан корректно
- **Impact:** боевой прогон через службу пойдёт тем же venv — соответствие соблюдено

---

**Total deviations:** 1 (окружение, не влияет на корректность)
**Impact on plan:** Без влияния на результат — учтено для группы 3.

## Issues Encountered
- Незначительное предупреждение: 17 товаров без категории попали в «Другое»; одна пустая категория в предупреждении парсера — некритично.

## User Setup Required
Доступ к серверу daniella (ssh my-vps) — подтверждён. Боевой прогон выполняется через путь uploader под наблюдением владельца.

## Next Phase Readiness
- Код на сервере готов и проверен; цифры адекватны
- Перед группой 3 требуется опубликовать фронтенд-правку Wave 1 (строка «Новинки» в GROUP_ORDER) на Vercel
- Боевой прогон выполнять ТОЛЬКО штатным путём с бэкапом (через uploader / backup→upload→count)

---
*Phase: 01-1*
*Completed: 2026-06-07*
