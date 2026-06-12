---
phase: 12-ux
plan: "01"
subsystem: offline-ux
tags: [offline, pwa, ux, status-bar, indexeddb]
dependency_graph:
  requires: [11-03]
  provides: [offline-bar, useOnlineStatus, formatSyncTime]
  affects: [app/catalog/[secret]/layout.tsx]
tech_stack:
  added: []
  patterns: [client-island-in-server-layout, SSR-safe-navigator, idb-getMeta]
key_files:
  created:
    - lib/useOnlineStatus.ts
    - lib/formatSyncTime.ts
    - components/OfflineBar.tsx
  modified:
    - app/catalog/[secret]/layout.tsx
decisions:
  - "[12-01] useOnlineStatus: useState(true) + typeof navigator guard — SSR-safe без useCatalogSync"
  - "[12-01] OfflineBar читает syncTimestamp через getMeta напрямую (не через useCatalogSync) — лёгкий остров без тяжёлого хука"
  - "[12-01] isStale вычисляется в рендере (не в useState) — нет проблемы устаревшего состояния при долгом просмотре"
  - "[12-01] При syncedAt === null и онлайн — полоска скрыта (нет мигания при первом запуске без IDB-данных)"
  - "[12-01] try/catch вокруг getMeta — защита от приватного режима iOS (T-12-02 mitigate)"
metrics:
  duration: "166 секунд (~3 мин)"
  completed_date: "2026-06-12"
  tasks_completed: 2
  files_created: 3
  files_modified: 1
requirements: [SYNC-03]
---

# Phase 12 Plan 01: Индикатор офлайн-режима — Summary

Полоска статуса офлайна и свежести данных под синей шапкой каталога: три состояния (скрыта / серая / жёлтая), читает реальный `syncTimestamp` из IDB, SSR-safe.

## Что сделано

### Task 1: Хук useOnlineStatus + утилита formatSyncTime
**Коммит:** `1bdac80`

**lib/useOnlineStatus.ts** — лёгкий клиентский хук:
- SSR-safe: `useState(true)`, `typeof navigator !== "undefined"` проверка только внутри `useEffect`
- Слушает события `window.addEventListener("online" / "offline")` с cleanup
- Не импортирует `useCatalogSync` и не обращается к IDB — тонкая обёртка над `navigator.onLine`

**lib/formatSyncTime.ts** — чистая утилита форматирования (без `"use client"`, без внешних библиотек):
- `formatSyncTime(null)` → `"данные не загружены"`
- Сегодня → `"данные за 08:30"` (с ведущим нулём)
- Вчера → `"данные за вчера, 08:30"`
- Раньше → `"данные за 10 июня, 08:30"` (массив `MONTHS_GENITIVE`, родительный падеж, без года)
- Сравнение по календарным суткам (год+месяц+день), не по скользящему окну 24 ч

### Task 2: Компонент OfflineBar + вставка в layout
**Коммит:** `29b56fa`

**components/OfflineBar.tsx** — клиентский компонент-остров:
- Читает `syncTimestamp` из IDB через `getMeta("syncTimestamp")` в `useEffect([])`
- `getMeta` обёрнут в `try/catch` — защита от приватного режима iOS (T-12-02)
- Три состояния D-01: `isOnline && !isStale` → `return null`; офлайн → серый `bg-gray-100`; `isStale` → жёлтый `bg-yellow-50`
- Позиционирование D-02: `sticky top-12 z-40 w-full`; внутри `max-w-screen-2xl mx-auto`
- Текст: офлайн → `"Офлайн • данные за ЧЧ:ММ"`; онлайн+устарело → `"данные за ЧЧ:ММ"`
- НЕ использует красный цвет (D-03)

**app/catalog/[secret]/layout.tsx** — вставка:
- Добавлен импорт `OfflineBar`
- `<OfflineBar />` вставлен сразу после `</header>` и перед `<SubgroupFlyout />`
- Layout остаётся серверным `async`-компонентом — App Router автоматически делает OfflineBar клиентским островом

## Критерии успеха

| Критерий | Статус |
|----------|--------|
| Полоска скрыта при онлайн + свежие данные (< 24 ч) | ✅ `return null` при `isOnline && !isStale` |
| Серая полоска «Офлайн • данные за ЧЧ:ММ» в офлайне | ✅ `bg-gray-100 text-gray-600` |
| Жёлтая полоска при данных старше 24 ч | ✅ `bg-yellow-50 text-yellow-800` |
| Метка читается из реального syncTimestamp в IDB | ✅ `getMeta("syncTimestamp")` |
| npx tsc --noEmit без ошибок | ✅ |
| npm run build без ошибок | ✅ |

## Отклонения от плана

Нет — план выполнен точно как написан.

## Known Stubs

Нет. OfflineBar читает реальный `syncTimestamp` из IDB (не заглушку).

## Threat Flags

Нет новых поверхностей. Угроза T-12-02 (getMeta бросает в приватном режиме iOS) закрыта `try/catch` как требовал план.

## Self-Check: PASSED

- `lib/useOnlineStatus.ts` — существует ✅
- `lib/formatSyncTime.ts` — существует ✅
- `components/OfflineBar.tsx` — существует ✅
- Коммит `1bdac80` — существует ✅
- Коммит `29b56fa` — существует ✅
- `npm run build` — прошёл без ошибок ✅
