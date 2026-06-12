---
phase: 11-indexeddb-usecatalogsync
plan: "03"
subsystem: client-data-layer
tags: [indexeddb, offline, react, catalog-view, skeleton, pwa, off-01, off-02]
dependency_graph:
  requires: ["11-01", "11-02"]
  provides: ["components/CatalogView.tsx (offline-capable)", "app/catalog/[secret]/page.tsx (server-shell)"]
  affects: ["lib/useCatalogSync.ts"]
tech_stack:
  added: []
  patterns:
    - "Optional prop + hook fallback: products?: Product[] → productsProp ?? sync.products"
    - "Unconditional hook call (rules of hooks) with conditional result usage"
    - "Skeleton cards: animate-pulse grid matching production layout"
    - "Server component as auth shell only: secret check + initialMode, no data fetch"
key_files:
  created: []
  modified:
    - components/CatalogView.tsx
    - app/catalog/[secret]/page.tsx
decisions:
  - "[11-03] useCatalogSync() вызывается безусловно; productsProp ?? sync.products — проп в приоритете"
  - "[11-03] status = productsProp !== undefined ? ready : sync.status — обратная совместимость с prop-режимом"
  - "[11-03] Скелетон — 12 карточек в сетке grid-cols-2..2xl:grid-cols-6 с animate-pulse (D-02)"
  - "[11-03] Офлайн-заглушка — иконка + текст без кнопки; хук сам подтянет по событию online (D-03)"
  - "[11-03] page.tsx оставлен синхронным (убран async/await); async не нужен без getProducts()"
metrics:
  duration: "~10 мин"
  completed: "2026-06-12"
  tasks_completed: 2
  tasks_total: 2
  files_created: 0
  files_modified: 2
---

# Phase 11 Plan 03: Витрина каталога на клиентском офлайн-источнике (CatalogView + page.tsx)

**One-liner:** CatalogView переведён на useCatalogSync — products стал опциональным, скелетон при загрузке (D-02) и дружелюбная заглушка при офлайн-без-данных (D-03); page.tsx стал серверной оболочкой без SSR-данных, анти-паттерн №2 устранён.

## Что сделано

### Задача 1: CatalogView — опциональный products + useCatalogSync + скелетон/заглушка

Изменён `components/CatalogView.tsx`:

- Проп `products: Product[]` стал `products?: Product[]` (опциональный).
- В деструктуризации — `products: productsProp`, чтобы избежать конфликта с локальной переменной.
- `useCatalogSync()` вызывается на верхнем уровне компонента безусловно (правило хуков).
- Рабочий массив: `const products = productsProp ?? sync.products` — проп имеет приоритет, обеспечивая обратную совместимость с тестами и возможным прямым использованием.
- Статус: `const status = productsProp !== undefined ? "ready" : sync.status` — при переданном пропе нет смысла смотреть в хук.
- **D-02 (скелетон):** `status === "loading"` → 12 серых карточек с `animate-pulse` и `bg-gray-200` в сетке `grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-2 p-2`. Каждая карточка имеет aspect-square-блок под фото и две полоски под название/цену.
- **D-03 (заглушка офлайн):** `status === "empty-offline"` → центрированный блок с иконкой 📵, заголовком «Каталог ещё не загружен» и текстом «Подключитесь к интернету один раз — и дальше каталог будет работать даже без сети». Без кнопки — хук сам реагирует на событие `online`.
- **D-01 (бесшовная подмена):** `status === "ready"` → весь существующий рендер без изменений. Компонент не размонтируется при подмене данных → позиция прокрутки, открытый раздел и фильтры сохраняются.
- `npx tsc --noEmit` — без ошибок.

### Задача 2: page.tsx — серверная оболочка без SSR-данных

Изменён `app/catalog/[secret]/page.tsx`:

- Удалён импорт `getProducts` из `@/lib/sheets`.
- Удалён вызов `const products = await getProducts()`.
- Удалён проп `products={products}` из `<CatalogView />`.
- Функция стала синхронной (убран `async`, т.к. не осталось `await`).
- Сохранены: `export const dynamic = "force-dynamic"`, проверка секрета `params.secret !== process.env.CATALOG_SECRET → notFound()`, вычисление `initialMode` из `searchParams.filter`.
- Добавлены русские комментарии, объясняющие почему данные не прокидываются с сервера.
- `npm run build` завершился успешно — зелёный.

## Ключевые результаты

- **OFF-01 закрыт:** Каталог открывается без сети — данные приходят из IndexedDB через useCatalogSync.
- **OFF-02 закрыт:** Навигация по разделам/подгруппам, поиск и фильтры работают офлайн — CatalogView фильтрует массив в памяти, источник массива не важен.
- **D-02 реализован:** Первая загрузка показывает скелетон-карточки в сетке, не спиннер и не пустой экран.
- **D-03 реализован:** Офлайн без данных показывает понятное сообщение с инструкцией.
- **Анти-паттерн №2 устранён:** SSR-данные не прокидываются в CatalogView → офлайн-запуск не показывает пустой каталог.

## Acceptance Criteria — проверка

| Критерий | Статус |
|---|---|
| `products?: Product[]` в CatalogViewProps | PASS |
| useCatalogSync() вызывается безусловно | PASS |
| `productsProp ?? sync.products` — правильный приоритет | PASS |
| status=loading → сетка скелетонов с animate-pulse | PASS |
| status=empty-offline → текстовая заглушка без кнопки | PASS |
| useMemo grouped/flatFiltered/photoProducts сохранены | PASS |
| Lightbox, SearchBar, ScrollToTop сохранены | PASS |
| page.tsx НЕ содержит getProducts() | PASS |
| page.tsx НЕ передаёт products в CatalogView | PASS |
| Сохранена проверка secret → notFound() | PASS |
| Сохранены dynamic=force-dynamic и initialMode | PASS |
| Нет неиспользуемого импорта getProducts | PASS |
| npx tsc --noEmit без ошибок | PASS |
| npm run build зелёный | PASS |

## Deviations from Plan

None — план выполнен точно как написан. Единственное инженерное решение сверх задания: убран `async` с функции page.tsx (был async только из-за await getProducts; без него бессмысленен) — это улучшение, не отклонение.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: T-11-06 (mitigated) | app/catalog/[secret]/page.tsx | Проверка CATALOG_SECRET → notFound() сохранена на сервере; рефактор не ослабил контроль доступа |

## Known Stubs

Нет — данные витрины полностью связаны с IndexedDB через useCatalogSync; статус-экраны (скелетон и заглушка) являются намеренным дизайн-решением, не стабами.

## Self-Check

- [x] `components/CatalogView.tsx` существует — FOUND
- [x] `app/catalog/[secret]/page.tsx` существует — FOUND
- [x] Коммит `bb5ebe0` (CatalogView) — FOUND
- [x] Коммит `d67fbeb` (page.tsx) — FOUND
- [x] `npx tsc --noEmit` — PASS
- [x] `npm run build` — PASS

## Self-Check: PASSED
