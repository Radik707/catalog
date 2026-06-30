# Этап 20: Чистый вход клиента + история поиска — Карта паттернов

**Составлено:** 2026-06-30
**Файлов в работе:** 8 (6 изменяются, 2 создаются)
**Аналоги найдены:** 8 / 8

> Назначение файла: для каждого файла этапа — роль, поток данных, ближайший
> существующий аналог в кодовой базе и конкретные образцы кода (с путями и
> номерами строк), которые планировщик подставляет в действия планов.
> Ядро повтора и роли уже готово — этап его **оборачивает**, не переписывает.

---

## Классификация файлов

| Файл (изменяется/создаётся) | Роль | Поток данных | Ближайший аналог | Качество совпадения |
|---|---|---|---|---|
| `app/catalog/[secret]/layout.tsx` (изм.) | layout / композиция шапки | request-response (SSR) | сам же (точечная правка блока шапки строки 60-67) | точное (самоправка) |
| `components/HeaderPrimaryAction.tsx` (изм.) | компонент-гейт роли | event-driven (роль) | сам же + `BottomTabBar` | точное |
| `components/CartIcon.tsx` (изм.) | компонент-иконка | event-driven (роль/корзина) | `BottomTabBar` (гейт роли) | role-match |
| `components/CatalogNav.tsx` (изм.) | компонент-навигация | event-driven (nav-контекст) | сам же (компоновка разделов/режима) | точное (самоправка) |
| `components/SearchBar.tsx` (изм.) | компонент-инпут (controlled) | event-driven (поиск) | сам же + крепление выпадашки | точное (самоправка) |
| `components/CatalogView.tsx` (изм.) | компонент-контейнер витрины | transform (фильтрация) + localStorage | `orders/page.tsx` (логика повтора) | role-match |
| `lib/useSearchHistory.ts` (нов.) | хук-store (localStorage) | localStorage CRUD (FIFO) | `lib/useOrderHistory.ts` | **точное (эталон)** |
| Компонент строки повтора + выпадашка истории (нов., имена на усмотрение) | компонент-презентация | event-driven + transform | `OrderCard`/`ReorderSummaryModal` (`orders/page.tsx`) + `BottomTabBar` (гейт) | role-match |

**Примечание по новым компонентам:** CONTEXT (§code_context) и UI-SPEC оставляют
на усмотрение исполнителя, делать ли строку повтора и выпадашку отдельными
файлами или инлайнить в `CatalogView`/`SearchBar`. Образцы кода ниже работают в
обоих вариантах.

---

## Назначения паттернов

### `app/catalog/[secret]/layout.tsx` (layout, SSR-композиция шапки)

**Аналог:** сам файл (точечная правка). Блок справа в шапке — строки 62-67.

**Текущая правая группа шапки (строки 60-68):**
```tsx
<div className="flex items-center justify-between px-2 h-12 gap-2 max-w-screen-2xl mx-auto w-full">
  <CatalogNav navData={navData} secret={params.secret} />
  <div className="flex items-center gap-1 shrink-0">
    {/* Планшет → ↻ «Обновить» (для торговых); телефон/ПК → ♥ «Избранное» */}
    <HeaderPrimaryAction secret={params.secret} />
    <SettingsButton />
    <CartIcon secret={params.secret} />
  </div>
</div>
```

**Что делает этап (D-03/D-04):**
- У роли `client` убрать из правой группы дубли нижних табов: `HeaderPrimaryAction`
  (= `FavoritesIcon`) и `CartIcon`. Оставить только `SettingsButton` (⚙).
- У роли `sales` правую группу НЕ трогать (↻ SyncButton + ⚙ + 🛒).
- Освободившееся место отдать `CatalogNav` (разделы на первый план).
- **Не менять**: `h-12` (48px) шапки, `sticky top-0 z-50 bg-blue-600`, порядок провайдеров.

**Важно по реализации гейта:** `layout.tsx` — серверный компонент (`async`,
`await getProducts()`), он НЕ может читать `useRole`. Поэтому гейт роли делается
**внутри** клиентских компонентов (`HeaderPrimaryAction`, `CartIcon`), а не
условием в самом layout. Layout остаётся местом монтирования; решение «что
скрыть» инкапсулируется в дочерних клиентских островах (см. ниже). Это тот же
приём, что уже применён: `HeaderPrimaryAction` сам выбирает рендер по роли.

---

### `components/HeaderPrimaryAction.tsx` (компонент-гейт роли, event-driven)

**Аналог:** сам файл — это и есть эталон SSR-safe гейта (D-05/D-10).

**Текущий код целиком (строки 12-17):**
```tsx
export default function HeaderPrimaryAction({ secret }: { secret: string }) {
  const { role, ready } = useRole();

  if (!ready) return <div className="h-9 w-9" />;
  return role === "sales" ? <SyncButton /> : <FavoritesIcon secret={secret} />;
}
```

**Что делает этап (D-03):** у `client` больше не показывать `FavoritesIcon`
(он в нижних табах). Целевая форма — sales отдаёт `SyncButton`, client отдаёт
резерв места (или `null`):
```tsx
if (!ready) return <div className="h-9 w-9" />;       // SSR-safe резерв до ready
return role === "sales" ? <SyncButton /> : null;       // client → ничего сверху
```

**Ключевой паттерн для всего этапа — резерв места до `ready`:** `<div className="h-9 w-9" />`
вместо `null`, чтобы не было сдвига раскладки при гидратации (UI-SPEC §Interaction).

---

### `components/CartIcon.tsx` (компонент-иконка, event-driven роль+корзина)

**Аналог гейта:** `BottomTabBar.tsx` строки 22, 41-43 (`if (!ready || role !== "client") return null`).

**Текущий код (строки 5-10):** компонент НЕ знает роль — рендерит ссылку-корзину всегда.
```tsx
export default function CartIcon({ secret }: { secret: string }) {
  const { items } = useCartContext();
  const count = items.length;
  return (
    <a href={`/catalog/${secret}/cart`} className="relative p-2">
```

**Что делает этап (D-03):** скрыть у `client` (корзина в нижних табах), оставить
у `sales`. Добавить гейт роли по образцу `BottomTabBar`:
```tsx
import { useRole } from "@/lib/useRole";
// ...
const { role, ready } = useRole();
const { items } = useCartContext();
// до ready не рисуем (или резерв места), у client — скрываем (есть в табах)
if (!ready) return null;          // либо <span className="w-9 h-9" /> для резерва
if (role === "client") return null;
```
**Образец гейта — `BottomTabBar.tsx` (строки 40-43):**
```tsx
// Гейт: не рендерим до монтирования или если роль не «Клиент» (D-11).
if (!ready || role !== "client") {
  return null;
}
```

---

### `components/CatalogNav.tsx` (компонент-навигация, event-driven)

**Аналог:** сам файл (компоновка разделов/режима — D-04).

**Текущая структура (строки 65-92):** контейнер `flex items-center gap-2 min-w-0 flex-1`;
свёрнутая кнопка режима (`bg-white text-blue-600`, глиф `▾`) → по тапу `expanded`
показывает 3 режима; ряд разделов виден только при `!expanded && mode === "catalog"`.

**Активный чип — инверсия (паттерн палитры, строки 74-78, 112-114):**
```tsx
mode === m
  ? "bg-white text-blue-600"                                   // активный — инверсия
  : "bg-blue-500 text-white active:bg-blue-400 hover:bg-blue-400"
```

**Тап-зона иконки раздела (строки 112-116) — сохранять `minWidth: 46`:**
```tsx
className={`shrink-0 flex flex-col items-center justify-center px-1.5 py-0.5 rounded leading-none transition-colors ${
  active ? "bg-white text-blue-600" : "text-white active:bg-blue-500 hover:bg-blue-500"
}`}
style={{ minWidth: 46 }}
```

**Что делает этап (D-04):** разделы на первый план. Освободившееся справа место
(после удаления дублей у client) отдать ряду разделов — чтобы они «дышали» и не
теснились с дублирующей кнопкой «Каталог». Точная компоновка переключателя
режима — на усмотрение исполнителя; сохранить градиент-подсказки прокрутки
(строки 124-131) и `text-[9px]`/`text-base` микро-подписи.

---

### `components/SearchBar.tsx` (компонент-инпут controlled, event-driven)

**Аналог:** сам файл (крепление выпадашки истории — D-07).

**Текущий контракт (строки 3-9):** полностью controlled — `value`/`onChange`/`count`
приходят из `CatalogView`. Это и есть точка интеграции истории поиска.
```tsx
interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  count: number;
}
```

**Контейнер уже `relative` (строка 12)** — выпадашку истории крепить сюда
(`absolute` под инпутом, ниже шапки по z, поверх витрины — UI-SPEC §z-index):
```tsx
<div className="px-4 py-2 bg-white border-b border-gray-100">
  <div className="relative">           {/* ← якорь для absolute-выпадашки истории */}
    {/* инпут поиска ... */}
  </div>
</div>
```

**Что делает этап (D-07/D-08):** при фокусе на пустом поле под `SearchBar`
показать выпадашку недавних запросов. Понадобятся новые пропсы (на усмотрение):
например `history: string[]`, `onPick(q)`, `onRemove(q)`, `onClear()`, плюс
локальный `focused`-флаг. Запись запроса — при выполнении поиска (по debounce/
blur). Существующий placeholder `"Поиск товара..."` и крестик очистки (строки
41-49) НЕ менять.

---

### `components/CatalogView.tsx` (контейнер витрины, transform + localStorage)

**Аналог логики повтора:** `app/catalog/[secret]/orders/page.tsx` (строки 23-55).

**Существующее состояние поиска (строки 31, 207-208) — источник истории:**
```tsx
const [search, setSearch] = useState("");
// ...
<SearchBar value={search} onChange={setSearch} count={visibleCount} />
```
История поиска должна согласоваться с этим потоком: запись запроса при поиске,
чтение для выпадашки. Источник товаров — `useCatalogSyncContext()` (строка 37,
`sync.products`) — офлайн-безопасно (IndexedDB), без новой сети (D-09).

**Место строки повтора (D-06):** над списком, между `SearchBar` (строка 208) и
контентом витрины. Компактная одна строка (`bg-white`, `border-b border-gray-100`,
высота ~40-48px — UI-SPEC §Interaction), НЕ блок-витрина.

**Паттерн обработчика повтора — копировать из `orders/page.tsx` (строки 36-55):**
```tsx
const result = classifyReorder(entry.items, products, priceForm);
for (const line of result.lines) {
  if ((line.outcome === 'added' || line.outcome === 'price_changed') && line.product) {
    addToCartWithQuantity(line.product, line.addedQty ?? line.historyItem.quantity);
  }
}
setReorderSummary({ ...result, secret });
```
Где для строки повтора `entry = entries[entries.length - 1]` (последний заказ,
D-06), `products` из `useCatalogSyncContext`, `priceForm` из `useCatalogSettings`,
`addToCartWithQuantity` из `useCartContext`, `entries` из `useOrderHistoryContext`.

---

### `lib/useSearchHistory.ts` (НОВЫЙ — хук-store localStorage, FIFO)

**Аналог — ЭТАЛОН:** `lib/useOrderHistory.ts` (весь файл). Скопировать структуру
1:1, заменив тип записи (`string` вместо `OrderHistoryEntry`) и ключ.

**Образец валидации/чтения с мягкой деградацией (строки 14-38):**
```ts
const HISTORY_KEY = 'catalog-search-history';  // в духе catalog-* (D-08)
const MAX_HISTORY_ENTRIES = 10;                // потолок ~8-10 (D-08)

function loadHistory(): string[] {
  if (typeof window === 'undefined') return [];           // SSR-safe
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    const arr = raw ? JSON.parse(raw) : [];
    // мягкая деградация: фильтруем только непустые строки
    return Array.isArray(arr) ? arr.filter((q) => typeof q === 'string' && q.trim()) : [];
  } catch {
    return [];                                              // битый JSON — пусто, не падаем
  }
}

function saveHistory(entries: string[]) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(entries));
  } catch {
    // localStorage недоступен (приватный режим iOS) — молча пропускаем
  }
}
```

**Образец хука load-on-mount + save-on-change + isLoaded (строки 54-99):**
```ts
export function useSearchHistory() {
  const [entries, setEntries] = useState<string[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => { setEntries(loadHistory()); setIsLoaded(true); }, []);
  useEffect(() => { if (isLoaded) saveHistory(entries); }, [entries, isLoaded]);

  // дедуп + свежие сверху + FIFO-потолок (отличие от useOrderHistory: дедуп по строке)
  const addQuery = useCallback((q: string) => {
    const query = q.trim();
    if (!query) return;
    setEntries((prev) => {
      const without = prev.filter((x) => x.toLowerCase() !== query.toLowerCase());
      const next = [query, ...without];                    // свежие сверху (D-08)
      return next.slice(0, MAX_HISTORY_ENTRIES);
    });
  }, []);

  const removeQuery = useCallback((q: string) => {
    setEntries((prev) => prev.filter((x) => x !== q));
  }, []);

  const clearHistory = useCallback(() => setEntries([]), []);

  return { entries, isLoaded, addQuery, removeQuery, clearHistory };
}
```
**Отличия от `useOrderHistory` (намеренные):** свежие СВЕРХУ (`[q, ...without]`),
а не FIFO с конца как у заказов; дедуп по тексту запроса (регистронезависимо);
потолок 10 вместо 20. Всё остальное (SSR-гейт, try/catch, isLoaded-флаг) —
дословно по эталону.

---

### Компонент строки повтора + выпадашка истории (НОВЫЕ или инлайн)

**Аналог строки повтора (CTA):** кнопка «Повторить заказ» в `OrderCard`
(`orders/page.tsx` строки 230-237):
```tsx
<button
  onClick={() => onRepeat(entry)}
  className="w-full py-2 bg-blue-600 text-white text-sm font-semibold rounded-xl active:bg-blue-700 transition-colors"
>
  Повторить заказ
</button>
```
Для этапа 20 текст — «↻ Повторить последний заказ» (UI-SPEC §Copywriting).

**Аналог сводки повтора:** `ReorderSummaryModal` в `orders/page.tsx` (строки
311-475). UI-SPEC требует **переиспользовать** его, а не изобретать новый.

> ⚠️ **Долг рефакторинга для планировщика:** `ReorderSummaryModal`, `pluralGoods`,
> `pluralOrders`, `pluralItems` — сейчас **локальные функции внутри**
> `orders/page.tsx`, НЕ экспортированы. Чтобы строка повтора в `CatalogView`
> переиспользовала ту же сводку, их надо **вынести в общий модуль** (например
> `components/ReorderSummaryModal.tsx` + `lib/plural.ts`) и заимпортить в обоих
> местах. Без выноса — дублирование, что прямо противоречит принципу этапа
> «без обвесов/нагромождений».

**Образец safe-area для bottom-sheet сводки (строки 341-344) — обязателен:**
```tsx
<div
  className="w-full bg-white rounded-t-2xl shadow-2xl pb-safe max-h-[80vh] overflow-y-auto"
  style={{ paddingBottom: 'calc(env(safe-area-inset-bottom, 0px) + 5rem)' }}
  onClick={(e) => e.stopPropagation()}
>
```
Резерв `+ 5rem` — чтобы контент не уходил под `BottomTabBar` (`h-16`/64px).

**Аналог выпадашки истории (список с крестиком):** строка `OrderItem`
(`orders/page.tsx` строки 264-304) + кнопка «Очистить» (строки 116-127):
```tsx
<button
  onClick={() => { if (confirm('Удалить всю историю заказов?')) clearHistory(); }}
  className="text-xs text-red-500 font-medium active:opacity-70 flex-shrink-0"
>
  Очистить
</button>
```
Для истории поиска: пункт = `text-sm text-gray-800` на `bg-white`, иконка-часы
слева `text-gray-400`, крестик `✕` справа `text-gray-400` (без `confirm` —
лёгкое действие), «Очистить» = `text-xs text-red-500 font-medium` (UI-SPEC).
Палитра намеренно нейтральная — история не должна соперничать с синей кнопкой
повтора (антисвалка).

---

## Общие (сквозные) паттерны

### SSR-safe гейт роли (D-05/D-10)
**Источник:** `components/HeaderPrimaryAction.tsx` (строки 13-16), `components/BottomTabBar.tsx` (строки 22, 40-43).
**Применить к:** правкам шапки (`CartIcon`, `HeaderPrimaryAction`) и строке повтора.
```tsx
const { role, ready } = useRole();
if (!ready) return <div className="h-9 w-9" />;   // резерв места, НЕ null, чтобы не дёргалась раскладка
if (role !== "client") return null;               // (или role === "sales" — в зависимости от элемента)
```
Строка повтора дополнительно требует `entries.length > 0` (UI-SPEC §Interaction):
`if (!ready || role !== 'client' || entries.length === 0) return null;`

### localStorage-хук с мягкой деградацией (D-08/D-09)
**Источник:** `lib/useOrderHistory.ts` (весь файл).
**Применить к:** `lib/useSearchHistory.ts`.
Канон: `typeof window === 'undefined' → []` (SSR), `try/catch` вокруг чтения и
записи (приватный режим iOS), фильтрация битых записей, load-on-mount +
save-on-change + `isLoaded`-флаг. Ключ — в стиле `catalog-*`.

### Переиспользование готового ядра повтора (D-06)
**Источник:** `app/catalog/[secret]/orders/page.tsx` (строки 36-55) + `lib/reorder.ts` (`classifyReorder`) + `useCart.addToCartWithQuantity` (`lib/useCart.ts` строки 97-145).
**Применить к:** обработчику строки повтора в `CatalogView`.
`classifyReorder(items, products, priceForm)` — чистая функция, 4 исхода (added /
price_changed / out_of_stock / unavailable) + кап по остатку (`addedQty`/`capped`).
В корзину кладутся только `added`/`price_changed` через `addToCartWithQuantity`.
**Не переписывать** — обернуть.

### Контексты-провайдеры уже подключены (новых не нужно)
**Источник:** `app/layout.tsx` (строка 51, `OrderHistoryProvider`), `app/catalog/[secret]/layout.tsx` (роль/настройки/корзина/синк/nav).
**Следствие:** в `CatalogView` доступны `useOrderHistoryContext`, `useCatalogSyncContext`,
`useCartContext`, `useCatalogSettings`, `useRole`, `useNav` — без монтирования
новых провайдеров. История поиска — локальный хук/состояние, провайдер не нужен
(одна точка потребления — `CatalogView`/`SearchBar`).

### Палитра и токены (UI-SPEC, без нового визуального языка)
**Источник:** `CatalogNav` (инверсия активного `bg-white text-blue-600`), `BottomTabBar`/`CartIcon` (бейдж `bg-red-500`), `orders/page.tsx` (CTA `bg-blue-600 active:bg-blue-700`, «Очистить» `text-red-500`), `SearchBar` (`bg-gray-50 rounded-xl`).
**Применить ко всему новому UI этапа.** Акцент (синий) зарезервирован только за
кнопкой повтора, «Перейти в корзину», активным разделом/режимом и ссылками-
действиями. Иконки исходов сводки (`text-green-500`/`text-blue-500`/`text-gray-400`/
`text-red-400`/`text-amber-500`) — НЕ менять (семантика этапа 19).

---

## Файлы без аналога

Нет. Все 8 файлов этапа имеют близкий существующий аналог в кодовой базе.
Этап целиком построен на оборачивании готового ядра (роль, повтор, localStorage-
хук) и копировании устоявшихся Tailwind-токенов — новых архитектурных паттернов
не вводится (соответствует принципу «без обвесов»).

---

## Метаданные

**Область поиска аналогов:** `app/catalog/[secret]/`, `components/`, `lib/`.
**Файлов прочитано:** 11 (layout, useOrderHistory, BottomTabBar, HeaderPrimaryAction, CatalogView, SearchBar, CartIcon, useRole, reorder, orders/page, CatalogNav, OrderHistoryProvider, useCart-фрагмент).
**Дата извлечения паттернов:** 2026-06-30.
