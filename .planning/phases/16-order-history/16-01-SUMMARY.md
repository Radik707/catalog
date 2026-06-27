---
phase: 16-order-history
plan: 01
subsystem: ui
tags: [typescript, localStorage, react-hooks, order-history]

# Dependency graph
requires:
  - phase: 15-role-sales-client
    provides: useRole — паттерн localStorage-хука с isLoaded-флагом; образец useFavorites/useCart
provides:
  - "TypeScript-типы OrderHistoryItem и OrderHistoryEntry в lib/types.ts"
  - "Хук useOrderHistory с CRUD (addEntry/removeEntry/clearHistory) + FIFO 20 + мягкая деградация"
affects:
  - 16-02 (страница /orders + встройка записи в cart/page.tsx строится поверх этого контракта)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FIFO-потолок через slice(next.length - MAX): вытеснение самых старых при > 20 записей"
    - "isValidEntry-фильтр: мягкая деградация битых localStorage-записей без падения хука"
    - "Двойной useEffect (load-on-mount + save-on-change с isLoaded-guard) — единый паттерн для всех localStorage-хуков"

key-files:
  created:
    - lib/useOrderHistory.ts
  modified:
    - lib/types.ts

key-decisions:
  - "Типы OrderHistoryItem/OrderHistoryEntry размещены в lib/types.ts (рядом с Product), а не внутри useOrderHistory.ts — общий контракт, потребители импортируют из одного места"
  - "isValidEntry проверяет id/items/createdAt/channel — минимальный набор полей для рендера и удаления; поле total не обязательно для валидности (обратная совместимость)"
  - "channel в isValidEntry проверяется строго ('telegram' | 'max') — битые/неизвестные каналы молча отбрасываются (мягкая деградация D-14)"

patterns-established:
  - "HISTORY_KEY = 'catalog-order-history': ключ localStorage в стиле catalog-*"
  - "MAX_HISTORY_ENTRIES = 20 + FIFO через slice(next.length - MAX) в addEntry"
  - "isValidEntry: приватная guard-функция для фильтрации невалидных записей при загрузке"

requirements-completed: [HIST-01, HIST-02, HIST-04]

# Metrics
duration: 4min
completed: 2026-06-27
---

# Phase 16 Plan 01: Фундамент истории заказов Summary

**TypeScript-типы OrderHistoryItem/OrderHistoryEntry + хук useOrderHistory с FIFO-потолком 20 и мягкой деградацией битых localStorage-записей**

## Performance

- **Duration:** 4 мин
- **Started:** 2026-06-27T14:47:29Z
- **Completed:** 2026-06-27T14:51:30Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Объявлены типы `OrderHistoryItem` (снимок позиции: id/name/quantity/priceAtOrder/unit/imageUrl?) и `OrderHistoryEntry` (запись заказа: id/items/total/createdAt/channel) — по решениям D-07..D-11
- Создан `useOrderHistory` с CRUD-мутациями, FIFO-потолком 20 записей (D-13) и мягкой деградацией (D-14) — по образцу useCart/useFavorites
- `npx tsc --noEmit` проходит без ошибок, новых зависимостей не добавлено

## Task Commits

Каждое задание закоммичено атомарно:

1. **Task 1: Объявить типы OrderHistoryItem и OrderHistoryEntry** — `fd17e83` (feat)
2. **Task 2: Создать хук useOrderHistory** — `c657165` (feat)

**Метаданные плана:** (см. финальный коммит docs)

## Files Created/Modified
- `lib/types.ts` — добавлены экспортируемые интерфейсы OrderHistoryItem и OrderHistoryEntry
- `lib/useOrderHistory.ts` — хук-store истории заказов: loadHistory/saveHistory + useOrderHistory с addEntry/removeEntry/clearHistory

## Decisions Made
- Типы размещены в `lib/types.ts` (общий контракт), а не внутри хука — удобный импорт для потребителей в плане 02
- `isValidEntry` проверяет `id`, `items` (Array), `createdAt`, `channel` — минимальный набор для корректного рендера и CRUD; `total` намеренно не обязателен (будущая обратная совместимость)
- Строгая проверка `channel === 'telegram' || 'max'` в guard — любой неизвестный канал молча отбрасывается

## Deviations from Plan

Нет — план выполнен точно по спецификации.

## Issues Encountered

Нет — оба задания выполнены с первой попытки, `npx tsc --noEmit` без ошибок.

## Threat Surface Scan

Нет новых угроз: `lib/types.ts` и `lib/useOrderHistory.ts` — чисто клиентский код без сетевых вызовов, без API-эндпоинтов, без обработки пользовательского ввода на сервере.

Угрозы T-16-01 (Tampering), T-16-02 (DoS приватный режим), T-16-03 (DoS разрастание) — все закрыты:
- T-16-01: `isValidEntry` + `try/catch` вокруг `JSON.parse`
- T-16-02: `typeof window === 'undefined'` + тихий `try/catch` в save
- T-16-03: `MAX_HISTORY_ENTRIES = 20` + FIFO `slice`

## Known Stubs

Нет — этот план создаёт только типы и хук (без UI). Стабы появятся только если страница /orders не использует реальные данные из хука (проверить в плане 02).

## User Setup Required

Нет — никаких внешних сервисов и переменных окружения.

## Next Phase Readiness

- **16-02 (страница /orders + встройка в корзину)** может строиться немедленно: контракт `useOrderHistory` и типы `OrderHistoryEntry`/`OrderHistoryItem` зафиксированы.
- Импорт: `import { useOrderHistory } from '@/lib/useOrderHistory'`
- Импорт типов: `import { OrderHistoryEntry, OrderHistoryItem } from '@/lib/types'`

## Self-Check: PASSED

- [x] `lib/types.ts` содержит `export interface OrderHistoryItem` (строки 18–24) и `export interface OrderHistoryEntry` (строки 27–33)
- [x] `lib/useOrderHistory.ts` создан (99 строк), экспортирует `useOrderHistory`
- [x] Коммит `fd17e83` существует (Task 1)
- [x] Коммит `c657165` существует (Task 2)
- [x] `npx tsc --noEmit` проходит без ошибок

---
*Phase: 16-order-history*
*Completed: 2026-06-27*
