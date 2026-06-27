---
phase: 10-sw-manifest
plan: "01"
subsystem: infra
tags: [pwa, service-worker, serwist, next-config, gitignore, caching]

# Dependency graph
requires: []
provides:
  - Активный service worker на базе @serwist/next v9.5.11 (app/sw.ts → public/sw.js)
  - Каркас стратегий NetworkFirst (api-products) и CacheFirst (cloudinary-images, maxEntries:450)
  - next.config.mjs обёрнут withSerwist + заголовки Vercel против immutable-кэша
  - SW отключён в dev (D-13), skipWaiting:false (D-12)
  - .gitignore игнорирует public/sw.js и public/swe-worker*.js
affects:
  - этап 11 (IndexedDB + useCatalogSync — зависит от активного SW)
  - этап 12 (Офлайн-UX — зависит от SW и стратегий кэша)
  - этап 13 (Синхронизация фото — зависит от CacheFirst Cloudinary каркаса)
  - этап 14 (Install Prompt — зависит от SW + manifest)

# Tech tracking
tech-stack:
  added:
    - "@serwist/next ^9.5.11 (dep)"
    - "idb ^8.0.3 (dep, используется в этапе 11)"
    - "serwist ^9.5.11 (devDep)"
  patterns:
    - "withSerwist(serwistConfig)(nextConfig) — двухэтапная обёртка next.config.mjs"
    - "app/sw.ts — SW-файл компилируется webpack-плагином, серверные импорты запрещены"
    - "headers() в nextConfig для Cache-Control SW-файла"

key-files:
  created:
    - app/sw.ts
  modified:
    - package.json
    - package-lock.json
    - next.config.mjs
    - .gitignore

key-decisions:
  - "skipWaiting: false (D-12) — обновление SW только по явному согласию, иначе ChunkLoadError"
  - "disable: NODE_ENV===development (D-13) — SW отключён в npm run dev"
  - "Cache-Control: max-age=0, must-revalidate для /sw.js (D-14) — защита от Vercel immutable"
  - "ExpirationPlugin maxEntries:450 для Cloudinary — защита iOS-квоты ~50 МБ (D-16)"
  - "precacheEntries: self.__SW_MANIFEST — precache только app-shell, не 900 фото (anti-pattern)"

patterns-established:
  - "app/sw.ts: декларация ServiceWorkerGlobalScope через declare global + interface extension"
  - "runtimeCaching: кастомные стратегии ДО defaultCache (порядок важен)"

requirements-completed: [PWA-01]

# Metrics
duration: 15min
completed: "2026-06-12"
---

# Phase 10 Plan 01: Фундамент SW и Manifest Summary

**@serwist/next v9 подключён: активный SW с precache app-shell, NetworkFirst для API, CacheFirst для Cloudinary (maxEntries:450), заголовки Vercel против immutable-кэша sw.js, SW отключён в dev**

## Performance

- **Duration:** ~15 мин
- **Started:** 2026-06-12T~11:00Z
- **Completed:** 2026-06-12
- **Tasks:** 3 (Task 1 — чекпойнт, одобрен координатором; Task 2 и Task 3 — выполнены)
- **Files modified:** 5

## Accomplishments

- Установлены @serwist/next, idb, serwist — фундамент PWA-стека вехи v1.3
- app/sw.ts создан с полным каркасом стратегий и критическими настройками (skipWaiting:false, D-12)
- next.config.mjs обёрнут withSerwist + заголовки /sw.js против immutable-кэша Vercel (D-14)
- npm run build: код 0, строчка «✓ (serwist) Bundling the service worker script» в выводе
- public/sw.js корректно игнорируется .gitignore — не попадает в git

## Task Commits

1. **Task 1: Легитимность пакетов** — чекпойнт, одобрен координатором (пакеты проверены на npmjs.com); коммит не создаётся
2. **Task 2: Установить зависимости и создать app/sw.ts** — `766044a` (feat)
3. **Task 3: next.config.mjs + .gitignore** — `61007ee` (feat)

**Plan metadata:** см. финальный коммит docs

## Files Created/Modified

- `app/sw.ts` — исходник service worker: precache app-shell + NetworkFirst/CacheFirst стратегии
- `next.config.mjs` — обёртка withSerwist + заголовки Vercel для /sw.js
- `.gitignore` — блок «PWA: сгенерированные service worker файлы»
- `package.json` — добавлены @serwist/next, idb (deps) и serwist (devDep)
- `package-lock.json` — обновлён автоматически npm

## Decisions Made

- Следовал решениям D-11…D-16 из 10-CONTEXT.md без отклонений
- serwist попал в devDependencies (как указано в плане D-11), @serwist/next и idb — в dependencies

## Deviations from Plan

None — план выполнен точно по спецификации.

## Issues Encountered

При выполнении `npm install -D serwist` команда вернула «up to date» — serwist уже пришёл как транзитивная зависимость @serwist/next. Это норма: пакет был добавлен в devDependencies package.json напрямую, поэтому acceptance criteria выполнен. Проверено через `node -e` — все три пакета присутствуют в правильных секциях.

## User Setup Required

None — никаких переменных окружения или внешних сервисов для этапа 10-01 не требуется.

## Next Phase Readiness

Готово для этапа 10-02 (если есть) или этапа 11 (IndexedDB + useCatalogSync):
- SW активируется после `npm run build && npm start` и перехода в DevTools → Application → Service Workers
- Стратегии NetworkFirst/CacheFirst в app/sw.ts — каркас для расширения в этапах 11 и 13
- Заголовки Vercel настроены: после `git push` sw.js не будет залипать в кэше CDN

Ожидающие проверки (требуют продакшн-сборки + браузера, не автоматизированы):
- DevTools → Application → Service Workers: статус `activated and running`
- DevTools → Network → /sw.js → Response Headers: `cache-control: max-age=0, must-revalidate`
- npm run dev → SW отсутствует (проверка D-13)

---
*Phase: 10-sw-manifest*
*Completed: 2026-06-12*
