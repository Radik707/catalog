---
phase: 03-1
plan: 02
subsystem: database
tags: [gspread, google-sheets, python, edit-memory, migration, override, upload-pipeline]

# Dependency graph
requires:
  - phase: 03-1-01
    provides: "load_edit_memory + apply_edit_memory в upload.py; схема вкладки «Правки» (Товар|Тип|Значение)"
provides:
  - "migrate_overrides.py — разовая CLI-утилита: PRODUCT_OVERRIDES/PRODUCT_CONTAINS_OVERRIDES → строки group во вкладке «Правки»"
  - "upload.py без захардкоженных словарей группировки: PRODUCT_OVERRIDES/PRODUCT_CONTAINS_OVERRIDES/apply_product_override удалены"
  - "apply_group_mapping сохранена: только category_map → display_group + «Другое» + лог немаппленных"
  - "34 group-правки перенесены в вкладку «Правки» Google Sheet (из 19 исходных правил)"
affects:
  - "этап 4 (админ-панель владельца — добавляет правки group без деплоя кода)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Раскрытие широких правил (префикс/подстрока) в точечные правки по точному normalize_name (D-04↔D-07)"
    - "Разовая миграция-утилита с --dry-run перед боевым запуском (T-03-06)"
    - "append-запись во вкладку (не clear) — защита ручных правок владельца"
    - "Боевой запуск на сервере только через субагента sysadmin (правило проекта)"

key-files:
  created:
    - "scripts/migrate_overrides.py — утилита миграции PRODUCT_OVERRIDES → вкладка «Правки»"
  modified:
    - "scripts/upload.py — удалены PRODUCT_OVERRIDES, PRODUCT_CONTAINS_OVERRIDES, apply_product_override; упрощена apply_group_mapping"

key-decisions:
  - "Миграция разовая и уже выполнена: после удаления словарей из upload.py повторный запуск migrate_overrides.py невозможен (это ожидаемо)"
  - "19 правил → 34 точечные group-правки по normalize_name: каждое широкое префиксное/подстрочное правило раскрылось в конкретные нормализованные имена текущего каталога"
  - "Боевая запись во вкладку «Правки» подтверждена: upload.py --dry-run лог «Загружено правок из памяти: 34» (было 0)"

patterns-established:
  - "expand_overrides(product_names) → {normalize_name: group} — чистая функция без сетевых вызовов, пригодна для локальной проверки"
  - "Семантический разрыв D-04↔D-07 разрешён через раскрытие: широкое правило → набор точных имён"

requirements-completed: [MEM-01]

# Metrics
duration: ~20min (с чекпоинтом через sysadmin)
completed: 2026-06-07
---

# Этап 3 / План 02: Миграция захардкоженных правил групп в память правок — Summary

**19 префиксных/подстрочных правил PRODUCT_OVERRIDES раскрыты в 34 точечные group-правки и перенесены во вкладку «Правки» Google Sheet; захардкоженные словари удалены из upload.py — новые переопределения групп добавляются без деплоя кода**

## Performance

- **Duration:** ~20 мин (включая чекпоинт на боевой запуск через sysadmin)
- **Started:** 2026-06-07
- **Completed:** 2026-06-07
- **Tasks:** 3 (Task 1 — migrate_overrides.py; Task 2 — чекпоинт боевого запуска; Task 3 — удаление словарей)
- **Files modified:** 2 (migrate_overrides.py создан; upload.py изменён)

## Accomplishments

- Создана утилита `scripts/migrate_overrides.py` с функцией `expand_overrides()` — раскрывает префиксные/подстрочные правила в точные нормализованные имена товаров (разрешение семантического разрыва D-04↔D-07); функция чистая, без сетевых вызовов, локально верифицирована
- Боевой запуск на сервере daniella (через субагента sysadmin): 19 исходных правил раскрылись в 34 group-правки, записаны во вкладку «Правки»; `upload.py --dry-run` подтвердил «Загружено правок из памяти: 34»
- Удалены `PRODUCT_OVERRIDES`, `PRODUCT_CONTAINS_OVERRIDES`, `apply_product_override` из `upload.py`; `apply_group_mapping` сохранена и упрощена до своей единственной ответственности (category_map → display_group)

## Детали миграции

| Показатель | Значение |
|------------|----------|
| Исходных правил в коде | 19 (17 префиксных в PRODUCT_OVERRIDES + 2 подстрочных в PRODUCT_CONTAINS_OVERRIDES) |
| Раскрыто в точечные правки | 34 строки group во вкладке «Правки» |
| Подтверждение записи | upload.py --dry-run: «Загружено правок из памяти: 34» |
| Вкладка «Правки» | Google Sheet → вкладка «Правки» (append, ручные правки владельца сохранены) |
| Боевой запуск | Через субагента sysadmin на сервере daniella, venv /opt/apps/catalog/.venv |

**Важно: миграция разовая.** После удаления словарей из `upload.py` повторный запуск `migrate_overrides.py` невозможен — он импортирует `PRODUCT_OVERRIDES`/`PRODUCT_CONTAINS_OVERRIDES` из `upload.py`, которых там больше нет. Это ожидаемо: правила уже перенесены, утилита своё дело сделала.

## Task Commits

1. **Task 1: migrate_overrides.py** — `93ae7f4` (feat) — утилита с expand_overrides + --dry-run
2. **Task 2: чекпоинт боевого запуска** — нет коммита (операция на сервере через sysadmin)
3. **Task 3: удаление словарей из upload.py** — `19f78b2` (refactor)

## Files Created/Modified

- `scripts/migrate_overrides.py` — разовая CLI-утилита миграции; функция `expand_overrides()`; поддержка `--dry-run`; запись через `append_rows` (не clear); пропуск уже существующих group-правок
- `scripts/upload.py` — удалены PRODUCT_OVERRIDES (18 правил), PRODUCT_CONTAINS_OVERRIDES (2 правила), apply_product_override (14 строк); apply_group_mapping упрощена (-49 строк нетто), ответственность только за category_map → display_group

## Decisions Made

- **Миграция разовая, повторный запуск невозможен** — ожидаемо и задокументировано; правила уже в памяти
- **Боевой запуск только через sysadmin** — правило проекта (серверные операции = субагент sysadmin)
- **append-запись во вкладку** — не clear, чтобы не затереть ручные правки владельца (T-03-06)
- **apply_group_mapping сохранена** — функция нужна для category_map → display_group + лог немаппленных категорий

## Deviations from Plan

Нет — план выполнен точно как написано.

## Issues Encountered

Нет.

## User Setup Required

Нет — вкладка «Правки» уже содержит 34 group-правки после боевого запуска. Дополнительная настройка не требуется.

## Next Phase Readiness

- Анти-паттерн D-07 полностью устранён: переопределения групп больше не в коде
- Новые переопределения групп добавляются во вкладку «Правки» без деплоя
- Этап 3 завершён (оба плана выполнены: 03-01 ядро памяти + 03-02 миграция)
- Следующий этап 4: админ-панель владельца, которая будет писать во вкладку «Правки» напрямую

## Self-Check: PASSED

- FOUND: `scripts/migrate_overrides.py` — файл создан и содержит `expand_overrides` ✓
- FOUND: `scripts/upload.py` НЕ содержит `PRODUCT_OVERRIDES` ✓
- FOUND: `scripts/upload.py` НЕ содержит `PRODUCT_CONTAINS_OVERRIDES` ✓
- FOUND: `scripts/upload.py` НЕ содержит `apply_product_override` ✓
- FOUND: `scripts/upload.py` содержит `def apply_group_mapping` ✓
- FOUND: коммит `93ae7f4` (Task 1) ✓
- FOUND: коммит `19f78b2` (Task 3) ✓
- FOUND: файл парсируется Python без ошибок (AST-проверка PASSED) ✓

---
*Этап: 03-1*
*Завершено: 2026-06-07*
