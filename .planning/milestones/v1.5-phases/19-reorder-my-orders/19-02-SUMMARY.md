---
phase: 19-reorder-my-orders
plan: "02"
subsystem: reorder-ui
tags: [reorder, orders-screen, settings-panel, bottom-sheet, ux]
dependency_graph:
  requires: [lib/reorder.ts (classifyReorder), components/CartProvider.tsx (addToCartWithQuantity), components/CatalogSyncProvider.tsx, components/CatalogSettings.tsx, components/OrderHistoryProvider.tsx]
  provides: [app/catalog/[secret]/orders/page.tsx (кнопка «Повторить» + сводка), components/SettingsPanel.tsx (вход «Мои заказы»)]
  affects: [REORD-01, REORD-02, REORD-04]
tech_stack:
  added: []
  patterns: [bottom-sheet-modal, usePathname-path-derivation, useCallback-stable-ref, safe-area-inset]
key_files:
  created: []
  modified:
    - app/catalog/[secret]/orders/page.tsx
    - components/SettingsPanel.tsx
decisions:
  - "Сводка результата — bottom-sheet (прикреплена снизу), не центрированная модалка: на телефоне удобнее, не прячется под нижними табами благодаря padding-bottom = safe-area + 5rem"
  - "Путь к orders в SettingsPanel вычисляется через usePathname().replace(/\\/(cart|orders).../) — без проброса secret пропом и без изменений layout.tsx (наименее инвазивный вариант)"
  - "Пункт «Мои заказы» показывается безусловно (без гейта ready/роль) — экран безвреден в обеих ролях, нет риска гидратации (D-10)"
  - "handleRepeat завёрнут в useCallback с зависимостями [products, priceForm, addToCartWithQuantity, params.secret] — стабильная ссылка для передачи в дочерние OrderCard"
metrics:
  duration_minutes: 10
  completed_date: "2026-06-28"
  tasks_completed: 2
  tasks_total: 2
  files_created: 0
  files_modified: 2
requirements:
  - REORD-01
  - REORD-02
  - REORD-04
---

# Phase 19 Plan 02: UI повтора заказа — Summary

**Одной строкой:** Кнопка «Повторить заказ» на каждой карточке истории с bottom-sheet сводкой (добавлено N / список пропущенных с причинами / переход в корзину) и вход «Мои заказы» в SettingsPanel через usePathname без захардкоженного секрета.

## Задачи

| # | Задача | Статус | Коммит |
|---|--------|--------|--------|
| 1 | Кнопка «Повторить» + сводка результата на экране заказов | Выполнено | `1092ad9` |
| 2 | Вход на «Мои заказы» из меню настроек (REORD-04) | Выполнено | `2afcaaa` |

## Что сделано

### app/catalog/[secret]/orders/page.tsx (расширен)

Страница сохранила всю существующую структуру (заголовок «Отправленные заказы», карточки заказов, пустое состояние, удаление/очистка). Добавлено:

**Новые импорты:**
- `useState`, `useCallback` из React
- `useCatalogSyncContext` — актуальный каталог из IDB (офлайн-безопасно, D-09)
- `useCatalogSettings` — форма цен (priceForm)
- `useCartContext` — метод `addToCartWithQuantity`
- `classifyReorder`, `ReorderResult` из `lib/reorder` (план 19-01)

**handleRepeat (обработчик повтора):**
1. `classifyReorder(entry.items, products, priceForm)` — классифицирует позиции
2. Для каждой строки с `outcome === 'added' | 'price_changed'` → `addToCartWithQuantity(product, qty)`
3. Открывает сводку (`setReorderSummary`) с секретом для ссылки в корзину

**OrderCard расширен:**
- Принимает `onRepeat: (entry: OrderHistoryEntry) => void`
- Кнопка «Повторить заказ» в синем стиле (bg-blue-600) в нижней части карточки

**ReorderSummaryModal (новый компонент):**
- Bottom-sheet модалка с тёмной подложкой (тап по подложке — закрыть)
- `paddingBottom: calc(env(safe-area-inset-bottom) + 5rem)` — не прячется под табами клиента
- При `addedCount > 0`: «Добавлено N товаров» + список notable строк + кнопка «Перейти в корзину →»
- При `addedCount === 0`: честное сообщение «Ни одного товара сейчас нельзя добавить» без кнопки перехода
- Notable строки: `price_changed` (добавлен, было→стало), `out_of_stock` (нет в наличии), `unavailable` (товар больше недоступен)
- Иконки исходов: синяя (price_changed), серая (out_of_stock), красная (unavailable)

**Утилита `pluralGoods`:** склонение «товар/товара/товаров» для сводки.

**Инварианты соблюдены:**
- Нет слов «статус/принято/подтверждено/в доставке» (D-11)
- Нет новых сетевых вызовов — данные только из контекстов (D-09)
- `force-dynamic` и `/api/products` не тронуты

### components/SettingsPanel.tsx (расширен)

- Добавлен импорт `usePathname` из `next/navigation`
- Вычисление базового пути: `pathname.replace(/\/(cart|orders)(\/.*)?$/, "")`
- Путь к заказам: `${catalogBasePath}/orders`
- Пункт-ссылка «Мои заказы» с иконкой документа (SVG), стиль как у кнопки «Установить приложение» (border-blue-200, bg-blue-50, text-blue-700)
- `onClick={() => setPanelOpen(false)}` — закрывает панель при переходе
- Пункт показывается безусловно (нет гейта роль/ready) — D-10 соблюдён без риска гидратации

**Вход из корзины подтверждён:** `cart/page.tsx` содержит ссылку «История заказов» (таблетка bg-teal-500) → `/orders` — не дублируется. REORD-04 закрыт связкой «меню + корзина».

## Отклонения от плана

Нет — план выполнен точно по спецификации.

## Угрозы (Threat Model)

| ID | Категория | Компонент | Исход |
|----|-----------|-----------|-------|
| T-19-03 | Tampering | сводка повтора | Выполнено — имена товаров выводятся как текст в JSX, без dangerouslySetInnerHTML; React экранирует автоматически |
| T-19-04 | Information Disclosure | содержимое заказа | Выполнено — логика повтора не делает сетевых вызовов; всё в памяти клиента |
| T-19-05 | Spoofing/Hydration | вход «Мои заказы» | Выполнено — пункт показывается безусловно (без завязки на роль), ошибка гидратации исключена |

## Проверка (Verification)

- `npx tsc --noEmit` — прошёл с кодом 0 после обеих задач
- Кнопка «Повторить заказ» присутствует в OrderCard (файл строка ~227)
- `classifyReorder` вызывается в handleRepeat с актуальными `products` из `useCatalogSyncContext`
- `ReorderSummaryModal` корректно обрабатывает addedCount === 0 (нет кнопки в корзину)
- Пункт «Мои заказы» в SettingsPanel формирует путь через usePathname (строка ~48–49)
- Слова «статус/принято/подтверждено» отсутствуют в UI-коде (только в служебном комментарии)

## Self-Check: PASSED

- [x] `app/catalog/[secret]/orders/page.tsx` — изменён, содержит «Повторить заказ», classifyReorder, ReorderSummaryModal
- [x] `components/SettingsPanel.tsx` — изменён, содержит «Мои заказы» и ordersPath через usePathname
- [x] Коммит `1092ad9` — существует (task 1)
- [x] Коммит `2afcaaa` — существует (task 2)
- [x] TypeScript — без ошибок (оба раза npx tsc --noEmit завершился с кодом 0)
