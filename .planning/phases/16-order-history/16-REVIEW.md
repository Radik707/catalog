---
phase: 16-order-history
reviewed: 2026-06-27T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - lib/types.ts
  - lib/useOrderHistory.ts
  - app/catalog/[secret]/orders/page.tsx
  - app/catalog/[secret]/cart/page.tsx
findings:
  critical: 1
  warning: 5
  info: 4
  total: 10
status: issues_found
---

# Этап 16: Отчёт код-ревью

**Дата:** 2026-06-27
**Глубина:** standard
**Проверено файлов:** 4
**Статус:** issues_found (найдены проблемы)

## Что это значит

Я провёл состязательное ревью истории заказов: проверял на баги, а не подтверждал, что код написан. Нашёл один блокер с реальным риском потери данных (его надо починить до отгрузки), пять предупреждений и четыре мелких замечания. Ниже — по каждому: где, в чём суть, как чинить.

## Summary

Проверены: тип `OrderHistoryEntry`/`OrderHistoryItem` (`lib/types.ts`), хук-стор `useOrderHistory` (localStorage, FIFO 20, мягкая деградация), страница `/orders` и встройка записи снимка в корзину.

Основная проблема — архитектурная: `useOrderHistory` сделан по образцу `useCart` (load-on-mount + save-on-change), но, в отличие от `useCart`, НЕ обёрнут в провайдер. При этом хук вызывается **тремя независимыми экземплярами** (страница `/orders`, `TelegramButton`, `MaxOrderButton`). Два из них (`TelegramButton` и `MaxOrderButton`) живут одновременно на одной странице корзины — и их независимые `save-on-change`-эффекты могут перезаписать друг друга, теряя только что записанный заказ. Это блокер.

## Critical Issues

### CR-01: Гонка двух экземпляров `useOrderHistory` на странице корзины → потеря записи истории

**File:** `app/catalog/[secret]/cart/page.tsx:233`, `app/catalog/[secret]/cart/page.tsx:301`; механика — `lib/useOrderHistory.ts:55-69`

**Issue:**
`TelegramButton` (строка 233) и `MaxOrderButton` (строка 301) каждый вызывают `useOrderHistory()`. Это **два разных экземпляра** хука с независимыми React-состояниями `entries` — провайдера (как `CartProvider` для `useCart`) у истории нет (подтверждено grep: `OrderHistoryProvider` отсутствует).

Оба экземпляра при монтировании читают одинаковую историю из localStorage. Дальше состояния расходятся:

1. Клиент жмёт MAX → `MaxOrderButton.addEntry` обновляет `entries` своего экземпляра → его `save-on-change`-эффект (`useOrderHistory.ts:65-69`) пишет в localStorage `[...старое, заказ_MAX]`. Экземпляр `TelegramButton` об этом не знает — его `entries` остаётся без MAX-записи.
2. Клиент жмёт Telegram → `TelegramButton.addEntry` берёт `prev` из **своего** устаревшего состояния (без MAX-записи) → `next = [...prev_без_MAX, заказ_TG]` → его `save-on-change` перезаписывает localStorage, **затирая заказ MAX**.

Итог: один из двух последовательно отправленных заказов исчезает из истории. Это прямой риск потери данных, и он тем вероятнее, что D-03 сознательно НЕ очищает корзину после отправки — то есть сценарий «отправил в Telegram, потом в MAX из той же корзины» штатный, а не экзотический.

Тот же класс гонки возможен между страницей `/orders` (если открыта) и корзиной, но главный путь — две кнопки на одной странице.

**Fix:**
Сделать единый источник истории — провайдер поверх одного экземпляра хука, как уже сделано для корзины (`CartProvider` + `useCartContext`). Все потребители (`orders/page.tsx`, обе кнопки) читают один контекст:

```tsx
// lib/useOrderHistory.tsx (новый провайдер по образцу components/CartProvider.tsx)
'use client';
import { createContext, useContext, ReactNode } from 'react';
import { useOrderHistory as useOrderHistoryStore } from './useOrderHistory';

const Ctx = createContext<ReturnType<typeof useOrderHistoryStore> | null>(null);

export function OrderHistoryProvider({ children }: { children: ReactNode }) {
  const value = useOrderHistoryStore();
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useOrderHistoryContext() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useOrderHistoryContext должен быть внутри OrderHistoryProvider');
  return ctx;
}
```

Затем смонтировать `OrderHistoryProvider` в `app/catalog/[secret]/layout.tsx` (рядом с `CartProvider`) и заменить во всех трёх точках `useOrderHistory()` на `useOrderHistoryContext()`.

Альтернатива (если не хотите провайдер): в `addEntry` строить новый массив поверх **свежего чтения localStorage**, а не поверх React-state, и одновременно синхронизировать локальный state. Это сложнее и хрупче — провайдер предпочтительнее и совпадает с уже принятым в проекте паттерном корзины.

## Warnings

### WR-01: Запись в историю даже при отменённой/неудачной отправке MAX

**File:** `app/catalog/[secret]/cart/page.tsx:330-365`

**Issue:**
В `MaxOrderButton.handleSend` снимок добавляется в историю (`addEntry`, строка 340) **до** `fetch` и `window.open`. Комментарий объясняет это намерением «записать ровно один раз». Но следствие: запись «отправленный заказ» появится в истории, даже если:
- `fetch` упал И запасной `window.open(.../:share...)` пользователь закрыл, ничего не отправив;
- сервер вернул ошибку, переход в MAX не состоялся.

История называется «Отправленные заказы» (инвариант HIST-03), а фактически фиксирует «нажал кнопку», а не «отправил». Для Telegram-кнопки запись идёт после `window.open` (строка 253→267) — поведение между двумя каналами несимметрично.

**Fix:** Это продуктовое решение (поведение vs строгость названия). Если строго «отправил» — записывать в `try` после успешного `window.open(.../?start=...)` и в `catch` после успешного fallback-share; учесть требование идемпотентности (одна запись на нажатие). Минимум — задокументировать осознанный выбор, чтобы это не читалось как баг.

### WR-02: `pluralItems` дублируется в трёх местах с расходящимся поведением

**File:** `app/catalog/[secret]/orders/page.tsx:250-255`, `app/catalog/[secret]/cart/page.tsx:383-388`, плюс `pluralOrders` в `orders/page.tsx:242-247`

**Issue:**
Функция склонения `pluralItems` скопирована в `cart/page.tsx` и `orders/page.tsx` (идентичная логика). Дублирование склонений — источник рассинхрона: правку придётся вносить в нескольких файлах, и легко забыть один. Это прямо нарушает раздел «Code Quality / code duplication» из задачи ревью.

**Fix:** Вынести `pluralItems`/`pluralOrders` (или общий `plural(n, [one, few, many])`) в `lib/plural.ts` и импортировать. Пример:

```ts
// lib/plural.ts
export function plural(n: number, forms: [string, string, string]): string {
  if (n % 10 === 1 && n % 100 !== 11) return forms[0];
  if ([2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100)) return forms[1];
  return forms[2];
}
```

### WR-03: `isValidEntry` не проверяет числовые/строковые поля, на которые опирается рендер

**File:** `lib/useOrderHistory.ts:14-23`; потребитель — `app/catalog/[secret]/orders/page.tsx:118,130-140`

**Issue:**
`isValidEntry` проверяет `id`, `items` (только что это массив), `createdAt`, `channel`, но НЕ проверяет `total` (число) и НЕ заглядывает внутрь `items`. При этом `OrderCard` вызывает `new Date(entry.createdAt)` — если `createdAt` строка, но не валидная дата, `toLocaleString` вернёт `"Invalid Date"` (строки 118-124). А `entry.items` после фильтра гарантированно массив, но его элементы могут быть мусором (например, `null`), и тогда `entry.items.map(...item => <OrderItem item={item}/>)` (строка 166) обратится к `item.name`/`item.id` у `null` → исключение рендера. Мягкая деградация в `OrderItem` (`!item.name`) спасает от пустого/частичного объекта, но не от `null`/не-объекта в массиве.

**Fix:** Усилить валидатор: проверять, что `createdAt` парсится в валидную дату, и что каждый элемент `items` — объект. Минимально безопасно:

```ts
return (
  typeof e.id === 'string' &&
  Array.isArray(e.items) &&
  e.items.every((it) => it && typeof it === 'object') &&
  typeof e.createdAt === 'string' &&
  !Number.isNaN(Date.parse(e.createdAt as string)) &&
  (e.channel === 'telegram' || e.channel === 'max')
);
```

### WR-04: Снимок истории жёстко прописывает `unit: 'шт'`, теряя реальную фасовку

**File:** `app/catalog/[secret]/cart/page.tsx:214`; поле — `lib/types.ts:25`

**Issue:**
`buildOrderSnapshot` пишет в каждую позицию `unit: 'шт'` константой. При этом тип `OrderHistoryItem.unit` заявлен как «единица измерения», а в корзине цена выводится тоже как «/ шт» (строка 141). Проект же, по CLAUDE.md, имеет ~40 правил фасовки (за блок/кг/ящик/упаковку). То есть в историю записывается заведомо упрощённая/потенциально неверная единица. Сейчас `unit` нигде в рендере истории не используется (см. IN-03), так что прямого визуального бага нет — но это «мёртвое и при этом неверное» значение, которое выстрелит, как только историю начнут показывать с единицами или строить «Повторить заказ» (D-09).

**Fix:** Либо протянуть реальную фасовку товара в снимок (если она доступна на уровне `product`), либо честно убрать `unit` из снимка/типа до тех пор, пока он не нужен, чтобы не хранить недостоверные данные.

### WR-05: `onError`-заглушка мини-фото в истории не показывает запасную иконку

**File:** `app/catalog/[secret]/orders/page.tsx:199-223`

**Issue:**
В `OrderItem` при ошибке загрузки `<img>` обработчик (строки 208-213) прячет картинку (`display:none`) и ставит `parent.dataset.error = '1'`. Но SVG-заглушка отрисована только в `else`-ветке (нет `imageUrl`, строки 216-221). Если `imageUrl` есть, но картинка не загрузилась, `<img>` скрывается, а заглушка НЕ появляется — остаётся пустой серый квадрат `w-8 h-8`. Атрибут `data-error="1"` нигде не читается (ни CSS, ни JS), то есть это мёртвая отметка. Комментарий «показывается SVG-заглушка ниже» не соответствует реальности — заглушки «ниже» в этой ветке нет.

**Fix:** Рендерить заглушку при ошибке. Простейший вариант — состояние:

```tsx
const [broken, setBroken] = useState(false);
// ...
{item.imageUrl && !broken ? (
  <img ... onError={() => setBroken(true)} />
) : (
  <SvgPlaceholder />
)}
```

или через CSS-правило по `[data-error="1"]`, отображающее фоновую иконку. Сейчас же `data-error` бессмысленно.

## Info

### IN-01: `OrderItem` использует индекс как часть ключа (`item.id ?? idx`)

**File:** `app/catalog/[secret]/orders/page.tsx:167`

**Issue:** Ключ списка `key={item.id ?? idx}` — при отсутствии `id` падает на индекс. Для статичной истории это безвредно, но идентификатор позиции (`Product.id`) внутри одного заказа в принципе может повторяться, если один товар попал в снимок дважды (сейчас не происходит, но контракт это не запрещает). Лучше использовать стабильный составной ключ, например `${entry.id}:${idx}` на уровне родителя.

**Fix:** Не блокирующее; при желании — `key={`${item.id ?? 'noid'}-${idx}`}`.

### IN-02: Несовместимый формат `id` записи (`crypto.randomUUID()` vs `Date.now().toString()`)

**File:** `app/catalog/[secret]/cart/page.tsx:259-261`, `app/catalog/[secret]/cart/page.tsx:332-334`

**Issue:** Fallback `Date.now().toString()` при двух быстрых отправках (Telegram + MAX подряд в пределах одной миллисекунды, в окружении без `crypto.randomUUID`) теоретически даст одинаковый `id`. Тогда `removeEntry(entryId)` (`useOrderHistory.ts:83-85`) удалит обе записи разом, а React-`key` совпадёт. Современные браузеры с `crypto.randomUUID` не затронуты; риск маргинальный.

**Fix:** В fallback добавить энтропию: `Date.now().toString() + '-' + Math.random().toString(36).slice(2)`.

### IN-03: Поле `OrderHistoryItem.unit` записывается, но нигде не отображается

**File:** `lib/types.ts:25`, `app/catalog/[secret]/orders/page.tsx` (рендер позиции, строки 226-234)

**Issue:** `unit` сохраняется в снимок (cart `:214`), но страница истории его не выводит — показываются только название, `×quantity` и сумма. Сейчас это мёртвое поле (связано с WR-04). Не баг, но стоит отметить как незавершённый контракт: либо показать единицу, либо отложить поле.

**Fix:** Решить вместе с WR-04 — показать `unit` в `OrderItem` или убрать до надобности.

### IN-04: `params.secret` в ссылках не подразумевает проверки доступа на этой странице

**File:** `app/catalog/[secret]/orders/page.tsx:42,48,63`, `app/catalog/[secret]/cart/page.tsx:56,63,90`

**Issue:** Страницы используют `params.secret` только для построения ссылок навигации — это нормально (защита секрета выполняется выше по дереву согласно CLAUDE.md: «UUID — только в переменных, проверка на сервере»). Сама история — клиентский localStorage, серверного секрета не касается. Отмечаю как сознательно проверенное, не как дефект: на этих страницах нет валидации `secret`, и это ожидаемо, при условии что middleware/серверная проверка секрета действительно стоит на маршруте `catalog/[secret]` (вне рамок изменённых файлов этапа 16 — стоит подтвердить, что она есть).

**Fix:** Не требуется в рамках этапа; убедиться, что серверная проверка `CATALOG_SECRET` для всего сегмента `[secret]` существует (вне этих файлов).

---

_Reviewed: 2026-06-27_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
