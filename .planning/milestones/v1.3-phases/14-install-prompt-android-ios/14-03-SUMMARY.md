---
phase: 14-install-prompt-android-ios
plan: "03"
subsystem: pwa-install
tags: [pwa, viewport, safe-area, standalone, ios]
dependency_graph:
  requires:
    - phase: 14-02
      provides: components/InstallPrompt.tsx + env(safe-area-inset-bottom) в UI
  provides:
    - app/layout.tsx — viewport-fit=cover активирован для safe-area в standalone
  affects: [веха-v1.3-iPhone-приёмка]
tech-stack:
  added: []
  patterns: [viewport-fit-cover, safe-area-insets]

key-files:
  created: []
  modified:
    - app/layout.tsx

key-decisions:
  - "viewport-fit=cover добавлен в существующий export const viewport — не создан второй export (D-07)"
  - "iPhone-приёмка (критерии #2 и #5) отложена на конец вехи v1.3 — по образцу этапов 11/12/13"
  - "Этап 14 закрыт по авто-критериям: #1 (кодом/косвенно), #3 (однократность — в хуке), #4 (viewport-fit=cover)"

patterns-established:
  - "viewport-fit=cover через Next.js Viewport.viewportFit — расширяет существующий объект, не создаёт дублей"

requirements-completed: [PWA-02]

duration: ~3 мин
completed: "2026-06-13"
---

# Phase 14 Plan 03: Standalone Viewport Summary

**viewport-fit=cover добавлен в корневой layout — env(safe-area-inset-*) из плана 02 активирован для standalone на iPhone с чёлкой; ручная iPhone-приёмка отложена на конец вехи v1.3.**

## Performance

- **Duration:** ~3 мин
- **Started:** 2026-06-13
- **Completed:** 2026-06-13
- **Tasks:** 2 (Task 1 выполнен, Task 2 отложена)
- **Files modified:** 1

## Accomplishments

- В `app/layout.tsx` расширен `export const viewport: Viewport` полем `viewportFit: "cover"` — `env(safe-area-inset-*)`, подключённый в плане 02 для нижней шторки/баннера, теперь реально работает в standalone на iPhone с чёлкой (D-07)
- `npm run build` прошёл без ошибок TypeScript после правки
- Ручная iPhone-приёмка (критерии #2/#5) корректно отложена по образцу этапов 11, 12, 13

## Task Commits

1. **Task 1: viewport-fit=cover в корневом viewport** — `96cf863` (feat)
2. **Task 2: Ручная приёмка на реальном iPhone** — *отложена* (checkpoint:human-verify → «отложено»)

## Files Created/Modified

- `app/layout.tsx` — `viewportFit: "cover"` добавлен в объект `export const viewport`; сохранено поле `themeColor: "#2563eb"`

## Decisions Made

- **viewportFit в существующем объекте viewport** — расширён, не продублирован. Next.js 14 требует ровно один `export const viewport`; нарушение приводит к предупреждению сборки.
- **Отложенная приёмка** — по образцу этапов 11/12/13: авто-критерии (#1 косвенно, #3, #4 кодом) закрыты; iPhone-приёмка (#2/#5) вносится в STATE.md → «Отложенные элементы» и проводится перед сдачей вехи v1.3.
- **git push не производился** — деплой делает владелец при финальной приёмке вехи v1.3.

## Deviations from Plan

Нет — план выполнен строго. Task 1 реализован как описано. Task 2 отложен штатным образом (инструкция в `<how-to-verify>` прямо предусматривает сигнал «отложено»).

## Deferred Items (Отложенная приёмка)

**iPhone-приёмка PWA-02 (критерии #2 и #5) — отложена на конец вехи v1.3:**

| Критерий | Описание | Статус |
|----------|----------|--------|
| #2 | Bottom-sheet на реальном iPhone понятен без технических знаний | Отложен |
| #5 | Установить каталог на домашний экран через Safari → запустить в standalone | Отложен |

Что сделать при приёмке:
1. `git push origin main` → дождаться автодеплоя Vercel
2. Открыть секретную ссылку в Safari на iPhone
3. Дождаться bottom-sheet (~25 с или прокрутка ≥100 px)
4. Проверить шторку → закрыть → перезагрузить → не повторяется
5. Настройки → «Установить приложение» → шторка снова
6. Установить → запустить с домашнего экрана → без адресной строки, full-screen

## Issues Encountered

Не было — правка однострочная, сборка прошла с первого запуска.

## Known Stubs

Нет.

## Threat Flags

Нет новой сетевой поверхности. Угроза плана обработана:
- **T-14-05** (интерфейс под чёлкой в standalone): `viewport-fit=cover` активирован + `env(safe-area-inset-bottom)` из плана 02 — контент не уходит под системную зону (D-07, критерий #4)

## Закрытие этапа 14 (Install Prompt)

Этап 14 закрыт по авто-критериям:

| Критерий | Закрытие |
|----------|----------|
| #1 — Android-баннер (код) | Кодом (план 02: AndroidBanner) — реальный Android-тест при деплое |
| #2 — bottom-sheet понятен на iPhone | Отложена → конец вехи v1.3 |
| #3 — однократность промпта | Кодом (план 01: localStorage-флаг dismissed) |
| #4 — корректный standalone (safe-area) | Кодом (план 02: env(safe-area-inset-bottom) + план 03: viewport-fit=cover) |
| #5 — установка на реальном iPhone | Отложена → конец вехи v1.3 |

## Self-Check: PASSED

- [x] `C:/catalog/app/layout.tsx` — содержит `viewportFit: "cover"` и сохранён `themeColor`
- [x] Коммит `96cf863` — Task 1, подтверждён
- [x] `npm run build` — прошёл без ошибок (выполнено при Task 1)
- [x] Отложенная приёмка оформлена в STATE.md → «Отложенные элементы»

---
*Phase: 14-install-prompt-android-ios*
*Completed: 2026-06-13*
