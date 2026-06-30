---
phase: 18-client-bottom-tabs
plan: 02
subsystem: ui
tags: [react, nextjs, tailwind, role-gate, bottom-tabs, pwa, safe-area, contact-fab, layout]

# Dependency graph
requires:
  - phase: 18-01
    provides: components/BottomTabBar.tsx — готовый компонент (гейт роли, 3 вкладки, бейджи, safe-area)
  - phase: 15-role-split
    provides: useRole hook с SSR-safe ready-флагом (role/client гейт)
  - phase: 14-install-prompt
    provides: InstallPromptProvider — обёртка, внутри которой монтируется BottomTabBar
provides:
  - app/catalog/[secret]/layout.tsx — BottomTabBar смонтирован рядом с ContactFab, ClientBottomSpacer внутри main
  - components/ClientBottomSpacer.tsx — резерв нижнего отступа только для роли client (null для sales)
  - components/ContactFab.tsx — подъём плавающей кнопки выше панели для client (bottom-24), sales без изменений
affects:
  - Этап 19 (нижние табы готовы, вкладка «Корзина» уже ведёт к корзине)
  - Этап 20 (нижняя навигация-фундамент для «Главной»)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - ClientBottomSpacer: клиентский остров с гейтом роли, резерв высоты через inline style calc(4rem + env(safe-area-inset-bottom))
    - ContactFab: условный bottom для роли (bottom-24 для client, bottom-6 для sales) через useRole()
    - BottomTabBar: монтируется внутри InstallPromptProvider (читает все провайдеры) — паттерн D-12

key-files:
  created:
    - components/ClientBottomSpacer.tsx
  modified:
    - app/catalog/[secret]/layout.tsx
    - components/ContactFab.tsx

key-decisions:
  - "ClientBottomSpacer: высота calc(4rem + env(safe-area-inset-bottom)) через inline style — резерв контента только для client (D-09)"
  - "ContactFab: role === 'client' → bottom-24 (96px); role === 'sales' → bottom-6 без изменений (D-10)"
  - "BottomTabBar смонтирован внутри InstallPromptProvider рядом с ContactFab — читает все провайдеры (роль/режим/корзина/избранное) (D-12)"
  - "Task 3 (checkpoint:human-verify) PASSED — владелец принял на проде 2026-06-28 (ответ «принято»)"

patterns-established:
  - "ClientBottomSpacer: гейт if (!ready || role !== 'client') return null — обязательный SSR-safe паттерн (аналог BottomTabBar)"
  - "Условный bottom ContactFab по роли — паттерн для будущих FAB-компонентов в раскладке с нижними табами"

requirements-completed: [TABS-03, TABS-04]

# Metrics
duration: 20min
completed: 2026-06-28
---

# Phase 18 Plan 02: Интеграция нижней панели — монтирование, раскладка, приёмка Summary

**Монтирование BottomTabBar в каталожный layout с резервом нижнего отступа (ClientBottomSpacer, только для client) и подъёмом ContactFab выше панели для роли client (bottom-24 vs bottom-6 для sales); сборка прошла, приёмка на проде подтверждена владельцем («принято»)**

## Performance

- **Duration:** ~20 мин (Task 1 + Task 2) + приёмка на проде (Task 3)
- **Started:** 2026-06-28T15:50:00Z
- **Completed:** 2026-06-28 (приёмка подтверждена)
- **Tasks:** 3 (Task 1 — монтирование + spacer, Task 2 — ContactFab + сборка, Task 3 — приёмка на проде)
- **Files modified:** 3 (layout.tsx правлен, ContactFab.tsx правлен, ClientBottomSpacer.tsx создан)

## Accomplishments

- **Task 1:** Смонтирован `<BottomTabBar secret={params.secret} />` в `app/catalog/[secret]/layout.tsx` (внутри InstallPromptProvider, рядом с ContactFab); создан `components/ClientBottomSpacer.tsx` — клиентский остров с гейтом роли (null при !ready || role !== 'client'), резервирует высоту `calc(4rem + env(safe-area-inset-bottom))` через inline style, смонтирован внутри `<main>` после `{children}`
- **Task 2:** `components/ContactFab.tsx` дополнен `useRole()`; для `role === 'client'` контейнер поднят до `bottom-24` (96px, выше панели 64px + запас), для sales остался `bottom-6`; дочерние иконки (Telegram/MAX) не правились — смещаются вместе с контейнером; `npm run build` завершился успешно (7 страниц, 0 ошибок TS/линтера)
- **Task 3:** Ручная приёмка на проде (Vercel) — владелец проверил: панель видна в роли client, бейджи счётчиков работают, контент не перекрыт, ContactFab выше панели, в роли Агент — панели нет, safe-area учтён. Результат: **«принято»** 2026-06-28

## Task Commits

1. **Task 1: Смонтировать BottomTabBar в layout + резерв нижнего отступа контента (только client)** — `7d6e98a` (feat)
2. **Task 2: Поднять ContactFab выше панели для роли client + сборка** — `df537ae` (feat)
3. **Task 3: checkpoint:human-verify** — PASSED на проде, без коммита (верификация, не код)

## Files Created/Modified

- `app/catalog/[secret]/layout.tsx` — добавлен импорт BottomTabBar + монтирование `<BottomTabBar secret={params.secret} />` рядом с `<ContactFab />`; `<ClientBottomSpacer />` внутри `<main>` после `{children}`
- `components/ClientBottomSpacer.tsx` — новый клиентский компонент: гейт роли (null для sales/до ready), резерв высоты `calc(4rem + env(safe-area-inset-bottom))`, "use client", useRole()
- `components/ContactFab.tsx` — добавлен useRole(); условный `bottom-24` для client, `bottom-6` для sales; дочерние позиции не изменены

## Decisions Made

- `ClientBottomSpacer` использует inline `style` для высоты (не Tailwind `h-[calc(...)]`) — надёжнее на Safari, согласовано с паттерном InstallPrompt (D-08/D-09).
- ContactFab поднят до `bottom-24` (96px) — перекрытие исключено при высоте панели 64px (h-16) + safe-area (D-10).
- BottomTabBar монтируется внутри InstallPromptProvider (не выше) — получает доступ к провайдерам роли/навигации/корзины/избранного без дополнительных контекстов (D-12).
- Дочерние кнопки ContactFab (Telegram, MAX) не правились — их `bottom-[5.5rem]`/`[10.5rem]` относительны контейнеру, сдвигаются автоматически.

## Deviations from Plan

Нет — план выполнен точно.

## Issues Encountered

Нет.

## Known Stubs

Нет — компонент полностью функционален, данные реальные (роль из localStorage через useRole).

## Threat Flags

Нет новой поверхности атаки — монтирование компонента и правки раскладки. Нет новых эндпойнтов, секретов или хранилищ.

## Self-Check: PASSED

- [x] `components/ClientBottomSpacer.tsx` существует
- [x] `app/catalog/[secret]/layout.tsx` содержит `BottomTabBar` и `ClientBottomSpacer`
- [x] `components/ContactFab.tsx` содержит `useRole` и ветку для `role === 'client'`
- [x] Коммит `7d6e98a` существует (Task 1)
- [x] Коммит `df537ae` существует (Task 2)
- [x] `npm run build` прошёл успешно (зафиксировано при выполнении Task 2)
- [x] Task 3 (checkpoint:human-verify) PASSED — владелец подтвердил на проде: «принято» (2026-06-28)
- [x] TABS-03 выполнено: в роли «Торговый» нижней панели нет
- [x] TABS-04 выполнено: панель не перекрывает контент и ContactFab; safe-area учтён; работает офлайн и в standalone-PWA

## Next Phase Readiness

- Этап 18 полностью завершён (2/2 планов): TABS-01..04 выполнены
- Этап 19 («Повторить заказ» + «Мои заказы») — следующий; вкладка «Корзина» в BottomTabBar уже ведёт к /cart, что логично использовать как точку входа
- Блокеров нет

---
*Phase: 18-client-bottom-tabs*
*Completed: 2026-06-28*
