---
phase: 18-client-bottom-tabs
plan: 01
subsystem: ui
tags: [react, nextjs, tailwind, role-gate, bottom-tabs, pwa, safe-area]

# Dependency graph
requires:
  - phase: 15-role-split
    provides: useRole hook с SSR-safe ready-флагом (role/client гейт)
  - phase: 13-photo-sync
    provides: InstallPrompt safe-area паттерн (env(safe-area-inset-bottom) inline style)
provides:
  - components/BottomTabBar.tsx — клиентская нижняя панель вкладок для роли «Клиент»
  - Гейт роли: null при !ready || role !== 'client'
  - 3 равные вкладки: Каталог / Избранное / Корзина (grid-cols-3, h-16)
  - Бейджи-счётчики: items.length (корзина) и count (избранное), красная пилюля
  - safe-area-inset-bottom через inline style (надёжнее на Safari)
affects:
  - 18-02 (монтирование в layout.tsx — следующий план)
  - 19-reorder (может использовать тот же паттерн таба)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - SSR-safe гейт роли через useRole: null до ready (паттерн HeaderPrimaryAction)
    - Нижние табы: grid-cols-3 h-16 с inline safe-area-inset-bottom
    - Бейджи-счётчики: absolute -top-0.5 -right-0.5 w-5 h-5 bg-red-500 rounded-full (паттерн CartIcon)
    - Активная вкладка по pathname.endsWith('/cart') || mode (каскадное определение D-03)

key-files:
  created:
    - components/BottomTabBar.tsx
  modified: []

key-decisions:
  - "Task 1 и Task 2 реализованы в одном Write: файл создан сразу полным (каркас + бейджи + safe-area)"
  - "items.length для счётчика корзины (не totalItems) — согласованность с CartIcon (D-06)"
  - "safe-area-inset-bottom через inline style, не Tailwind pb-[env(...)] — надёжнее на Safari (D-08)"
  - "aria-pressed на каждой кнопке вместо aria-current — паттерн FavoritesIcon"

patterns-established:
  - "BottomTabBar-гейт: if (!ready || role !== 'client') return null — обязательный SSR-safe паттерн для клиентских UI-блоков"
  - "Бейдж счётчика: span.relative > svg + span.absolute (обёртка иконки relative, бейдж absolute)"

requirements-completed: [TABS-01, TABS-02]

# Metrics
duration: 15min
completed: 2026-06-28
---

# Phase 18 Plan 01: Нижняя панель вкладок (BottomTabBar) Summary

**Клиентский компонент нижних табов с гейтом роли (null для sales/до ready), 3 вкладками (Каталог/Избранное/Корзина), счётчиками-бейджами (items.length/count, красная пилюля), safe-area снизу и активным состоянием text-blue-600/text-gray-500**

## Performance

- **Duration:** ~15 мин
- **Started:** 2026-06-28T15:30:00Z
- **Completed:** 2026-06-28T15:45:00Z
- **Tasks:** 2 (выполнены в одном файле)
- **Files modified:** 1 (создан)

## Accomplishments

- Создан `components/BottomTabBar.tsx` (195 строк, минимум 60 по плану)
- Гейт роли SSR-safe: null при !ready || role !== 'client' — панель не мелькает при гидратации
- 3 вкладки с inline-SVG иконками: сетка (Каталог) / сердечко (Избранное, тот же d-path что FavoritesIcon) / корзина (тот же d-path что CartIcon)
- Бейджи-счётчики на «Избранное» и «Корзина» в стиле CartIcon: красная пилюля bg-red-500, только при > 0, обрезка > 99
- safe-area-inset-bottom через inline style (паттерн InstallPrompt, надёжнее Safari)
- aria-label и aria-pressed на каждой кнопке

## Task Commits

1. **Task 1: Каркас, гейт роли, 3 вкладки, навигация, активное состояние** — `4354d00` (feat)

*Task 2 (бейджи + safe-area) реализован в том же файле при создании — отдельного коммита нет (см. Deviations).*

**Метаданные плана:** будет добавлен ниже.

## Files Created/Modified

- `components/BottomTabBar.tsx` — нижняя панель вкладок клиента: гейт роли, 3 вкладки, бейджи, safe-area

## Decisions Made

- Task 1 и Task 2 реализованы за один Write: файл создавался сразу в полной форме (каркас + бейджи + safe-area), что логично при создании нового файла.
- `items.length` для бейджа корзины (не `totalItems`) — согласованность с CartIcon (D-06).
- `safe-area-inset-bottom` через inline `style`, не Tailwind `pb-[env(...)]` — надёжнее на Safari (D-08, паттерн InstallPrompt).
- `aria-pressed` на кнопках вместо `aria-current` — паттерн FavoritesIcon.

## Deviations from Plan

**1. [Rule N/A - Объединение задач] Task 1 и Task 2 выполнены единым созданием файла**

- **Обнаружено при:** Task 2
- **Суть:** При создании нового файла код Task 2 (бейджи, safe-area, aria) был включён сразу вместе с Task 1. Технически Task 2 не требовал отдельного коммита изменений — файл уже содержал всё необходимое.
- **Верификация:** Все автоматические проверки обоих задач прошли (`OK base`, `OK badges`), `npx tsc --noEmit` без ошибок.
- **Влияние:** Нет. Все критерии приёмки обеих задач выполнены. Один коммит вместо двух — приемлемо для создания нового файла.

---

**Итого отклонений:** 1 (объединение задач, не нарушает правил)
**Влияние на план:** Нет — все критерии успеха выполнены.

## Issues Encountered

Нет.

## Self-Check: PASSED

- [x] `components/BottomTabBar.tsx` существует
- [x] Верификация Task 1: `OK base`
- [x] Верификация Task 2: `OK badges`
- [x] TypeScript: `npx tsc --noEmit` без ошибок по BottomTabBar.tsx
- [x] Коммит `4354d00` существует

## User Setup Required

Нет — компонент готов к монтированию в layout. Монтирование — план 18-02.

## Next Phase Readiness

- `BottomTabBar` готов к монтированию в `app/catalog/[secret]/layout.tsx`
- Следующий шаг: план 18-02 — монтирование в layout, подъём ContactFab для роли client (D-10), нижний отступ контента (D-09)
- Блокеров нет

---
*Phase: 18-client-bottom-tabs*
*Completed: 2026-06-28*
