---
phase: 19-reorder-my-orders
plan: "01"
subsystem: reorder-core
tags: [reorder, cart, pricing, pure-function]
dependency_graph:
  requires: [lib/types.ts, lib/pricing.ts, lib/useCart.ts, components/CartProvider.tsx]
  provides: [lib/reorder.ts (classifyReorder), lib/useCart.ts (addToCartWithQuantity), components/CartProvider.tsx (addToCartWithQuantity)]
  affects: [план 19-02 (UI повтора), этап 20 (блок «Повторить» на Главной)]
tech_stack:
  added: []
  patterns: [pure-function, useCallback, Map-index, satisfies-narrowing]
key_files:
  created:
    - lib/reorder.ts
  modified:
    - lib/useCart.ts
    - components/CartProvider.tsx
decisions:
  - "Матчинг двойной: сначала O(1) по Map<id>, затем O(1) по Map<normalizedName> — без линейного поиска"
  - "Нормализация имени вынесена в локальную функцию normalizeName (trim + toLowerCase + replace /\\s+/ → ' ')"
  - "Сравнение цен округляется до 2 знаков через roundPrice() — устраняет float-погрешность ×1.05"
  - "out_of_stock: currentPrice всё равно вычисляется — UI может показать «было X стало Y» даже для отсутствующих"
  - "addToCartWithQuantity обёрнут в useCallback([]) — стабильная ссылка, паттерн как у addToCart"
  - "CartProvider пробрасывает через value={cart} целиком — новый метод входит автоматически, тип CartContextValue обновлён"
metrics:
  duration_minutes: 2
  completed_date: "2026-06-28"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 2
requirements:
  - REORD-03
---

# Phase 19 Plan 01: Ядро повтора заказа — Summary

**Одной строкой:** Чистый хелпер `classifyReorder` с четырьмя исходами (added/price_changed/out_of_stock/unavailable), актуальной ценой через `effectivePrice` и двойным матчингом (id → нормализованное имя); метод `addToCartWithQuantity` с капом по остатку и накоплением для существующих позиций.

## Задачи

| # | Задача | Статус | Коммит |
|---|--------|--------|--------|
| 1 | Чистый хелпер классификации повтора (lib/reorder.ts) | ✅ Выполнено | `9e0184e` |
| 2 | Метод добавления с количеством (useCart + CartProvider) | ✅ Выполнено | `c8d7108` |

## Что создано

### lib/reorder.ts (новый файл)

Чистый модуль без зависимостей на React/DOM. Экспортирует:

- **`ReorderOutcome`** — тип-союз четырёх исходов
- **`ReorderLineResult`** — результат по одной позиции: `outcome`, `historyItem`, `product?`, `currentPrice?`, `oldPrice`
- **`ReorderResult`** — агрегат: `lines[]` + `addedCount`
- **`classifyReorder(historyItems, catalog, priceForm)`** — главная функция

Логика классификации:
1. Строит два Map-индекса каталога: по `product.id` и по `normalizeName(product.name)`
2. Для каждой позиции истории: матчинг по id → фолбэк по имени → один из четырёх исходов
3. Цена актуальная: `effectivePrice(product, priceForm)` с учётом +5% Ефимовой (форма `"1"`)
4. Порог отсутствия: `stock <= 1` — тот же, что скрытие товаров на витрине
5. Сравнение цен: `roundPrice(currentPrice) !== roundPrice(oldPrice)` (округление до 2 знаков)

### lib/useCart.ts (дополнен)

Новый метод `addToCartWithQuantity(product, quantity)`:
- Кап по остатку: `Math.min(quantity, product.stock)`
- Накопление для существующих позиций: `Math.min(existing.quantity + quantity, product.stock)`
- При `stock <= 0` или `quantity <= 0` — ничего не делает
- Обёрнут в `useCallback([])` — стабильная ссылка

Существующий `addToCart` (+1) не затронут.

### components/CartProvider.tsx (дополнен)

`CartContextValue` расширен полем `addToCartWithQuantity: (product: Product, quantity: number) => void`. Метод пробрасывается автоматически через `value={cart}` (хук возвращает объект целиком).

## Отклонения от плана

Нет — план выполнен точно по спецификации.

## Угрозы (Threat Model)

| ID | Категория | Компонент | Исход |
|----|-----------|-----------|-------|
| T-19-01 | Tampering | lib/reorder.ts | Принято — хелпер не доверяет `priceAtOrder` для добавления, берёт актуальную цену из каталога |
| T-19-02 | Information Disclosure | содержимое заказа | Выполнено — хелпер чистый, без сетевых вызовов и логирования |

Новой серверной поверхности не введено: `force-dynamic` и `params.secret` не затронуты.

## Проверка (Verification)

- `npx tsc --noEmit` — прошёл с кодом 0 после обеих задач
- `lib/reorder.ts` — нет импортов React/DOM, только `./types` и `./pricing`
- `addToCartWithQuantity` присутствует в `useCart` и в типе `CartContextValue`

## Self-Check: PASSED

- [x] `lib/reorder.ts` — файл создан, содержит `classifyReorder` (148 строк, > min_lines 40)
- [x] Коммит `9e0184e` — существует (task 1)
- [x] Коммит `c8d7108` — существует (task 2)
- [x] TypeScript — без ошибок
