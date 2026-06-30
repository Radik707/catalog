---
phase: 20-client-clean-entry
verified: 2026-06-30T12:00:00Z
status: human_needed
score: 6/6 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Шапка роли «Клиент» на проде (телефон)"
    expected: "Справа в шапке только ⚙ Настройки — ♥ и 🛒 отсутствуют. Снизу видны табы Каталог · Избранное · Корзина. При переключении роли на «Торговый» — шапка возвращается к ↻ + ⚙ + 🛒, нижних табов нет. Перезагрузка не вызывает мелькания лишних иконок."
    why_human: "Визуальный рендер SSR-safe гейта и отсутствие layout-shift нельзя верифицировать без браузера"
  - test: "Строка «↻ Повторить последний заказ» и сводка на проде"
    expected: "Если есть история заказов (role=client) — над каталогом одна компактная строка с кнопкой. Тап → корзина пополняется, появляется сводка с честным текстом «Добавлено N товаров» и списком пропущенных/изменённых. Нет слов «статус/принято». Если нечего добавить — честное сообщение без кнопки перехода. У role=sales строки нет."
    why_human: "Функциональный тест повтора требует реальной истории заказов в localStorage на устройстве; offline-поведение проверяется только в браузере"
  - test: "История поиска в SearchBar на проде"
    expected: "После 2-3 запросов: фокус на пустом поле → выпадает список. Тап по пункту подставляет запрос в поле. Крестик ✕ удаляет конкретный запрос. «Очистить» убирает весь список. В авиарежиме история доступна."
    why_human: "Взаимодействие с localStorage и мобильный UX выпадашки (onPointerDown, blur-задержка) требуют живого браузера на устройстве"
---

# Этап 20: Чистый вход клиента + история поиска — Отчёт верификации

**Цель этапа:** В роли «Клиент» вход чище и быстрее: шапка разгружена от дублей с нижними табами, разделы вынесены на первый план, поиск помнит недавние запросы, повтор последнего заказа доступен одной компактной строкой. В роли «Торговый» вход и шапка не меняются.

**Дата верификации:** 2026-06-30
**Статус:** HUMAN NEEDED — все 6 автоматически верифицируемых must-have пройдены; 3 пункта требуют ручной приёмки владельца на проде после деплоя.

**Ре-верификация:** Нет — начальная верификация.

---

## Цель достигнута через код?

### Наблюдаемые истины (must-haves)

| # | Истина | Статус | Свидетельство |
|---|--------|--------|---------------|
| 1 | У роли `client` в шапке справа остаётся только ⚙ Настройки (♥ и 🛒 убраны) | ✓ VERIFIED | `HeaderPrimaryAction.tsx` строка 15: `role === "sales" ? <SyncButton /> : null`; `CartIcon.tsx` строка 22: `if (role === "client") return null` |
| 2 | У роли `sales` шапка не меняется (↻ SyncButton + ⚙ + 🛒 на месте) | ✓ VERIFIED | `HeaderPrimaryAction`: ветка `sales` возвращает `<SyncButton />` без изменений; `CartIcon`: рендерит ссылку корзины с бейджем `bg-red-500` для sales |
| 3 | `ReorderSummaryModal` и функции склонения вынесены в общие модули и переиспользуются | ✓ VERIFIED | `components/ReorderSummaryModal.tsx` — дефолтный экспорт, 177 строк, не заглушка; `lib/plural.ts` — 3 именованных экспорта; `orders/page.tsx` импортирует оба, локальных копий нет (`function ReorderSummaryModal` и `function pluralOrders` в page.tsx отсутствуют) |
| 4 | `useSearchHistory`: localStorage, потолок 10, дедуп, SSR-гейт, мягкая деградация | ✓ VERIFIED | `lib/useSearchHistory.ts`: ключ `catalog-search-history`, `MAX_HISTORY_ENTRIES = 10`, SSR-гейт `typeof window === 'undefined'`, `try/catch` на load/save, дедуп регистронезависимо (`x.toLowerCase() !== query.toLowerCase()`), методы `addQuery/removeQuery/clearHistory` через `useCallback` |
| 5 | Строка «↻ Повторить последний заказ» только при `role==='client' && entries.length > 0`; все хуки выше ранних return | ✓ VERIFIED | `CatalogView.tsx` строки 49-63: все хуки (useRole, useOrderHistoryContext, useCartContext, useSearchHistory, useCatalogSyncContext) вызываются безусловно до ранних return (строки 183, 212); `showRepeatRow = ready && role === "client" && orderEntries.length > 0` (строка 268) |
| 6 | История поиска проброшена в SearchBar; SearchBar показывает выпадашку при фокусе на пустом поле | ✓ VERIFIED | `CatalogView.tsx` строки 275-283: пропсы `history={searchEntries}`, `onPickHistory`, `onRemoveHistory`, `onClearHistory` переданы; `SearchBar.tsx`: `showHistory = focused && (history?.length ?? 0) > 0 && !value.trim()`, выпадашка `absolute z-40`, `onPointerDown` с `e.preventDefault()` для blur-safe тапа |

**Итог: 6/6 истин верифицированы**

---

### Необходимые артефакты

| Артефакт | Ожидание | Статус | Детали |
|----------|----------|--------|--------|
| `components/HeaderPrimaryAction.tsx` | Гейт роли: sales → SyncButton, client → null | ✓ VERIFIED | 16 строк, реальная логика, FavoritesIcon отсутствует |
| `components/CartIcon.tsx` | Гейт роли: client → null, sales → корзина с бейджем | ✓ VERIFIED | 46 строк, `useRole` и `useCartContext` до любого return, `items.length` → бейдж |
| `components/CatalogNav.tsx` | Разделы на первом плане через flex-1 | ✓ VERIFIED | Комментарий на строке 27 о передаче места разделам; `minWidth: 46`, `bg-white text-blue-600`, `from-blue-600` присутствуют |
| `components/ReorderSummaryModal.tsx` | Общая модалка-сводка, bottom-sheet, safe-area + 5rem | ✓ VERIFIED | 177 строк, `"use client"`, дефолтный экспорт, `paddingBottom: 'calc(env(safe-area-inset-bottom, 0px) + 5rem)'`, семантические цвета исходов (`text-green-500/text-blue-500/text-gray-400/text-red-400/text-amber-500`) |
| `lib/plural.ts` | pluralGoods / pluralOrders / pluralItems | ✓ VERIFIED | 36 строк, 3 чистые функции, правило `n%10`/`n%100`, исключения 11-14 |
| `lib/useSearchHistory.ts` | FIFO-хук, ключ catalog-search-history, офлайн-safe | ✓ VERIFIED | 91 строка, полная реализация по образцу useOrderHistory |
| `components/SearchBar.tsx` | Опциональные пропсы истории, выпадашка, aria-label | ✓ VERIFIED | 163 строки, пропсы `history?/onPickHistory?/onRemoveHistory?/onClearHistory?` опциональны, `focused` state, `onPointerDown` + `e.preventDefault()` для корректного blur |
| `components/CatalogView.tsx` | Строка повтора + история поиска + гейт роли | ✓ VERIFIED | 363 строки, все хуки безусловно на строках 49-63, строка повтора с гейтом строка 268, debounce 800мс для записи в историю (строка 86), ReorderSummaryModal в конце JSX |

---

### Ключевые связи (key links)

| От | К | Через | Статус | Детали |
|---|---|---|---|---|
| `components/CartIcon.tsx` | `lib/useRole` | `useRole()` | ✓ WIRED | import строка 3, вызов строка 13 |
| `components/HeaderPrimaryAction.tsx` | `lib/useRole` | `role === "sales"` | ✓ WIRED | import строка 3, вызов строка 12 |
| `app/catalog/[secret]/orders/page.tsx` | `components/ReorderSummaryModal` | import default | ✓ WIRED | строка 23: `import ReorderSummaryModal from '@/components/ReorderSummaryModal'` |
| `app/catalog/[secret]/orders/page.tsx` | `lib/plural` | import именованный | ✓ WIRED | строка 25: `import { pluralOrders, pluralItems } from '@/lib/plural'` |
| `components/CatalogView.tsx` | `lib/useSearchHistory` | `useSearchHistory()` | ✓ WIRED | import строка 27, вызов строка 58 |
| `components/CatalogView.tsx` | `components/ReorderSummaryModal` | import default | ✓ WIRED | import строка 25, рендер строка 355 |
| `components/CatalogView.tsx` | `lib/reorder` | `classifyReorder` | ✓ WIRED | import строка 23, вызов в `handleRepeatLast` строка 98 |

---

### Трассировка данных (Level 4)

| Артефакт | Переменная данных | Источник | Реальные данные | Статус |
|----------|-----------------|---------|----------------|--------|
| `CatalogView` → строка повтора | `orderEntries` | `useOrderHistoryContext()` → localStorage `catalog-order-history` | Да — реальная история из localStorage (этап 16) | ✓ FLOWING |
| `CatalogView` → история поиска | `searchEntries` | `useSearchHistory()` → localStorage `catalog-search-history` | Да — реальные строки из localStorage | ✓ FLOWING |
| `SearchBar` → выпадашка | `history` prop | пробрасывается из CatalogView | Да — тот же массив `searchEntries` | ✓ FLOWING |
| `CatalogView` → повтор | `products` | `useCatalogSyncContext()` → IndexedDB / fetch | Да — реальный каталог из IndexedDB (офлайн) или fetch | ✓ FLOWING |

---

### Поведенческие спот-проверки

| Поведение | Команда | Результат | Статус |
|-----------|---------|-----------|--------|
| Сборка Next.js без ошибок | `npm run build` | exit 0, все маршруты собраны, `/catalog/[secret]` — dynamic | ✓ PASS |
| `useSearchHistory` экспортирует функцию | файл читаем, `export function useSearchHistory` на строке 43 | Функция найдена | ✓ PASS |
| `ReorderSummaryModal` — клиентский компонент с дефолтным экспортом | строки 1, 12 | `'use client'` + `export default function ReorderSummaryModal` | ✓ PASS |
| `orders/page.tsx` не содержит локальных копий | grep `function ReorderSummaryModal\|function pluralOrders` | Нет совпадений | ✓ PASS |
| `force-dynamic` на витрине не сломан | grep в `app/catalog/[secret]/page.tsx` и `api/products/route.ts` | Оба файла содержат `export const dynamic = "force-dynamic"` | ✓ PASS |
| Правило хуков: все хуки до ранних return | строки вызовов хуков 49-63 vs ранние return строки 183, 212 | Все хуки выше return | ✓ PASS |

---

### Проверка антипаттернов

| Файл | Паттерн | Серьёзность | Примечание |
|------|---------|-------------|------------|
| `components/CatalogView.tsx` | Нет TBD/FIXME/TODO/XXX | — | Чисто |
| `components/SearchBar.tsx` | Нет маркеров долга | — | Чисто |
| `lib/useSearchHistory.ts` | Нет маркеров долга | — | Чисто |
| `components/ReorderSummaryModal.tsx` | Нет маркеров долга | — | Чисто |
| `lib/plural.ts` | Нет маркеров долга | — | Чисто |

Долговых маркеров не найдено. Стабов не найдено. Весь код — рабочая функциональность.

---

### Покрытие требований

| Требование | Источник | Описание | Статус | Свидетельство |
|-----------|---------|---------|--------|---------------|
| HOME-01 | 20-01-PLAN | Шапка client без дублей нижних табов, разделы на первом плане | ✓ SATISFIED | HeaderPrimaryAction + CartIcon + CatalogNav |
| HOME-02 | 20-02/20-03-PLAN | Общий модуль повтора + строка «↻ Повторить последний заказ» | ✓ SATISFIED | ReorderSummaryModal.tsx + plural.ts + строка в CatalogView |
| HOME-03 | 20-03-PLAN | Всё работает офлайн (localStorage/IndexedDB) | ✓ SATISFIED (частично) | useSearchHistory — localStorage, офлайн-safe; строка повтора читает orderEntries из localStorage; полная offline-проверка требует устройства |
| SRCH-01 | 20-03-PLAN | История запросов в поиске — localStorage, выпадашка при фокусе | ✓ SATISFIED | useSearchHistory + SearchBar с выпадашкой |

---

### Ручная приёмка (ожидает деплоя)

По условию задачи два чекпойнта `checkpoint:human-verify` в планах 20-01 и 20-03 являются визуальными и функциональными проверками на живом устройстве после деплоя. Они не могут быть верифицированы автоматически.

#### 1. Чистая шапка клиента (план 20-01, задача 4)

**Тест:** Откройте каталог на телефоне в роли «Клиент».
**Ожидаемо:** Справа в шапке только ⚙. Снизу — табы Каталог · Избранное · Корзина. При переключении на «Торговый»: шапка возвращается к ↻ + ⚙ + 🛒, нижних табов нет. Перезагрузка не вызывает мелькания.
**Почему требует человека:** Визуальный рендер на реальном устройстве, отсутствие layout-shift при гидратации.

#### 2. Строка повтора + история поиска на проде (план 20-03, задача 4)

**Тест:** В роли «Клиент» (при наличии истории заказов): проверить строку повтора, сводку, историю поиска, офлайн-режим. В роли «Торговый»: убедиться, что строки повтора нет.
**Ожидаемо:** Строка повтора видна, тап кладёт позиции в корзину и открывает сводку без слов «статус/принято». История поиска — выпадашка при фокусе, удаление крестиком, очистка кнопкой. Всё работает в авиарежиме.
**Почему требует человека:** Взаимодействие с localStorage на устройстве, мобильный UX выпадашки (onPointerDown/blur), офлайн-сценарий.

---

### Инварианты вехи v1.5 — проверка

| Инвариант | Статус |
|-----------|--------|
| `force-dynamic` + `cache:"no-store"` не тронуты | ✓ Оба файла подтверждены |
| Офлайн-модель v1.3: новые данные читаются из localStorage/IndexedDB | ✓ useSearchHistory → localStorage; строка повтора читает orderEntries из OrderHistoryProvider |
| Роль SSR-safe: до монтирования — нейтральный дефолт | ✓ Все три компонента и CatalogView: резерв места или `null` до `ready` |
| Локальная история — не «статус»: нигде нет «принято/подтверждено» | ✓ Проверено в ReorderSummaryModal и CatalogView |
| Только роль «Клиент»: у sales строки повтора нет | ✓ Гейт `role === "client"` в CatalogView строка 268 |

---

## Итог

**6/6 must-haves верифицированы автоматически.** Код реализует заявленную функциональность полностью: гейты роли правильно расставлены, правило хуков соблюдено, данные текут от реальных источников, дублирования нет, долговых маркеров нет, сборка зелёная.

**Статус: HUMAN NEEDED** — 3 пункта ручной приёмки на проде (визуальная проверка шапки, функциональный тест строки повтора и истории поиска с реальными данными на устройстве). Это запланированные чекпойнты этапа, не проблемы кода.

---

_Верифицировано: 2026-06-30_
_Верификатор: Claude (gsd-verifier)_
