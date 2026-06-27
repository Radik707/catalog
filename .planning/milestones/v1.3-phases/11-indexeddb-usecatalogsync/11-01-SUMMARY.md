---
phase: 11-indexeddb-usecatalogsync
plan: "01"
subsystem: data-layer
tags: [indexeddb, idb, offline, catalog-db]
dependency_graph:
  requires: [idb (installed in phase 10), lib/types.ts]
  provides: [lib/catalogDb.ts — IndexedDB API wrapper]
  affects: [lib/useCatalogSync.ts (plan 02), CatalogView (plan 03)]
tech_stack:
  added: []
  patterns: [idb openDB, upgrade callback versioning, single-key object store]
key_files:
  created: [lib/catalogDb.ts]
  modified: []
decisions:
  - "[11-01] База catalog-db, stores products и meta — единственное место с IndexedDB API в проекте"
  - "[11-01] Упрощённый формат: Product[] под одним ключом 'all' (не record-per-item) — атомарные чтение/запись"
  - "[11-01] upgrade-колбэк с objectStoreNames.contains — stores создаются только при отсутствии (задел под миграцию схемы)"
  - "[11-01] dbPromise кэш — один openDB на жизнь вкладки"
metrics:
  duration: "~2 мин"
  completed_date: "2026-06-12"
  tasks_completed: 1
  tasks_total: 1
  files_created: 1
  files_modified: 0
---

# Phase 11 Plan 01: Обёртка IndexedDB (lib/catalogDb.ts) Summary

**One-liner:** Тонкая обёртка idb на базе catalog-db с четырьмя функциями (getProducts/saveProducts/getMeta/saveMeta) и upgrade-колбэком для версионирования схемы.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Создать обёртку lib/catalogDb.ts | 9948f96 | lib/catalogDb.ts (создан, 107 строк) |

## What Was Built

Создан клиентский модуль `lib/catalogDb.ts` — единственная точка доступа к IndexedDB в проекте.

**Функциональность:**
- `getProducts(): Promise<Product[]>` — читает весь массив товаров; при первом запуске возвращает `[]` (не падает, не возвращает undefined)
- `saveProducts(products: Product[]): Promise<void>` — атомарная перезапись массива товаров
- `getMeta<T>(key: string): Promise<T | undefined>` — читает метаданные (syncTimestamp, prevImageUrls — задел для этапов 12–13)
- `saveMeta(key: string, value: unknown): Promise<void>` — сохраняет произвольное метаданное

**Схема базы:**
- База: `catalog-db` (версия 1)
- Store `products` — весь `Product[]` под фиксированным ключом `"all"`
- Store `meta` — произвольные пары ключ/значение

**Версионирование:** upgrade-колбэк создаёт stores только при их отсутствии (`objectStoreNames.contains`). При росте `DB_VERSION` колбэк вызывается с прежним `oldVersion` и может мигрировать данные, не ломая каталог (угроза T-11-02 закрыта).

## Verification Results

- `npx tsc --noEmit` — завершён без ошибок
- Все 9 критериев приёмки выполнены (openDB, stores, функции, fallback, contains, импорты, нет localStorage)
- Файл 107 строк (минимум по плану: 40)

## Deviations from Plan

None — план выполнен точно как написан.

## Known Stubs

None — модуль полностью функционален. Стубы отсутствуют.

## Threat Flags

None — новых точек входа/выхода данных не создано. Данные остаются на устройстве агента (клиентская IDB). CATALOG_SECRET в IDB не хранится.

## Self-Check: PASSED

- lib/catalogDb.ts создан: FOUND
- Коммит 9948f96 существует: FOUND
- `npx tsc --noEmit` прошёл без ошибок: PASSED
