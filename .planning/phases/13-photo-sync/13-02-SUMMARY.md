---
phase: 13-photo-sync
plan: "02"
subsystem: ui
tags: [pwa, offline, cloudinary, react-context, service-worker, sync]
human_needed: true

# Dependency graph
requires:
  - phase: 13-01
    provides: lib/syncPhotos.ts, refetch в UseCatalogSyncResult, unoptimized ProductCard, CacheableResponsePlugin
  - phase: 12-01
    provides: useOnlineStatus, OfflineBar
provides:
  - CatalogSyncProvider — единый экземпляр useCatalogSync в React-контексте для шапки и витрины
  - SyncButton — кнопка ↻ в шапке: idle → spin → галочка, disabled офлайн
  - CatalogView переведён с локального useCatalogSync на useCatalogSyncContext (нет двойного sync)
  - layout.tsx обёрнут в CatalogSyncProvider, SyncButton встроен в правый блок шапки
affects: [14-install-prompt]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - CatalogSyncProvider: createContext + Provider + useContext-хук (по образцу CatalogSettingsProvider/NavProvider)
    - Client-остров в серверном layout: SyncButton и CatalogSyncProvider встраиваются как готовые клиентские узлы
    - SyncButton: busy/done state + setTimeout(1500) для галочки-сброса — паттерн кратковременного тика (по образцу OfflineBar)
    - disabled кнопки офлайн с title-пояснением — паттерн из кнопки отправки заказа этапа 12

key-files:
  created:
    - components/CatalogSyncProvider.tsx
    - components/SyncButton.tsx
  modified:
    - components/CatalogView.tsx
    - app/catalog/[secret]/layout.tsx

key-decisions:
  - "[13-02] CatalogSyncProvider поднимает единственный useCatalogSync выше шапки — прямой проп от layout до CatalogView невозможен (серверный компонент)"
  - "[13-02] isOnline берётся из useCatalogSyncContext (не дублируется через useOnlineStatus в SyncButton)"
  - "[13-02] OfflineBar оставлен как есть — читает syncTimestamp напрямую из IDB, обновится при следующем тике ≤60с (задержка приемлема)"
  - "[13-02] iPhone-приёмка (Task 3) отложена на конец вехи v1.3 — по образцу этапов 11 и 12"

patterns-established:
  - "Подъём хука в Provider: когда client-остров в layout и компонент в main должны делить один экземпляр хука — поднять в CatalogSyncProvider"
  - "SyncButton busy/done: setBusy → await refetch() → finally setBusy(false) setDone(true) setTimeout сброс"

requirements-completed: [SYNC-01]

# Metrics
duration: ~10 мин (Task 1+2 из прошлой сессии)
completed: 2026-06-13
---

# Phase 13 Plan 02: Кнопка «Обновить» в шапке — Summary

**CatalogSyncProvider поднял единственный useCatalogSync в контекст; SyncButton (↻, spin→галочка, disabled офлайн) встроен в шапку рядом с шестерёнкой; SYNC-01 закрыт; iPhone-приёмка IMG-01..03 отложена на конец вехи v1.3**

## Performance

- **Duration:** ~10 мин
- **Completed:** 2026-06-13
- **Tasks:** 2 из 3 (Task 3 — отложенная HUMAN-UAT)
- **Files modified:** 4 (2 создано, 2 изменено)

## Accomplishments

- Создан `CatalogSyncProvider` — единый экземпляр `useCatalogSync` для всего дерева каталога; исключён риск двойного sync/fetch между шапкой и витриной
- Создан `SyncButton` (↻): онлайн — крутится при обновлении, показывает галочку на 1.5с; офлайн — заблокирован с `title="Нужен интернет для обновления"` и `opacity-50`
- `CatalogView` переведён с `useCatalogSync()` на `useCatalogSyncContext()` — один источник данных без второго экземпляра хука
- `layout.tsx` обёрнут в `<CatalogSyncProvider>`, `<SyncButton />` добавлен в правый блок шапки перед шестерёнкой
- `npm run build` — Compiled successfully

## Task Commits

1. **Task 1: CatalogSyncProvider + перевод CatalogView** — `cdc97ce` (feat)
2. **Task 2: SyncButton + встройка в layout** — `e132694` (feat)
3. **Task 3: iPhone-приёмка офлайн-фото** — ⏸ ОТЛОЖЕНА (см. ниже)

## Files Created/Modified

- `components/CatalogSyncProvider.tsx` — `"use client"`, `createContext<UseCatalogSyncResult | null>(null)`, компонент `CatalogSyncProvider` + хук `useCatalogSyncContext`; вызывает `useCatalogSync()` ровно один раз
- `components/SyncButton.tsx` — `"use client"`, default export; состояния `busy`/`done`; `refetch` и `isOnline` из `useCatalogSyncContext`; SVG arrow-path + animate-spin + SVG-галочка
- `components/CatalogView.tsx` — заменён `useCatalogSync` на `useCatalogSyncContext`; логика продуктов, фильтров, lightbox — не тронуты
- `app/catalog/[secret]/layout.tsx` — добавлены импорты `SyncButton`, `CatalogSyncProvider`; содержимое обёрнуто в `<CatalogSyncProvider>`; `<SyncButton />` в правом блоке шапки

## Decisions Made

- **Подъём в провайдер:** layout — серверный компонент, прямой проп от шапки в CatalogView невозможен. Решение: CatalogSyncProvider по образцу NavProvider/CatalogSettingsProvider.
- **isOnline из контекста:** SyncButton не вызывает `useOnlineStatus` самостоятельно — использует `isOnline` из `useCatalogSyncContext`, который уже его содержит (нет дублирования).
- **OfflineBar без изменений:** обновится при следующем тике ≤60с — задержка приемлема; дополнительная связка через контекст — опциональная полировка.

## Отложенная HUMAN-UAT: iPhone-приёмка офлайн-фото (Task 3)

**Статус:** deferred — отложена по решению владельца на конец вехи v1.3.
Это согласуется с практикой этапов 11 и 12 (iPhone-приёмка откладывалась аналогично).

**Требования, ожидающие подтверждения на устройстве:** IMG-01, IMG-02, IMG-03 (код готов, приёмка не проведена).

### Чеклист iPhone-приёмки (дословно из Task 3 плана 13-02)

Деплой: `git push` → дождаться автодеплоя Vercel. Затем на РЕАЛЬНОМ iPhone (Safari, не симулятор):

1. Открыть каталог по секретной ссылке онлайн, дождаться загрузки.
2. Прокрутить и открыть 5–10 карточек с фото; открыть 2–3 в полноэкранном просмотрщике (Lightbox) с зумом.
3. Включить авиарежим. Открыть те же карточки → фото видны. Открыть те же фото в Lightbox с зумом → видны (критерий №1).
4. Открыть товар, который НЕ просматривали онлайн → должна быть иконка-заглушка «нет фото», не битая картинка (D-06).
5. DevTools (Safari Web Inspector с Mac, опционально) → Cache Storage cloudinary-images ≤ 450 записей, суммарно ≤ ~40–50 МБ, без QuotaExceededError (критерии №3, №4).
6. Снова онлайн → нажать ↻ → иконка крутится → галочка; метка свежести в OfflineBar обновилась; в Cache Storage НЕ перекачались старые URL заново, добавились только новые (если были) (критерий №2).

**Когда проводить:** перед сдачей вехи v1.3 (после завершения этапа 14).
**Сигнал о возобновлении:** «принято» (или описать расхождения).

## Критерии успеха

| Критерий | Статус |
|----------|--------|
| CatalogSyncProvider создан, экспортирует Provider + useCatalogSyncContext | ✅ |
| Provider вызывает useCatalogSync() ровно один раз | ✅ |
| CatalogView использует useCatalogSyncContext (нет прямого useCatalogSync) | ✅ |
| SyncButton: крутится при busy, галочка при done | ✅ |
| SyncButton: disabled + opacity при офлайн, title-пояснение | ✅ |
| SyncButton и CatalogView делят один экземпляр sync | ✅ |
| layout.tsx: CatalogSyncProvider обёртывает шапку и main | ✅ |
| SyncButton в правом блоке шапки перед шестерёнкой | ✅ |
| npx tsc --noEmit без ошибок | ✅ |
| npm run build — Compiled successfully | ✅ |
| SYNC-01 закрыт (кнопка ручного обновления) | ✅ код-complete |
| IMG-01/IMG-02/IMG-03 — офлайн-фото на реальном iPhone | ⏸ отложена |

## Deviations from Plan

Task 3 (checkpoint:human-verify) не выполнена сейчас — отложена по явному решению владельца на конец вехи v1.3, по образцу этапов 11 и 12. Кодовая часть плана (Task 1, Task 2) выполнена точно как написана.

## Issues Encountered

Нет.

## User Setup Required

Нет — внешняя конфигурация не требуется.

## Next Phase Readiness

- Этап 13 завершён по авто-критериям: кэш-слой фото (план 01) + кнопка «Обновить» (план 02) — оба в production-сборке
- Следующий: Этап 14 (Install Prompt — Android баннер + iOS инструкция)
- Отложенная iPhone-приёмка (IMG-01..03) — провести перед финальной сдачей вехи v1.3, чеклист сохранён выше

## Self-Check: PASSED (код), приёмка отложена

- `components/CatalogSyncProvider.tsx` — существует ✅
- `components/SyncButton.tsx` — существует ✅
- Коммит `cdc97ce` — Task 1 (CatalogSyncProvider + CatalogView) ✅
- Коммит `e132694` — Task 2 (SyncButton + layout) ✅
- `npm run build` — Compiled successfully ✅
- iPhone-приёмка (Task 3) — ⏸ отложена на конец вехи v1.3

---
*Phase: 13-photo-sync*
*Completed: 2026-06-13*
