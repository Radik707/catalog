---
phase: 19-reorder-my-orders
verified: 2026-06-28T23:00:00Z
status: passed
score: 11/11
overrides_applied: 0
human_verification:
  - test: "Открыть экран «Отправленные заказы» на телефоне (Vercel prod). Убедиться, что на каждой карточке заказа видна кнопка «Повторить заказ»."
    expected: "Синяя кнопка «Повторить заказ» на всю ширину карточки, под списком позиций."
    why_human: "Реальный рендер и тап-зоны на мобильном браузере нельзя проверить grep-ом."
  - test: "Нажать «Повторить заказ» на заказе с хотя бы одним товаром, который сейчас есть в каталоге. Проверить bottom-sheet сводку."
    expected: "Снизу появляется bottom-sheet с заголовком «Результат повтора». Показано «Добавлено N товаров в корзину» (зелёная галочка). Кнопка «Перейти в корзину →» присутствует."
    why_human: "Визуальный рендер bottom-sheet, safe-area, перекрытие нижними табами — только на устройстве."
  - test: "Нажать «Повторить» на заказе, все товары которого заведомо отсутствуют (остаток ≤ 1 или удалены из прайса)."
    expected: "Сводка показывает янтарный значок с текстом «Ни одного товара из заказа сейчас нельзя добавить». Кнопки «Перейти в корзину» нет."
    why_human: "Требует реальных данных каталога; нельзя симулировать без dev-сервера."
  - test: "Открыть панель настроек (шестерёнка в шапке). Убедиться, что присутствует пункт «Мои заказы»."
    expected: "Пункт «Мои заказы» с иконкой документа отображается в панели. Тап по нему закрывает панель и переходит на экран заказов."
    why_human: "Визуальное отображение панели и навигационный переход — только в браузере."
  - test: "Проверить пустое состояние экрана «Отправленные заказы» (на устройстве без истории, либо после «Очистить»)."
    expected: "Иконка документа, текст «Вы пока не отправляли заказов», ссылки «Вернуться в каталог» и «Перейти в корзину →»."
    why_human: "Визуальное оформление пустого состояния — только в браузере."
  - test: "Проверить, что кнопки переключения роли (Клиент / Агент) в SettingsPanel не мигают при первом открытии страницы."
    expected: "Активная кнопка роли корректно подсвечена с первого кадра (нет flash белого/синего до гидратации)."
    why_human: "Гидратационное мигание видно только на живом устройстве при первом рендере."
---

# Phase 19: «Повторить заказ» + «Мои заказы» — Verification Report

**Phase Goal:** Клиент видит список отправленных заказов и в один тап повторяет любой — позиции подставляются в корзину с проверкой актуальной цены/наличия. Локальная история честно подписана «Отправленные заказы», исчезнувшие товары помечаются прямо, а не подменяются молча.
**Verified:** 2026-06-28T23:00:00Z
**Status:** passed (приёмка владельца 2026-06-29)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Экран «Мои заказы» показывает локальную историю: дата-время, сумма, позиции, канал; пустое состояние оформлено | ✓ VERIFIED | `orders/page.tsx`: `OrderCard` рендерит `dateStr`, `channelLabel`, `entry.items.length`, `total.toFixed(2)`. Пустое состояние (строки 67–98) содержит иконку и текст. |
| 2 | Кнопка «Повторить» подставляет позиции в корзину в один тап | ✓ VERIFIED | `orders/page.tsx` стр. 231–237: `<button onClick={() => onRepeat(entry)}>Повторить заказ</button>`. `handleRepeat` вызывает `classifyReorder` → `addToCartWithQuantity`. |
| 3 | При повторе цена берётся актуальная (с учётом +5% Ефимовой), не замороженная | ✓ VERIFIED | `lib/reorder.ts` стр. 157: `effectivePrice(matched, priceForm)`. Import `effectivePrice` из `./pricing` подтверждён стр. 6. `priceAtOrder` используется только для сравнения (`roundPrice(currentPrice) !== roundPrice(oldPrice)`). |
| 4 | Товар с остатком ≤ 1 → `out_of_stock`; не найденный → `unavailable` | ✓ VERIFIED | `reorder.ts` стр. 161: `if (matched.stock <= 1)` → `out_of_stock`. Стр. 148: `if (!matched)` → `unavailable`. |
| 5 | Исчезнувшие/недоступные товары помечаются честно, не подменяются молча | ✓ VERIFIED | Модалка `ReorderSummaryModal` (стр. 307–475): `out_of_stock` → «нет в наличии», `unavailable` → «товар больше недоступен», `price_changed` → «было X → стало Y». Фолбэк по имени консервативный: при коллизии (несколько товаров с одним нормализованным именем) → `unavailable`. |
| 6 | Если добавить нечего — честное сообщение, кнопка корзины не показывается | ✓ VERIFIED | `orders/page.tsx` стр. 362–382: при `addedCount > 0` — зелёная галочка; при `=== 0` — янтарный значок с «Ни одного товара из заказа сейчас нельзя добавить». Кнопка «Перейти в корзину» в блоке `{addedCount > 0 && (…)}` стр. 455–462. |
| 7 | Вход на «Мои заказы» из меню настроек | ✓ VERIFIED | `SettingsPanel.tsx` стр. 99–108: `<a href={ordersPath}>Мои заказы</a>`. Путь через `usePathname().replace(/\/(cart|orders)(\/.*)?$/, "")` — без захардкоженного секрета. Клик закрывает панель (`onClick={() => setPanelOpen(false)}`). |
| 8 | Вход на «Мои заказы» из корзины | ✓ VERIFIED | `cart/page.tsx` стр. 63–68 (пустая корзина): `<a href={...orders}>Мои отправленные заказы →</a>`. Стр. 90–95 (заполненная): таблетка `bg-teal-500` «История заказов» → `/orders`. |
| 9 | `classifyReorder` — чистая функция без импортов React/DOM | ✓ VERIFIED | `reorder.ts` стр. 5–6: `import { Product, OrderHistoryItem } from './types'` и `import { PriceForm, effectivePrice } from './pricing'`. Никаких React/DOM/localStorage импортов. |
| 10 | `addToCartWithQuantity` присутствует в `useCart` и пробрасывается через `CartProvider` | ✓ VERIFIED | `useCart.ts` стр. 97–115: метод с капом `Math.min(existing.quantity + quantity, product.stock)` и `Math.min(quantity, product.stock)`. `CartProvider.tsx` стр. 14: поле в `CartContextValue`; стр. 25–26: `value={cart}` разворачивает весь хук. |
| 11 | Инвариант D-11: нет слов «статус/принято/подтверждено/в доставке» в UI | ✓ VERIFIED | Grep в `orders/page.tsx` нашёл эти слова только в комментарии-отрицании «Не содержит слов "статус"…». В JSX/UI-тексте отсутствуют. |

**Score: 11/11 truths verified**

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `lib/reorder.ts` | Чистая функция `classifyReorder`, 4 исхода | ✓ VERIFIED | 201 строка; экспортирует `ReorderOutcome`, `ReorderLineResult`, `ReorderResult`, `classifyReorder`. Коммит `9e0184e` + fix-коммиты `65a2440`, `264d004`, `e4fc940`. |
| `lib/useCart.ts` | Метод `addToCartWithQuantity(product, quantity)` | ✓ VERIFIED | Стр. 97–115, обёрнут в `useCallback([])`. Существующий `addToCart` не тронут. |
| `components/CartProvider.tsx` | `addToCartWithQuantity` в `CartContextValue` | ✓ VERIFIED | Стр. 14: тип `(product: Product, quantity: number) => void`. Коммит `c8d7108`. |
| `app/catalog/[secret]/orders/page.tsx` | Кнопка «Повторить» + `ReorderSummaryModal` | ✓ VERIFIED | Стр. 231–237: кнопка. Стр. 307–475: компонент сводки. Коммит `1092ad9` + `e4fc940`. |
| `components/SettingsPanel.tsx` | Пункт «Мои заказы» с путём через `usePathname` | ✓ VERIFIED | Стр. 51: `pathname.replace(…)`. Стр. 99–108: ссылка. Коммит `2afcaaa` + `7f8c08c`. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `lib/reorder.ts` | `lib/pricing.ts` | `import effectivePrice` | ✓ WIRED | Стр. 6 `reorder.ts`: `import { PriceForm, effectivePrice } from './pricing'`; вызов стр. 157. |
| `components/CartProvider.tsx` | `lib/useCart.ts` | `addToCartWithQuantity` через `value={cart}` | ✓ WIRED | `CartProvider` вызывает `useCart()` стр. 25, пробрасывает весь объект. Тип включает метод стр. 14. |
| `orders/page.tsx` | `lib/reorder.ts` | `import classifyReorder` | ✓ WIRED | Стр. 20 `orders/page.tsx`: `import { classifyReorder, ReorderResult } from '@/lib/reorder'`; вызов стр. 39. |
| `orders/page.tsx` | `components/CartProvider.tsx` | `addToCartWithQuantity` через `useCartContext` | ✓ WIRED | Стр. 18: `import { useCartContext }`; стр. 30: деструктуризация; стр. 47: вызов. |
| `orders/page.tsx` | `components/CatalogSyncProvider.tsx` | `products` через `useCatalogSyncContext` | ✓ WIRED | Стр. 14: import; стр. 26: `const { products }`. Используется стр. 39 в `classifyReorder`. |
| `SettingsPanel.tsx` | `next/navigation` | `usePathname` | ✓ WIRED | Стр. 4: `import { usePathname } from 'next/navigation'`; стр. 46: `const pathname = usePathname()`; стр. 51: вычисление `catalogBasePath`. |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `orders/page.tsx` → `handleRepeat` | `products` | `useCatalogSyncContext()` из IndexedDB | Да — IDB-кэш каталога (реальные товары) | ✓ FLOWING |
| `orders/page.tsx` → `handleRepeat` | `priceForm` | `useCatalogSettings()` из localStorage | Да — `"1"` или `"2"`, живое значение | ✓ FLOWING |
| `orders/page.tsx` → `handleRepeat` | `entries` | `useOrderHistoryContext()` из localStorage | Да — реальная история заказов | ✓ FLOWING |
| `lib/reorder.ts` | `currentPrice` | `effectivePrice(matched, priceForm)` из `lib/pricing.ts` | Да — вычисляется по актуальному `Product.price` и форме | ✓ FLOWING |

---

### Behavioral Spot-Checks

Step 7b: SKIPPED — нет runnable entry points без dev-сервера (проект деплоится на Vercel; локального dev у оператора нет).

---

### Requirements Coverage

| Требование | Источник плана | Описание | Статус | Доказательство |
|------------|----------------|----------|--------|----------------|
| REORD-01 | 19-02-PLAN.md | Экран «Мои заказы»: дата-время, сумма, позиции, канал; пустое состояние | ✓ SATISFIED | `OrderCard` рендерит все поля; пустое состояние стр. 67–98. |
| REORD-02 | 19-02-PLAN.md | Кнопка «Повторить» в один тап из карточки заказа | ✓ SATISFIED | Кнопка стр. 231–237; `handleRepeat` → `classifyReorder` → `addToCartWithQuantity`. |
| REORD-03 | 19-01-PLAN.md | Актуальная цена/наличие при повторе; честные пометки | ✓ SATISFIED | `effectivePrice` вместо `priceAtOrder`; 4 исхода; сводка показывает причины. |
| REORD-04 | 19-02-PLAN.md | Вход на «Мои заказы» из нижних табов или меню | ✓ SATISFIED | Пункт в `SettingsPanel` (меню ⚙) + ссылки в `cart/page.tsx`. Без 4-й вкладки (CONTEXT D-08 явно разрешает «меню» как альтернативу). |

---

### Fix-коммиты: верификация исправлений code review

| Исправление | Коммит | Что проверяли | Найдено в коде | Статус |
|-------------|--------|--------------|----------------|--------|
| WR-01: нормализация `oldPrice` — защита от NaN | `65a2440` | `typeof historyItem.priceAtOrder === 'number' && Number.isFinite(...)` | `reorder.ts` стр. 130 | ✓ VERIFIED |
| WR-02: консервативный фолбэк — не подставлять при коллизии | `264d004` | `candidates.length === 1` перед присвоением `matched` | `reorder.ts` стр. 142 | ✓ VERIFIED |
| WR-03: подсветка роли гейтится на `ready` | `7f8c08c` | `ready && role === "client"` в className | `SettingsPanel.tsx` стр. 80, 88 | ✓ VERIFIED |
| WR-04: честное усечение — `addedQty` / `requestedQty` / `capped` | `e4fc940` | Поля `capped`, `addedQty`, `requestedQty` в `ReorderLineResult`; рендер «добавлено N из M» | `reorder.ts` стр. 41–52, 181–186; `orders/page.tsx` стр. 438–444 | ✓ VERIFIED |

---

### Anti-Patterns Found

Сканирование файлов, изменённых в этапе (`lib/reorder.ts`, `lib/useCart.ts`, `components/CartProvider.tsx`, `components/SettingsPanel.tsx`, `app/catalog/[secret]/orders/page.tsx`):

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `orders/page.tsx` стр. 119, 121 | `confirm(...)` — нативный диалог браузера | ℹ Info | Не блокирует цель; confirm() для подтверждения удаления — допустимо для MVP |

Маркеры `TBD`, `FIXME`, `XXX` — не обнаружены. Заглушки `return null` / `return {}` / `return []` — не обнаружены в основных путях рендера.

---

### Human Verification Required

#### 1. Кнопка «Повторить» на карточке заказа — визуальный рендер

**Test:** Открыть экран «Отправленные заказы» на телефоне (Vercel prod), убедиться, что на каждой карточке заказа видна кнопка «Повторить заказ».
**Expected:** Синяя кнопка «Повторить заказ» (`bg-blue-600`) на всю ширину карточки под списком позиций.
**Why human:** Реальный рендер и тап-зоны на мобильном браузере нельзя проверить grep-ом.

#### 2. Bottom-sheet сводки при успешном повторе

**Test:** Нажать «Повторить заказ» на заказе с хотя бы одним товаром, который сейчас есть в каталоге.
**Expected:** Снизу появляется bottom-sheet «Результат повтора» с зелёной галочкой «Добавлено N товаров» и кнопкой «Перейти в корзину →». Панель не прячется под нижними табами клиента.
**Why human:** Визуальный рендер bottom-sheet, `safe-area-inset-bottom + 5rem` padding, перекрытие BottomTabBar — только на устройстве.

#### 3. Сводка при нулевом результате повтора

**Test:** Нажать «Повторить» на заказе, все товары которого заведомо недоступны.
**Expected:** «Ни одного товара из заказа сейчас нельзя добавить»; кнопки «Перейти в корзину» нет.
**Why human:** Требует реальных данных каталога; нельзя симулировать без dev-сервера.

#### 4. Пункт «Мои заказы» в меню настроек

**Test:** Открыть панель настроек (⚙ в шапке), проверить наличие пункта «Мои заказы».
**Expected:** Пункт с иконкой документа и текстом «Мои заказы» присутствует. Тап закрывает панель и переходит на `/catalog/{secret}/orders`.
**Why human:** Визуальное отображение панели и навигационный переход — только в браузере.

#### 5. Пустое состояние экрана заказов

**Test:** Открыть экран «Отправленные заказы» при пустой истории (очистить через кнопку «Очистить» или на устройстве без истории).
**Expected:** Иконка документа, текст «Вы пока не отправляли заказов», ссылки «Вернуться в каталог» и «Перейти в корзину →».
**Why human:** Визуальное оформление пустого состояния — только в браузере.

#### 6. Отсутствие гидратационного мигания роли

**Test:** Открыть SettingsPanel при сохранённой роли «Агент» (sales). Проверить первый кадр отображения кнопок «Клиент / Агент».
**Expected:** Кнопка «Агент» подсвечена с первого кадра без мигания. (Исправление WR-03 — флаг `ready` гейтит подсветку.)
**Why human:** Гидратационное мигание видно только на живом устройстве при первом рендере.

---

### Gaps Summary

Программных блокирующих пробелов не обнаружено. Все 11 наблюдаемых истин верифицированы на уровне кода. Статус `human_needed` выставлен, поскольку поведение UI (рендер bottom-sheet, safe-area, навигация, мигание гидратации) нельзя проверить без реального устройства и прод-деплоя.

---

_Verified: 2026-06-28T23:00:00Z_
_Verifier: Claude (gsd-verifier)_
