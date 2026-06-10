---
phase: 06-1
plan: 01
subsystem: api
tags: [google-sheets, typescript, next.js, product-type]

# Dependency graph
requires:
  - phase: 05-1
    provides: "Колонки J «Подгруппа» и K «Раздел» заполнены в Google Sheet через upload.py"
provides:
  - "Тип Product с опциональными полями subgroup (J) и section (K)"
  - "getProducts() читает диапазон A2:K и маппит все 11 колонок Sheet"
affects:
  - "06-02 — план 02 строит навигацию раздел→подгруппа поверх этих полей"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Expand-contract: новые поля опциональны, текущая витрина не ломается"
    - "row[N] || undefined — паттерн маппинга опциональных строк из Sheet"

key-files:
  created: []
  modified:
    - lib/types.ts
    - lib/sheets.ts

key-decisions:
  - "Поля subgroup/section строго опциональны (?): существующие компоненты не требуют изменений до плана 02"
  - "Диапазон расширен до A2:K в единственном месте getProducts() — локализованное изменение"

patterns-established:
  - "expand-contract: добавлять новые поля опциональными перед переходом компонентов"

requirements-completed: [NAV-01, NAV-04]

# Metrics
duration: 8min
completed: 2026-06-09
---

# Phase 6, Plan 01: Слой данных Summary

**Тип Product расширен полями subgroup/section (колонки J/K Google Sheet), getProducts() читает A2:K — фундамент двухуровневой навигации без поломки текущей витрины**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-06-09T~start
- **Completed:** 2026-06-09
- **Tasks:** 3 (2 с кодом + 1 верификация)
- **Files modified:** 2

## Accomplishments

- Тип `Product` получил опциональные поля `subgroup?: string` и `section?: string` с русскими комментариями, указывающими на колонки J/K
- `getProducts()` расширила диапазон чтения с `A2:I` до `A2:K`; маппинг `row[9]`/`row[10]` добавлен по существующему паттерну `|| undefined`
- Полная сборка `npm run build` прошла без ошибок — текущая витрина не сломана (поля опциональны)

## Task Commits

1. **Task 1: Добавить поля subgroup и section в тип Product** — `fd2f24f` (feat)
2. **Task 2: Расширить диапазон чтения до A2:K, маппинг J/K** — `dc8ddb2` (feat)
3. **Task 3: Проверочная сборка** — (только верификация, отдельный коммит не требовался)

**Plan metadata:** коммит этого файла (docs)

## Files Created/Modified

- `lib/types.ts` — добавлены `subgroup?: string` (колонка J) и `section?: string` (колонка K) после `description`; добавлены русские комментарии к полям badge/imageUrl/description
- `lib/sheets.ts` — диапазон `A2:I` → `A2:K`; `subgroup: row[9] || undefined`, `section: row[10] || undefined`; обновлён JSDoc getProducts()

## Decisions Made

Поля добавлены строго опциональными (`?`) согласно решению D-07 и паттерну expand-contract из Этапа 5: ни один существующий компонент не требует изменений до плана 02 — компиляция и сборка проходят без изменения каких-либо компонентов.

## Deviations from Plan

Нет — план выполнен точно как написан.

## Issues Encountered

Нет.

## User Setup Required

Нет — никаких внешних сервисов не добавлено. Google Sheet уже содержит нужные колонки (Этап 5).

## Next Phase Readiness

- Слой данных готов: `Product.subgroup` и `Product.section` доступны в любом компоненте
- План 02 может строить группировку `section → subgroup → товары` из уже полученного массива `Product[]`
- Порядок разделов/подгрупп сохраняется «по первому появлению» — сортировка `upload.py` (Этап 5) обеспечивает правильный порядок

---
*Phase: 06-1*
*Completed: 2026-06-09*
