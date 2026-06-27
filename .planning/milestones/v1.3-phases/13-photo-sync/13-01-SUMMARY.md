---
phase: 13-photo-sync
plan: 01
subsystem: ui
tags: [pwa, service-worker, cloudinary, next-image, indexeddb, serwist, offline]

# Dependency graph
requires:
  - phase: 11-indexeddb-usecatalogsync
    provides: useCatalogSync hook, catalogDb getMeta/saveMeta, prevImageUrls ключ
  - phase: 10-sw-manifest
    provides: CacheFirst Cloudinary matcher в app/sw.ts (каркас)
provides:
  - unoptimized рендер фото в ProductCard — браузер запрашивает прямой res.cloudinary.com URL
  - onError-фолбэк на PhotoPlaceholder при офлайн + незакэшированное фото (D-06)
  - CacheableResponsePlugin(statuses:[200]) — только успешные ответы попадают в кэш (T-13-01)
  - lib/syncPhotos.ts: diff-предзагрузка только новых URL, первая синхронизация ленивая (D-04)
  - UseCatalogSyncResult.refetch — ручная синхронизация для кнопки «Обновить» (SYNC-01)
affects: [13-photo-sync план 02 (SyncButton), 14-install-prompt]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - unoptimized next/image для согласования URL с SW-matcher (подход 1)
    - CacheableResponsePlugin поверх ExpirationPlugin в CacheFirst
    - syncPhotos: diff через Set(O1) + fire-and-forget fetch (SW перехватит и закэширует)
    - Ленивая первая загрузка — не precache 900 фото на старте

key-files:
  created:
    - lib/syncPhotos.ts
  modified:
    - components/ProductCard.tsx
    - app/sw.ts
    - lib/useCatalogSync.ts

key-decisions:
  - "[13-01] Подход 1 (locked): raw Cloudinary URL через unoptimized — matcher SW, рендер и prefetch используют один формат"
  - "[13-01] onError-фолбэк на PhotoPlaceholder (imgError state) — D-06 без лишних пометок"
  - "[13-01] CacheableResponsePlugin statuses:[200] — защита T-13-01 от кэширования 4xx/5xx"
  - "[13-01] syncPhotos: при пустом prevUrls fetch не вызывается (анти-паттерн №1, взрыв квоты iOS)"
  - "[13-01] refetch: sync — sync стабилен через useCallback([]), защита от гонки syncGenRef встроена"

patterns-established:
  - "unoptimized: добавлять к next/image когда SW должен кэшировать тот же URL что и браузер"
  - "fire-and-forget prefetch: fetch(url).catch(() => {}) — SW перехватит CacheFirst"
  - "diff через Set: prevSet = new Set(prevUrls); toFetch = newUrls.filter(u => !prevSet.has(u))"

requirements-completed: [IMG-01, IMG-02, IMG-03, SYNC-02]

# Metrics
duration: 3min
completed: 2026-06-13
---

# Phase 13 Plan 01: Синхронизация фото — кэш-слой Summary

**SW-кэш фото активирован: unoptimized ProductCard + CacheableResponsePlugin(200) + diff-предзагрузка через syncPhotos + refetch в контракте хука**

## Performance

- **Duration:** ~3 мин
- **Started:** 2026-06-13T13:27:04Z
- **Completed:** 2026-06-13T13:30:01Z
- **Tasks:** 3
- **Files modified:** 4 (3 изменено, 1 создан)

## Accomplishments

- Согласован URL фото: `unoptimized` в обоих `<Image>` ProductCard → браузер запрашивает `https://res.cloudinary.com/...`, SW-matcher `/^https:\/\/res\.cloudinary\.com\//` ловит его — офлайн-кэш карточек теперь реально работает
- SW кэширует только 200-ответы Cloudinary: `CacheableResponsePlugin({ statuses: [200] })` защищает от записи 4xx/5xx в Cache Storage (T-13-01)
- `lib/syncPhotos.ts`: diff по `prevImageUrls` через `Set` (O1), prefetch только новых URL огонь-и-забыл; первая синхронизация — полностью ленивая (анти-паттерн №1 iOS-квоты исключён)
- `UseCatalogSyncResult` расширен полем `refetch: () => Promise<void>` — готовый фундамент для кнопки «Обновить» (план 02)

## Task Commits

1. **Task 1: unoptimized + onError PhotoPlaceholder (D-06)** — `0f187b8` (feat)
2. **Task 2: CacheableResponsePlugin в CacheFirst Cloudinary** — `a41bb15` (feat)
3. **Task 3: syncPhotos + refetch в useCatalogSync** — `c82fcb7` (feat)

## Files Created/Modified

- `components/ProductCard.tsx` — `imgError` state + `unoptimized` + `onError` на обоих Image (сетка + список)
- `app/sw.ts` — добавлен `CacheableResponsePlugin({ statuses: [200] })` в plugins CacheFirst
- `lib/syncPhotos.ts` — новый модуль: diff-предзагрузка новых фото, ленивая первая загрузка
- `lib/useCatalogSync.ts` — импорт и вызов `syncPhotos(fresh)`, `refetch` в интерфейсе и return

## Decisions Made

Все решения были зафиксированы в 13-CONTEXT.md до выполнения плана — исполнитель следовал locked decision (подход 1). Никаких новых архитектурных решений принято не было.

## Deviations from Plan

Нет — план выполнен точно как написан. Все acceptance criteria пройдены:
- `unoptimized` встречается 4 раза в ProductCard (сетка × 2 блока, включая атрибут)
- `onError` встречается 2 раза (по одному на каждый Image)
- `CacheableResponsePlugin` импортирован и использован в sw.ts
- `syncPhotos` вызывается после `saveProducts` (grep: 4 вхождения в useCatalogSync)
- `refetch` в контракте и return (grep: 3 вхождения)
- `prevImageUrls` в syncPhotos (grep: 3 вхождения)
- `new Set` в syncPhotos (grep: 1 вхождение)
- `npx tsc --noEmit` — без ошибок
- `npm run build` — Compiled successfully

## Известные риски (не блокеры)

Cloudinary отдаёт фото cross-origin → ответ может быть opaque (status 0). `CacheableResponsePlugin({ statuses: [200] })` кэширует только `status === 200`. Если на реальном iPhone-приёмке (план 02) обнаружится, что фото не кэшируются — возможная причина: opaque-ответы. Альтернатива: добавить `crossOrigin="anonymous"` к Image и настроить CORS на Cloudinary. Отмечено как риск для проверки на устройстве.

## Issues Encountered

Нет.

## User Setup Required

Нет — внешняя конфигурация не требуется.

## Next Phase Readiness

- Фундамент кэш-слоя фото готов: URL согласованы, SW кэширует правильно, syncPhotos работает
- `refetch` экспонирован — план 02 (SyncButton) подключится к нему без изменений хука
- Поведенческая верификация (онлайн → авиарежим → карточки с фото) — на реальном iPhone в плане 02 (HUMAN-UAT)

---
*Phase: 13-photo-sync*
*Completed: 2026-06-13*
