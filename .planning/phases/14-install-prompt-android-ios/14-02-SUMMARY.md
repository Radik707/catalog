---
phase: 14-install-prompt-android-ios
plan: "02"
subsystem: pwa-install
tags: [pwa, install-prompt, react-context, tailwind, bottom-sheet, android-banner]
dependency_graph:
  requires:
    - phase: 14-01
      provides: lib/useInstallPrompt.ts + components/InstallPromptProvider.tsx (хук детекта платформы и провайдер)
  provides:
    - components/InstallPrompt.tsx — баннер Android + bottom-sheet iOS
    - app/catalog/[secret]/layout.tsx — InstallPromptProvider-обёртка + <InstallPrompt /> рядом с OfflineBar
    - components/SettingsPanel.tsx — пункт «Установить приложение» (скрыт в standalone)
  affects: [plan-03-manifest-viewport]
tech-stack:
  added: []
  patterns: [fixed-bottom-island, force-open-pattern, safe-area-inset-bottom]

key-files:
  created:
    - components/InstallPrompt.tsx
  modified:
    - lib/useInstallPrompt.ts
    - app/catalog/[secret]/layout.tsx
    - components/SettingsPanel.tsx

key-decisions:
  - "forceOpen + openFromSettings() добавлены в хук: открывает iOS-шторку из настроек даже при dismissed (D-05)"
  - "InstallPromptProvider обёрнут вокруг содержимого внутри CatalogSyncProvider — оба (SettingsPanel и InstallPrompt) являются его потомками"
  - "<InstallPrompt /> смонтирован сразу после <OfflineBar /> — минимально-инвазивная вставка (D-06)"
  - "Кнопка «Установить приложение» закрывает панель настроек после нажатия (setPanelOpen(false)) — UX-решение"
  - "env(safe-area-inset-bottom) через inline style (не Tailwind) — совместимость с Safari (D-07)"

patterns-established:
  - "forceOpen-паттерн: флаг boolean в хуке для принудительного показа UI из external source (разделение engaged/forceOpen)"
  - "fixed-bottom-island: компонент с fixed bottom-0, z-50, safe-area-inset-bottom — добавить рядом с OfflineBar в layout"

requirements-completed: [PWA-02]

duration: ~8 мин
completed: "2026-06-13"
---

# Phase 14 Plan 02: InstallPrompt UI Summary

**Фирменный баннер установки для Android и bottom-sheet инструкции для iOS с постоянной кнопкой «Установить приложение» в настройках под единым InstallPromptProvider.**

## Performance

- **Duration:** ~8 мин
- **Started:** 2026-06-13
- **Completed:** 2026-06-13
- **Tasks:** 2
- **Files modified:** 4 (1 создан, 3 изменено)

## Accomplishments

- Создан `components/InstallPrompt.tsx` — клиентский остров по образцу OfflineBar: баннер Android с кнопкой «Установить» и крестиком, bottom-sheet iOS с 3-шаговой инструкцией «Поделиться → На экран Домой → Добавить»
- Добавлены `forceOpen` (state) и `openFromSettings()` (callback) в хук `lib/useInstallPrompt.ts` — позволяют открывать iOS-шторку из настроек даже после dismiss
- `app/catalog/[secret]/layout.tsx` обёрнут в `InstallPromptProvider`; `<InstallPrompt />` смонтирован рядом с `<OfflineBar />`
- `components/SettingsPanel.tsx` дополнен пунктом «Установить приложение» — скрывается в standalone, вызывает `openFromSettings()` при клике

## Task Commits

1. **Task 1: InstallPrompt — баннер Android + bottom-sheet iOS** — `a127320` (feat)
2. **Task 2: Монтирование в layout + пункт в настройках** — `70050c1` (feat)

## Files Created/Modified

- `components/InstallPrompt.tsx` — новый клиентский остров: баннер Android + bottom-sheet iOS с safe-area и фирменными цветами
- `lib/useInstallPrompt.ts` — добавлены `forceOpen: boolean`, `openFromSettings(): Promise<void>` в UseInstallPromptResult
- `app/catalog/[secret]/layout.tsx` — `InstallPromptProvider` оборачивает дерево, `<InstallPrompt />` после `<OfflineBar />`
- `components/SettingsPanel.tsx` — `useInstallPromptContext()` + кнопка «Установить приложение»

## Decisions Made

- **forceOpen/openFromSettings** — добавлен в хук (план 01), а не инлайн во флаге компонента. Это разделяет логику «показать по вовлечённости» и «показать по запросу пользователя», что чище и тестируемее.
- **env(safe-area-inset-bottom) через inline style** — Tailwind-класс `pb-[env(safe-area-inset-bottom)]` работает, но inline style надёжнее на Safari из-за порядка применения CSS; выбрали style.
- **setPanelOpen(false) при нажатии «Установить приложение»** — UX-улучшение: панель скрывается, и баннер/шторка не перекрываются ей.
- **platform === "android" || platform === "ios"** — кнопка в настройках скрыта для `unsupported` (нет смысла) и `installed` (через `!isStandalone`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Расширение интерфейса] Добавлены forceOpen и openFromSettings в UseInstallPromptResult**
- **Found during:** Task 1 (проектирование InstallPrompt — нужен механизм открытия из настроек)
- **Issue:** План описал необходимость `openFromSettings()`/`forceOpen`, но не включил их в интерфейс `UseInstallPromptResult` из плана 01. Компонент и SettingsPanel не могли бы скомпилироваться без них.
- **Fix:** Добавлены `forceOpen: boolean` и `openFromSettings(): Promise<void>` в интерфейс и реализацию хука `lib/useInstallPrompt.ts`; `dismiss()` расширен: сбрасывает `forceOpen`.
- **Files modified:** `lib/useInstallPrompt.ts`
- **Verification:** npm run build прошёл без ошибок TypeScript; grep-проверки OK
- **Committed in:** a127320 (Task 1 commit)

---

**Total deviations:** 1 авто-фикс (Rule 2 — расширение интерфейса хука из плана 01)
**Impact on plan:** Необходимое расширение для корректности — без forceOpen/openFromSettings Task 2 не мог бы реализовать D-05. Никакого scope creep.

## Issues Encountered

Не было — сборка прошла с первого запуска, TypeScript ошибок нет.

## Known Stubs

Нет — компонент полностью реален, читает live-состояние из хука.

## Threat Flags

Нет новой сетевой поверхности. Угрозы плана обработаны:
- **T-14-03** (повторный показ): `dismiss()` пишет в localStorage + сбрасывает `forceOpen` — баннер не возвращается без явного действия пользователя
- **T-14-04** (перекрытие контента): `env(safe-area-inset-bottom)` + крестик/«Позже» — шторка не загораживает системную зону и всегда закрываема

## Self-Check: PASSED

- [x] `C:/catalog/components/InstallPrompt.tsx` — создан, 172 строки > min_lines 60
- [x] `C:/catalog/app/catalog/[secret]/layout.tsx` — содержит `InstallPromptProvider` и `<InstallPrompt`
- [x] `C:/catalog/components/SettingsPanel.tsx` — содержит `useInstallPromptContext`, `Установить приложение`, `isStandalone`
- [x] `C:/catalog/lib/useInstallPrompt.ts` — содержит `forceOpen`, `openFromSettings`
- [x] Коммит `a127320` — Task 1, подтверждён
- [x] Коммит `70050c1` — Task 2, подтверждён
- [x] `npm run build` — ✓ без ошибок TypeScript

## Next Phase Readiness

- Plan 03 (viewport-fit=cover + метатеги safe-area) может строиться поверх готового UI
- Баннер корректно работает при `viewport-fit=cover` (safe-area уже учтён через `env(safe-area-inset-bottom)`)
- iPhone-приёмка (критерий #5) отложена по аналогии с этапами 11–13 — не блокирует план 03

---
*Phase: 14-install-prompt-android-ios*
*Completed: 2026-06-13*
