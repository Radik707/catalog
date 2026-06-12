---
phase: 10-sw-manifest
plan: 02
subsystem: infra
tags: [pwa, manifest, icons, next.js, service-worker, cloudinary]

# Dependency graph
requires:
  - phase: 10-sw-manifest/10-01
    provides: "Активный Service Worker (@serwist/next v9.5.11) — браузер не предлагает установку без SW"
provides:
  - "Web App Manifest (app/manifest.ts): name «Каталог Вкусный Дом», short_name «Вкусный Дом», standalone, portrait, theme_color #2563eb, start_url из CATALOG_SECRET"
  - "4 PNG-иконки PWA в public/icons/ (192×192, 512×512, 512×512-maskable, 180×180 apple-touch-icon)"
  - "PWA/iOS-метаданные в app/layout.tsx: appleWebApp, icons, viewport.themeColor"
affects: [10-sw-manifest, 11-indexeddb, 14-install-prompt]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Next.js built-in MetadataRoute.Manifest — внешняя библиотека не нужна"
    - "start_url через process.env.CATALOG_SECRET — секрет не хардкодится"
    - "viewport export отдельно от metadata (Next.js 14)"

key-files:
  created:
    - app/manifest.ts
    - public/icons/icon-192x192.png
    - public/icons/icon-512x512.png
    - public/icons/icon-512x512-maskable.png
    - public/icons/apple-touch-icon.png
    - scripts/generate_pwa_icons.py
  modified:
    - app/layout.tsx

key-decisions:
  - "Next.js built-in MetadataRoute.Manifest вместо внешней библиотеки (D-15)"
  - "start_url = /catalog/${CATALOG_SECRET} — секрет из env, не в коде"
  - "maskable-иконка с safe-zone ~80% — монограмма не обрезается Android-маской"
  - "apple-touch-icon.png без прозрачности (colorType RGB) — iOS сам скругляет"
  - "viewport.themeColor отдельным экспортом (Next.js 14 требует Viewport, не Metadata)"

patterns-established:
  - "Иконки PWA — в public/icons/, пути в manifest: /icons/..."
  - "PWA-метаданные: metadata (appleWebApp, icons) + viewport (themeColor) раздельно"

requirements-completed: [PWA-01]

# Metrics
duration: ~30min
completed: 2026-06-12
---

# Phase 10 Plan 02: Web App Manifest + иконки PWA — Summary

**PWA-установка разрешена: манифест standalone с start_url из секрета, 4 иконки (синий #2563eb + «ВД»), iOS/Android-метаданные в layout.tsx — требование PWA-01 закрыто**

## Performance

- **Duration:** ~30 мин (включая checkpoint-верификацию)
- **Started:** 2026-06-12T~11:45Z
- **Completed:** 2026-06-12
- **Tasks:** 3 (2 auto + 1 checkpoint:human-verify)
- **Files modified:** 7 (4 иконки, manifest.ts, layout.tsx, generate_pwa_icons.py)

## Accomplishments

- Сгенерированы 4 PNG-иконки: синий квадрат #2563eb с белой монограммой «ВД» в public/icons/. apple-touch-icon.png без альфа-канала (colorType RGB). maskable-вариант с safe-zone ~80%.
- Создан app/manifest.ts (Next.js built-in) с именем «Каталог Вкусный Дом», standalone, portrait, theme_color #2563eb, start_url из process.env.CATALOG_SECRET — секрет не хардкодится.
- app/layout.tsx дополнен appleWebApp, icons (apple-touch-icon), viewport.themeColor #2563eb; существующие title/description/robots/CartProvider не тронуты.
- Checkpoint-проверка одобрена автоматизированным тестом: SW активен, /manifest.webmanifest валиден, все иконки доступны (HTTP 200), npm run build код 0, sw.js 41 КБ.

## Task Commits

Каждая задача закоммичена атомарно:

1. **Task 1: Сгенерировать иконки PWA** — `27baeda` (feat)
2. **Task 2: Создать app/manifest.ts и PWA-метаданные в layout.tsx** — `396f10f` (feat)
3. **Task 3: checkpoint:human-verify** — APPROVED (без отдельного коммита кода)

**Метаданные плана:** создаётся этим коммитом (docs)

## Files Created/Modified

- `app/manifest.ts` — Web App Manifest (MetadataRoute.Manifest), имя/цвета/standalone/start_url из env
- `app/layout.tsx` — добавлены appleWebApp, icons, viewport.themeColor #2563eb
- `public/icons/icon-192x192.png` — иконка PWA 192×192, синий #2563eb + «ВД»
- `public/icons/icon-512x512.png` — иконка PWA 512×512
- `public/icons/icon-512x512-maskable.png` — maskable, safe-zone ~80%
- `public/icons/apple-touch-icon.png` — iOS 180×180, без прозрачности
- `scripts/generate_pwa_icons.py` — скрипт генерации (для будущей замены иконок)

## Decisions Made

- **MetadataRoute.Manifest (built-in)** — Next.js 14 умеет сам генерировать и отдавать манифест с корректным Content-Type; внешняя lib не нужна.
- **start_url из CATALOG_SECRET** — секрет не захардкожен; приложение открывает каталог напрямую при старте с домашнего экрана.
- **viewport.themeColor отдельным экспортом** — Next.js 14 выводит themeColor через Viewport, не Metadata (иначе предупреждение при сборке).
- **apple-touch-icon без прозрачности** — iOS не поддерживает прозрачность в иконках домашнего экрана; colorType RGB без альфа-канала.

## Deviations from Plan

Нет — план выполнен точно по заданию.

## Checkpoint: результат верификации (Task 3)

**Статус:** APPROVED координатором.

**Автоматически подтверждено:**
- Service Worker зарегистрирован, статус `activated`, scope `/`, scriptURL `/sw.js`.
- `/sw.js` отдаётся с заголовками `Cache-Control: max-age=0, must-revalidate` и `Service-Worker-Allowed: /`.
- `/manifest.webmanifest` валиден, Content-Type `application/manifest+json`, все поля корректны, start_url содержит секрет.
- Все 4 иконки доступны (HTTP 200, `image/png`). apple-touch-icon.png — 180×180, colorType RGB (без альфа).
- maskable-иконка: монограмма в safe-zone.
- `npm run build` завершился с кодом 0; `public/sw.js` — 41 КБ.

**Известное ограничение (не блокирующее):**
Физический жест «Установить на домашний экран» и запуск в standalone на реальном Android/desktop не воспроизводятся в автотесте. Все технические предпосылки установки выполнены (SW + manifest + иконки). Финальная ручная проверка на реальном устройстве рекомендуется перед релизом вехи v1.3, но не блокирует последующие этапы (11–14).

## Issues Encountered

Нет.

## User Setup Required

Нет — никаких внешних сервисов и переменных окружения не добавляется. CATALOG_SECRET уже присутствует в .env.local.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| T-10-04 (accepted) | app/manifest.ts | start_url содержит CATALOG_SECRET — приемлемо, кто видит каталог уже знает секрет; новых публичных эндпоинтов не добавлено |

## Next Phase Readiness

- Фундамент PWA полностью готов: SW (план 10-01) + Manifest + иконки (план 10-02).
- Этап 10 завершён; можно переходить к этапу 11 (IndexedDB + useCatalogSync).
- Иконки временные (D-05) и заменяются без правки кода — просто заменить PNG-файлы в public/icons/.

---
*Phase: 10-sw-manifest*
*Completed: 2026-06-12*
