---
phase: 11-indexeddb-usecatalogsync
plan: "02"
subsystem: client-data-layer
tags: [indexeddb, offline, react-hook, stale-while-revalidate, pwa]
dependency_graph:
  requires: ["11-01"]
  provides: ["lib/useCatalogSync.ts"]
  affects: ["components/CatalogView.tsx", "app/catalog/[secret]/page.tsx"]
tech_stack:
  added: []
  patterns:
    - "stale-while-revalidate: IDB → fetch → бесшовная подмена Product[]"
    - "useCallback для стабильной ссылки на sync() в зависимостях useEffect"
    - "useRef-флаг для однократного вызова navigator.storage.persist()"
    - "SSR-безопасность: navigator/window только внутри useEffect/callbacks"
key_files:
  created:
    - lib/useCatalogSync.ts
  modified: []
decisions:
  - "[11-02] sync() через useCallback([]) — зависимостей нет, ссылка стабильна; useEffect([sync]) корректен"
  - "[11-02] Начальное isOnline=true на SSR, исправляется в useEffect — безопасно для Next.js гидратации"
  - "[11-02] catch блок IDB читает без throw: редкий сбой IDB (приватный режим iOS) не ломает монтирование"
  - "[11-02] persist() вызывается под двойным guard: persistCalledRef + navigator.storage?.persist (nullable)"
metrics:
  duration: "~5 мин"
  completed: "2026-06-12"
  tasks_completed: 1
  tasks_total: 1
  files_created: 1
  files_modified: 0
---

# Phase 11 Plan 02: useCatalogSync — стратегия stale-while-revalidate + офлайн-статусы

**One-liner:** Клиентский React-хук stale-while-revalidate: мгновенный рендер из IndexedDB + тихий fetch /api/products + авто-подтягивание по событию online + однократный persist() для защиты от iOS eviction.

## Что сделано

Создан `lib/useCatalogSync.ts` — клиентский хук, который будет подключён к CatalogView вместо SSR-данных из page.tsx (план 03).

### Логика синхронизации

1. При монтировании: `getProducts()` из IndexedDB → если кэш есть, мгновенно `setProducts(cached)` + `status="ready"` (без ожидания сети).
2. Параллельно: `getMeta("syncTimestamp")` → `setSyncedAt`.
3. Если `navigator.onLine === false` → не делаем fetch; если кэш пуст → `status="empty-offline"`.
4. Если онлайн: `fetch("/api/products")` → `setProducts(fresh)` + `saveProducts(fresh)` + `saveMeta("syncTimestamp", now)` + `setSyncedAt(now)` + `status="ready"`.
5. После первой успешной синхронизации — `navigator.storage.persist()` под guard `navigator.storage?.persist`.
6. `catch`: тех. ошибку не пробрасываем; если кэш пуст → `status="empty-offline"`, если есть — оставляем `"ready"`.

### Подписки на события

- `window.addEventListener("online", ...)` → `setIsOnline(true)` + повторный `sync()` (D-03: авто без кнопки).
- `window.addEventListener("offline", ...)` → `setIsOnline(false)`.
- Cleanup `removeEventListener` в `return` из `useEffect` — утечек нет.

## Критерии приёмки — проверка

| Критерий | Статус |
|---|---|
| `"use client"` в начале файла | PASS |
| Экспортирует `useCatalogSync` | PASS |
| `fetch("/api/products"` внутри sync | PASS |
| Читает `getProducts()` ДО fetch (кэш первым) | PASS |
| Возвращает `products`, `isOnline`, `syncedAt`, `status` | PASS |
| `status`: три значения `"loading" \| "ready" \| "empty-offline"` | PASS |
| `navigator.storage?.persist` с guard, useRef-флаг однократности | PASS |
| `saveMeta("syncTimestamp", now)` при успехе | PASS |
| Подписка online/offline с `removeEventListener` в cleanup | PASS |
| catch не пробрасывает ошибку — D-04 | PASS |
| Нет `navigator`/`window` на верхнем уровне модуля | PASS |
| `npx tsc --noEmit` без ошибок | PASS |

## Threat Flags

Новых security-поверхностей не введено. CATALOG_SECRET не читается и не записывается в IDB. Хук оперирует только публичными данными витрины (T-11-03 — accepted).

## Deviations from Plan

None — план выполнен точно как написан.

## Self-Check

- [x] `lib/useCatalogSync.ts` создан — FOUND
- [x] Коммит `ca08a7e` существует
- [x] `npx tsc --noEmit` прошёл без ошибок

## Self-Check: PASSED
