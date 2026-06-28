# Phase 16: Локальная история заказов — Pattern Map

**Mapped:** 2026-06-27
**Files analyzed:** 4 (новых/изменяемых файлов в рамках этапа)
**Analogs found:** 4 / 4

## File Classification

| Новый/изменяемый файл | Роль | Поток данных | Ближайший аналог | Качество совпадения |
|---|---|---|---|---|
| `lib/useOrderHistory.ts` | hook / store | CRUD + localStorage (event-driven persist) | `lib/useCart.ts` + `lib/useFavorites.ts` | exact |
| `app/catalog/[secret]/orders/page.tsx` | page component | request-response (localStorage read) | `app/catalog/[secret]/cart/page.tsx` | exact |
| `app/catalog/[secret]/cart/page.tsx` (изменение) | page component | CRUD + side-effect write | `app/catalog/[secret]/cart/page.tsx` (себя же дополняет) | self |
| `lib/types.ts` (добавление типа) | model / type definition | — | `lib/types.ts` (себя же дополняет) | self |

## Pattern Assignments

---

### `lib/useOrderHistory.ts` (hook, localStorage CRUD)

**Аналог:** `lib/useCart.ts` (строки 1–136) и `lib/useFavorites.ts` (строки 1–68)

Хук истории строится по одному шаблону с `useCart` и `useFavorites`:
- именованный константный ключ `catalog-*`
- чистые функции `load*` / `save*` с `typeof window === 'undefined'` и тихим `try/catch`
- `useState` + `isLoaded`-флаг
- первый `useEffect` — загрузка при монтировании + `setIsLoaded(true)`
- второй `useEffect` — сохранение при изменении только если `isLoaded` уже `true`
- все мутации через `useCallback`

**Паттерн ключа localStorage** (`lib/useCart.ts`, строки 13, `lib/useFavorites.ts`, строка 6):
```typescript
const CART_KEY = 'catalog-cart';
const FAV_KEY  = 'catalog-favorites';
// Для истории — по аналогии:
const HISTORY_KEY = 'catalog-order-history';
```

**Паттерн load-функции с тихим try/catch** (`lib/useCart.ts`, строки 15–23):
```typescript
function loadCart(): CartItem[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(CART_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}
```
Для истории: при загрузке дополнительно фильтровать невалидные записи — мягкая деградация (D-14).
Пример проверки: `Array.isArray(arr) ? arr.filter(isValidEntry) : []` — аналог проверки в `useFavorites.ts`, строки 14–16.

**Паттерн save-функции** (`lib/useCart.ts`, строки 26–33):
```typescript
function saveCart(items: CartItem[]) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(CART_KEY, JSON.stringify(items));
  } catch {
    // localStorage может быть недоступен (приватный режим и т.д.)
  }
}
```

**Паттерн useState + isLoaded + двойной useEffect** (`lib/useCart.ts`, строки 35–50):
```typescript
export function useCart() {
  const [items, setItems] = useState<CartItem[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  // Загружаем при монтировании (только на клиенте)
  useEffect(() => {
    setItems(loadCart());
    setIsLoaded(true);
  }, []);

  // Сохраняем при каждом изменении (после первой загрузки)
  useEffect(() => {
    if (isLoaded) {
      saveCart(items);
    }
  }, [items, isLoaded]);
```

**Паттерн мутации через useCallback** (`lib/useCart.ts`, строки 94–96; `lib/useFavorites.ts`, строки 47–53):
```typescript
const clearCart = useCallback(() => {
  setItems([]);
}, []);
```

**Специфика истории — потолок 20 записей (D-13).** При добавлении новой записи:
```typescript
// FIFO-вытеснение: если больше MAX_HISTORY_ENTRIES — убрать самый старый (index 0)
const MAX_HISTORY_ENTRIES = 20;
const addEntry = useCallback((entry: OrderHistoryEntry) => {
  setEntries((prev) => {
    const next = [...prev, entry];
    return next.length > MAX_HISTORY_ENTRIES ? next.slice(next.length - MAX_HISTORY_ENTRIES) : next;
  });
}, []);
```

**Специфика истории — удаление одной записи** (аналог `removeFromCart`, `lib/useCart.ts`, строки 72–74):
```typescript
const removeEntry = useCallback((entryId: string) => {
  setEntries((prev) => prev.filter((e) => e.id !== entryId));
}, []);
```

---

### `lib/types.ts` (добавление типа `OrderHistoryEntry`)

**Аналог:** существующие интерфейсы в `lib/types.ts` (строки 1–15) и `lib/useCart.ts` (строки 7–10).

**Паттерн inline-типа для элемента хука** (`lib/useCart.ts`, строки 7–10):
```typescript
// Товар в корзине = товар + количество
export interface CartItem {
  product: Product;
  quantity: number;
}
```

**Новый тип по решениям D-07…D-11.** Размещать рядом с `Product` в `lib/types.ts` или в `lib/useOrderHistory.ts`:
```typescript
// Снимок позиции заказа в момент отправки (для истории заказов).
// id товара сохраняется как задел под «Повторить заказ» (v1.5, D-09).
export interface OrderHistoryItem {
  id: string;          // id товара (Product.id)
  name: string;        // название на момент заказа
  quantity: number;
  priceAtOrder: number; // effectivePrice(product, priceForm) — «цена как видел клиент» (D-08)
  unit: string;        // единица измерения (если есть в Product)
  imageUrl?: string;   // для мини-фото в списке истории; работает офлайн через кэш (D-10)
}

// Запись истории (один отправленный заказ).
export interface OrderHistoryEntry {
  id: string;           // уникальный id записи (crypto.randomUUID() или Date.now().toString())
  items: OrderHistoryItem[];
  total: number;        // сумма по priceAtOrder × quantity
  createdAt: string;    // ISO-строка (new Date().toISOString())
  channel: 'telegram' | 'max'; // канал отправки (D-02)
}
```

---

### `app/catalog/[secret]/orders/page.tsx` (page component, localStorage read)

**Аналог:** `app/catalog/[secret]/cart/page.tsx` — структура страницы копируется почти один в один.

**Паттерн структуры страницы: шапка + список + sticky-низ** (`cart/page.tsx`, строки 63–178):
```typescript
return (
  <div className="flex flex-col min-h-[calc(100vh-48px)]">
    {/* Заголовок страницы */}
    <div className="px-4 py-3 border-b border-gray-100 bg-white flex items-center justify-between gap-2">
      <a href={`/catalog/${params.secret}`} className="text-blue-600 text-sm font-medium active:opacity-70 flex-shrink-0">
        ← Каталог
      </a>
      <h2 className="font-semibold text-gray-900 flex-1 text-center">
        {items.length} {pluralItems(items.length)}
      </h2>
      <button onClick={() => { if (confirm("...")) { clearCart(); } }} className="text-xs text-red-500 font-medium active:opacity-70">
        Очистить
      </button>
    </div>

    {/* Список товаров */}
    <div className="flex-1 bg-white">
      {items.map(...)}
    </div>

    {/* Sticky-низ */}
    <div className="sticky bottom-0 bg-white border-t border-gray-200 px-4 py-4 shadow-[0_-4px_12px_rgba(0,0,0,0.06)]">
      ...
    </div>
  </div>
);
```

**Паттерн пустого состояния** (`cart/page.tsx`, строки 35–59):
```typescript
if (isEmpty) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4 text-center">
      <svg className="w-16 h-16 text-gray-200 mb-4" .../>
      <p className="text-gray-400 text-lg">Корзина пуста</p>
      <a href={`/catalog/${params.secret}`} className="mt-3 text-blue-600 text-sm font-medium active:opacity-70">
        Вернуться в каталог
      </a>
    </div>
  );
}
```
Для `/orders` — аналогично, текст: «Вы пока не отправляли заказов» (D-06).

**Паттерн confirm() для деструктивного действия** (`cart/page.tsx`, строки 78–80):
```typescript
onClick={() => {
  if (confirm("Вы действительно хотите очистить ВСЮ корзину?")) {
    clearCart();
  }
}}
```
Для истории: `confirm("Удалить всю историю заказов?")` → `clearHistory()`.

**Паттерн мини-фото с onError-заглушкой** (`cart/page.tsx`, строки 96–113):
```typescript
<div className="flex-shrink-0 w-12 h-12 rounded overflow-hidden border border-gray-100 bg-white">
  {product.imageUrl ? (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={product.imageUrl}
      alt={product.name}
      className="w-full h-full object-contain"
      loading="lazy"
      decoding="async"
    />
  ) : (
    <div className="w-full h-full flex items-center justify-center text-gray-300">
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75..." />
      </svg>
    </div>
  )}
</div>
```
В истории — аналогичный блок, но данные из `OrderHistoryItem.imageUrl`, а не из `Product`.

**Паттерн pluralItems** (`cart/page.tsx`, строки 307–312):
```typescript
function pluralItems(n: number): string {
  if (n % 10 === 1 && n % 100 !== 11) return "позиция";
  if ([2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100))
    return "позиции";
  return "позиций";
}
```
В `/orders/page.tsx` — аналогичный `pluralOrders(n)` для склонения слова «заказ».

**Паттерн навигации «← назад»** (`cart/page.tsx`, строки 68–71):
```typescript
<a
  href={`/catalog/${params.secret}`}
  className="text-blue-600 text-sm font-medium active:opacity-70 flex-shrink-0"
>
  ← Каталог
</a>
```
Для `/orders` ссылка возврата ведёт на корзину: `← Корзина` → `href={/catalog/${params.secret}/cart}`.

---

### `app/catalog/[secret]/cart/page.tsx` (изменение — запись в историю + ссылка на /orders)

**Аналог:** себя же — это дополнение к двум существующим `handleSend`.

**Точки встройки в `TelegramButton.handleSend`** (`cart/page.tsx`, строки 192–210):
```typescript
const handleSend = () => {
  // ... существующий код сборки text и window.open ...
  // ДОБАВИТЬ ПОСЛЕ window.open: запись в историю (D-01, D-02)
  // addEntry({ id, items: snapshot, total, createdAt, channel: 'telegram' })
};
```

**Точки встройки в `MaxOrderButton.handleSend`** (`cart/page.tsx`, строки 259–288):
```typescript
const handleSend = async () => {
  const text = buildText();
  // ДОБАВИТЬ ДО setSending(true) или внутри try после window.open: запись в историю
  // addEntry({ id, items: snapshot, total, createdAt, channel: 'max' })
  setSending(true);
  try { ... } catch { ... } finally { setSending(false); }
};
```

**Паттерн effectivePrice для формирования снимка** (`cart/page.tsx`, строки 26–30 и 198–200):
```typescript
// priceAtOrder = то, что видел клиент (D-08)
const priceAtOrder = effectivePrice(product, priceForm);
```

**Точка встройки ссылки на /orders в пустой корзине** (`cart/page.tsx`, строки 51–57):
```typescript
// ТЕКУЩИЙ КОД (строки 51–57):
<a
  href={`/catalog/${params.secret}`}
  className="mt-3 text-blue-600 text-sm font-medium active:opacity-70"
>
  Вернуться в каталог
</a>
// ДОБАВИТЬ ПОД НИМ (D-05):
<a
  href={`/catalog/${params.secret}/orders`}
  className="mt-2 text-blue-500 text-sm active:opacity-70"
>
  Мои отправленные заказы →
</a>
```

---

## Shared Patterns

### localStorage: ключи вида `catalog-*`
**Источник:** `lib/useCart.ts` строка 13; `lib/useFavorites.ts` строка 6
**Применять к:** `lib/useOrderHistory.ts`
```typescript
const HISTORY_KEY = 'catalog-order-history';
```

### SSR-безопасная загрузка из localStorage
**Источник:** `lib/useCart.ts` строки 15–23; `lib/useFavorites.ts` строки 10–19
**Применять к:** `lib/useOrderHistory.ts` (функция `loadHistory`)
```typescript
if (typeof window === 'undefined') return [];
try {
  const raw = localStorage.getItem(KEY);
  return raw ? JSON.parse(raw) : [];
} catch {
  return [];
}
```

### Тихий try/catch при записи в localStorage
**Источник:** `lib/useCart.ts` строки 26–33; `lib/useFavorites.ts` строки 22–28
**Применять к:** `lib/useOrderHistory.ts` (функция `saveHistory`)
```typescript
try {
  localStorage.setItem(KEY, JSON.stringify(data));
} catch {
  // localStorage может быть недоступен (приватный режим) — молча пропускаем
}
```

### isLoaded-флаг для предотвращения записи до монтирования
**Источник:** `lib/useCart.ts` строки 36–50
**Применять к:** `lib/useOrderHistory.ts`
```typescript
const [isLoaded, setIsLoaded] = useState(false);
useEffect(() => { setData(load()); setIsLoaded(true); }, []);
useEffect(() => { if (isLoaded) save(data); }, [data, isLoaded]);
```

### confirm() для деструктивных действий
**Источник:** `cart/page.tsx` строки 78–80
**Применять к:** `orders/page.tsx` — очистить всё + удалить одну запись (D-12)
```typescript
if (confirm("Удалить всю историю заказов?")) { clearHistory(); }
if (confirm("Удалить эту запись?")) { removeEntry(entry.id); }
```

### effectivePrice для снимка цены
**Источник:** `lib/pricing.ts` строки 21–26; используется в `cart/page.tsx` строки 27–30, 121, 151, 198
**Применять к:** `cart/page.tsx` (оба handleSend) при формировании `OrderHistoryItem.priceAtOrder`
```typescript
import { effectivePrice } from '@/lib/pricing';
// ...
priceAtOrder: effectivePrice(product, priceForm)
```

### Мини-фото с SVG-заглушкой при ошибке
**Источник:** `cart/page.tsx` строки 96–113
**Применять к:** `orders/page.tsx` — для отображения `OrderHistoryItem.imageUrl`

### Sticky-подвал страницы
**Источник:** `cart/page.tsx` строки 165–177
**Применять к:** `orders/page.tsx` — для итогового действия или инфо-блока внизу страницы
```typescript
<div className="sticky bottom-0 bg-white border-t border-gray-200 px-4 py-4 shadow-[0_-4px_12px_rgba(0,0,0,0.06)]">
```

### Комментарии в новом коде — на русском языке
**Источник:** `lib/useCart.ts`, `lib/useFavorites.ts`, `lib/useRole.tsx` — все файлы
**Применять к:** всем новым файлам этапа 16 (требование CLAUDE.md)

---

## No Analog Found

Нет файлов без аналога: все 4 файла имеют точные или близкие аналоги в кодовой базе.

| Файл | Роль | Поток | Причина отсутствия аналога |
|---|---|---|---|
| — | — | — | — |

---

## Metadata

**Scope поиска аналогов:** `lib/`, `app/catalog/[secret]/`, `components/`
**Прочитано файлов:** 7 (useCart.ts, useFavorites.ts, useRole.tsx, cart/page.tsx, CartProvider.tsx, layout.tsx, pricing.ts, types.ts)
**Дата маппинга:** 2026-06-27
