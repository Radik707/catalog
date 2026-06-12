---
phase: 08-1
plan: 02
subsystem: api
tags: [google-sheets, typescript, nextjs, server-filter, hidden]

# Dependency graph
requires:
  - phase: 08-1/plan-01
    provides: тип правки «скрыт» в Python-пайплайне (колонка L заполняется upload.py)
provides:
  - Поле hidden?: boolean в интерфейсе Product (lib/types.ts)
  - Диапазон чтения Google Sheets расширен до A2:L
  - Маппинг row[11] === "1" → Product.hidden
  - Серверная фильтрация скрытых товаров в getProducts() (HIDE-05)
affects: [08-03, 08-04, api-products, витрина]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "expand-contract: новое поле в конец интерфейса + расширение диапазона Sheets — старый код не ломается"
    - "server-side filter: скрытие на сервере в getProducts, не на клиенте — данные не попадают в браузер"

key-files:
  created: []
  modified:
    - lib/types.ts
    - lib/sheets.ts

key-decisions:
  - "hidden маппится строго как row[11] === '1': undefined/пустая строка трактуется как видимый (совместимость до появления колонки)"
  - "Фильтр products.filter((p) => !p.hidden) — последняя операция перед return, после fallback-блока structure_map"
  - "Фильтрация только в lib/sheets.ts; в компонентах app/ нет дублирования"

patterns-established:
  - "expand-contract диапазон Sheets: A2:K → A2:L — добавлять в конец, не сдвигая старые колонки"
  - "server-filter: фильтр скрытых строго на сервере, после всех transform-операций"

requirements-completed: [HIDE-05]

# Metrics
duration: 5min
completed: 2026-06-11
---

# Phase 8 Plan 02: Чтение колонки «Скрыт» и серверная фильтрация в getProducts

**Product.hidden из колонки L Google Sheets, серверный фильтр products.filter((p) => !p.hidden) в getProducts — скрытые товары не попадают в ответ /api/products и в браузер**

## Performance

- **Duration:** ~5 мин
- **Started:** 2026-06-11T00:00:00Z
- **Completed:** 2026-06-11T00:05:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Интерфейс Product получил опциональное поле `hidden?: boolean` (колонка L)
- Диапазон чтения Google Sheets расширен с A2:K до A2:L (expand-contract, совместим)
- Маппинг row[11] === "1" → hidden: если колонки L ещё нет, row[11] === undefined → false (поведение не меняется)
- getProducts() фильтрует скрытые товары серверно, после fallback-блока structure_map и сортировки

## Task Commits

1. **Task 1: Поле hidden в Product + чтение колонки L** — `d3e61b5` (feat)
2. **Task 2: Фильтрация скрытых на сервере в getProducts** — `7f03081` (feat)

## Files Created/Modified

- `lib/types.ts` — добавлено поле `hidden?: boolean` (колонка L — «Скрыт»)
- `lib/sheets.ts` — диапазон A2:K → A2:L; маппинг row[11]; фильтр скрытых перед return

## Decisions Made

- `row[11] === "1"` — строгое сравнение со строкой "1": любое иное значение (undefined, "", "0") трактуется как видимый, что обеспечивает expand-contract совместимость до появления колонки L в листе
- Фильтр `products.filter((p) => !p.hidden)` — строго последняя операция перед return, после fallback-блока structure_map (~стр.50-79) и сортировки, чтобы не нарушить восстановление разделов и порядок

## Deviations from Plan

Нет — план выполнен точно по спецификации.

## Issues Encountered

Нет.

## Threat Model: T-08-03, T-08-04

- **T-08-03 (Information Disclosure):** скрытые товары не сериализуются в JSON — `products.filter((p) => !p.hidden)` выполняется в getProducts() ДО формирования ответа. Митигирован.
- **T-08-04 (Tampering):** скрытым считается строго `row[11] === "1"` — произвольный ввод не вызывает ложного скрытия. Митигирован.

## User Setup Required

Нет — изменения только в TypeScript-слое витрины.

## Next Phase Readiness

- Витрина готова читать поле `hidden` из колонки L: как только upload.py запишет "1" в колонку L, товар автоматически исчезнет с витрины
- Следующий шаг — план 08-03: admin.py белый список + кнопка-глазик в интерфейсе панели
- Боевая проверка через /api/products — в плане 08-04 (прогон через сисадмина)

---
*Phase: 08-1*
*Completed: 2026-06-11*
