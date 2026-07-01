# Phase 21: Quick-order набор + кратность упаковки — Pattern Map

**Mapped:** 2026-07-01
**Files analyzed:** 5 (1 новый компонент, 1 новый хелпер, 3 правки существующих)
**Analogs found:** 5 / 5 (все имеют прямой аналог в коде)

Этап — чистый фронт (Next.js 14 App Router + Tailwind + TS). Новый 4-й режим витрины
«Быстрый набор» для роли `sales`: плотная строка с мини-фото, названием, ценой с подписью
единицы, инлайн-полем количества (`QuantityInput` + «+/−») и добавлением в корзину прямо
из строки. Плюс тонкий хелпер `getUnit(product)` — «шов» под будущую ручную правку (этап 21b).

---

## File Classification

| Новый/изменяемый файл | Роль | Поток данных | Ближайший аналог | Качество совпадения |
|-----------------------|------|--------------|------------------|---------------------|
| `components/QuickOrderRow.tsx` (новый) | component | event-driven (запись в корзину из строки) | `components/ProductCard.tsx` режим «Список» (стр. 368–505) | exact (тот же плотный ряд с миниатюрой 56×56) |
| `lib/getUnit.ts` (новый) | utility | transform (product → строка единицы) | `lib/packaging.ts` (`getPackaging`) | role-match (тонкая обёртка над ним) |
| `components/CatalogView.tsx` (правка) | component | request-response (ветка рендера по `viewMode`) | сам файл — существующая ветка `viewMode === "list"` (стр. 322–327, 386–429) | exact (расширяем существующий свитч) |
| `components/CatalogSettings.tsx` (правка) | store/provider | CRUD (persist `viewMode` в localStorage) | сам файл — существующий тип `ViewMode` + persist (стр. 10, 109–158) | exact (добавляем 4-е значение) |
| `components/SettingsPanel.tsx` (правка) | component | event-driven (переключатель режима + гейт по роли) | сам файл — массив `views` + гейт роли (стр. 40, 56–60, 110–123) | exact |
| `app/catalog/[secret]/cart/page.tsx` (правка D-10, low-prio) | component | transform (снимок заказа) | сам файл — `buildOrderSnapshot` (стр. 208–225) | exact (замена литерала `'шт'`) |

---

## Pattern Assignments

### `lib/getUnit.ts` (utility, transform) — НОВЫЙ

**Analog:** `lib/packaging.ts` (`getPackaging(group, name)`).

**Что копировать:** сигнатуру и стиль тонкого чистого хелпера. В этапе 21 `getUnit` просто
делегирует `getPackaging(product.group, product.name)` (D-06). В этапе 21b тот же хелпер
научат сначала смотреть ручную правку, а `getPackaging()` останется дефолтом — быстрый набор
при этом повторно НЕ трогают. Это единственная точка «шва».

**Существующий вызов, который заменяется на `getUnit`** (`components/ProductCard.tsx:165`):
```typescript
import { getPackaging } from "@/lib/packaging";
const packaging = getPackaging(product.group, product.name);  // → "за шт" | "за блок" | "" ...
```

**Целевая форма нового хелпера** (`lib/getUnit.ts`):
```typescript
import { Product } from "./types";
import { getPackaging } from "./packaging";

// Единица счёта товара для строки быстрого набора и снимка заказа (D-06).
// Этап 21: просто обёртка над getPackaging(). Этап 21b: сюда добавится
// приоритет ручной правки из админ-панели, getPackaging() останется дефолтом.
// Возвращает подпись «за шт» / «за блок» / «за коробку» / … или "" (нет правила).
export function getUnit(product: Product): string {
  return getPackaging(product.group, product.name);
}
```

**Важно про формат:** `getPackaging` возвращает строку С предлогом («за шт», «за блок»),
а не голую единицу. Для подписи у цены это подходит как есть (см. `ProductCard.tsx:451`).
Для кнопки шага «+1 блок» и для снимка заказа (D-10, где нужно `'шт'`) единицу, возможно,
надо чистить от префикса «за ». Планировщику: решить, хранит ли `getUnit` строку с предлогом
или без — рекомендую вернуть КАК `getPackaging` (с предлогом) для обратной совместимости
подписи, а для кнопки/снимка срезать `"за "` на месте потребления.

---

### `components/QuickOrderRow.tsx` (component, event-driven) — НОВЫЙ

**Analog:** `components/ProductCard.tsx`, режим «Список» — лицевая сторона (стр. 368–458).
Берём миниатюру 56×56, раскладку `flex items-center gap-3`, подпись фасовки под ценой.
НЕ берём флип и оборотную сторону (D-03 — «без флипа и без открытия галереи»).

**Imports pattern** (образец из `ProductCard.tsx:1–7` + `AddToCartButton.tsx:1–5`):
```typescript
"use client";
import Image from "next/image";
import { Product } from "@/lib/types";
import { effectivePrice, PriceForm } from "@/lib/pricing";
import { getUnit } from "@/lib/getUnit";               // новый хелпер (D-06)
import { useCartContext } from "@/components/CartProvider";
import QuantityInput from "@/components/QuantityInput";
```

**Миниатюра 56×56 — копировать 1:1** (`ProductCard.tsx:394–414`, но БЕЗ `onClick={setFlipped}`
и без `CardCornerButton`):
```typescript
<div className="relative flex-shrink-0 w-14 h-14 rounded overflow-hidden border border-gray-100 bg-white">
  {product.imageUrl && !imgError ? (
    <Image
      src={product.imageUrl}
      alt={product.name}
      width={56}
      height={56}
      className="w-full h-full object-contain"
      unoptimized                       // прямой Cloudinary URL — тот же, что ловит SW-matcher
      onError={() => setImgError(true)}
    />
  ) : (
    <PhotoPlaceholder />                // импорт из ProductCard или вынести в общий файл
  )}
</div>
```

**Цена с подписью единицы** (`ProductCard.tsx:446–455`, заменить `packaging` на `getUnit`):
```typescript
const displayPrice = effectivePrice(product, priceForm);
const unit = getUnit(product);   // «за шт» / «за блок» / …
// ...
<div className="text-right">
  <span className="text-sm font-bold whitespace-nowrap">{displayPrice.toFixed(2)} ₽</span>
  {unit && <p className="text-xs text-gray-400">{unit}</p>}
</div>
```

**Скромный показ остатка** (D — «как в текущем режиме Список, без нового фильтра»)
(`ProductCard.tsx:434–440`):
```typescript
{inStock ? (
  <span className="text-xs text-emerald-600 font-medium">{product.stock} шт</span>
) : (
  <span className="text-xs text-gray-400">Нет в наличии</span>
)}
```

**СЕРДЦЕ строки — инлайн-количество с «+/−» + прямой ввод** — копировать паттерн
из `AddToCartButton.tsx:28–52` (блок «уже в корзине»). Именно он даёт «+ поле −» с капом:
```typescript
const { getQuantity, updateQuantity, addToCartWithQuantity } = useCartContext();
const qty = getQuantity(product.id);
// ...
<div className="flex items-center gap-1">
  <button
    onClick={() => updateQuantity(product.id, qty - 1)}
    className="w-7 h-7 rounded-lg bg-blue-100 text-blue-700 font-bold text-base flex items-center justify-center active:bg-blue-200"
  >−</button>
  <QuantityInput
    value={qty}
    max={product.stock}                                   // кап по остатку (D-08)
    onCommit={(v) => updateQuantity(product.id, v)}       // 0 = удаление (штатно, D-07)
    className="w-7 text-sm text-gray-900"
  />
  <button
    onClick={() => updateQuantity(product.id, qty + 1)}
    disabled={qty >= product.stock}                       // «+» блокируется на остатке (D-08)
    className="w-7 h-7 rounded-lg bg-blue-100 text-blue-700 font-bold text-base flex items-center justify-center active:bg-blue-200 disabled:opacity-40 disabled:cursor-not-allowed"
  >+</button>
</div>
```

**Первое добавление из строки** (когда `qty === 0`): либо переиспользовать
`<AddToCartButton product={...} />` как есть (он сам показывает «+» → превращается
в «− N +»), либо шаг «+1 {unit}» через `addToCartWithQuantity(product, 1)` (`useCart.ts:97`).
Рекомендация планировщику: вставить готовый `<AddToCartButton product={product} />` —
минимум нового кода, вся логика капа/добавления уже внутри (D-07, D-08).

**Локальное состояние ошибки фото** (`ProductCard.tsx` использует `useState`):
```typescript
const [imgError, setImgError] = useState(false);
```

**Кап по остатку — НЕ изобретать** (D-08): всё уже в `useCart.updateQuantity`
(`useCart.ts:77–91`, `Math.min(quantity, item.product.stock)`) и в `QuantityInput`
(`QuantityInput.tsx:51`, `if (n > max) n = max`). Компонент строки только вызывает
`updateQuantity` и передаёт `max={product.stock}`.

---

### `components/CatalogView.tsx` (component, request-response) — ПРАВКА

**Analog:** сам файл — существующая ветка `viewMode` (стр. 322–327) и рендер плоского/группового
списка (стр. 386–429). Новый режим встраивается ТОЧНО как `list`: без сетки, `flex-1`.

**Точка 1 — контейнер по режиму** (`CatalogView.tsx:322–327`), добавить ветку `quick`:
```typescript
const containerClass =
  viewMode === "list"
    ? "flex-1"
    : viewMode === "quick"                    // ← новый режим: плотный список без сетки
    ? "flex-1"
    : viewMode === "presentation"
    ? `flex-1 grid ${preset.cols} gap-1.5 p-1.5`
    : "flex-1 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-2 p-2";
```

**Точка 2 — выбор карточки** (`renderCard`, стр. 331–346). В режиме `quick` рендерить
`QuickOrderRow` вместо `ProductCard`:
```typescript
const renderCard = (product: Product) =>
  viewMode === "quick" ? (
    <QuickOrderRow key={product.id} product={product} priceForm={priceForm} />
  ) : (
    <ProductCard key={product.id} product={product} showPhotos={showPhotos} /* … */ />
  );
```

**Точка 3 — SSR-safe гейт по роли (КРИТИЧНО).** `useRole()` уже импортирован и вызван
(`CatalogView.tsx:17, 49`: `const { role, ready } = useRole();`). Паттерн гейта — копия
строки 348–351 (`showRepeatRow`): показывать только `ready && role === "sales"`, до `ready`
ничего не менять (иначе гидратация).
```typescript
// Если сохранён viewMode==="quick", но роль не sales (или ещё не ready) — не показываем
// режим набора: откатываемся к презентации, чтобы клиент не увидел режим агента.
const effectiveMode = viewMode === "quick" && !(ready && role === "sales")
  ? "presentation"
  : viewMode;
```
Далее использовать `effectiveMode` вместо `viewMode` в `containerClass`/`renderCard`/`ScrollToTop`.
`ScrollToTop` (стр. 355) — для `quick` передавать `"list"`.

**force-dynamic НЕ трогать** (правило проекта, CONTEXT §Established Patterns) — этот файл его
не касается, но убедиться, что правки не затрагивают `route.ts`/серверные части.

---

### `components/CatalogSettings.tsx` (store/provider, CRUD) — ПРАВКА

**Analog:** сам файл — тип `ViewMode` (стр. 10) и persist в localStorage (стр. 109–158).

**Точка 1 — расширить тип** (`CatalogSettings.tsx:10`):
```typescript
export type ViewMode = "list" | "grid" | "presentation" | "quick";  // + быстрый набор
```

**Точка 2 — валидация при чтении из localStorage** (стр. 110–111) — добавить `"quick"`:
```typescript
const v = localStorage.getItem("viewMode");
if (v === "list" || v === "grid" || v === "presentation" || v === "quick") setViewMode(v);
```

Persist-обёртка `updateViewMode` (стр. 151–154) не меняется — работает по строке `m`.
Дефолт остаётся `"presentation"` (стр. 91, D-01/D-02 — набор НЕ дефолт).

---

### `components/SettingsPanel.tsx` (component, event-driven) — ПРАВКА

**Analog:** сам файл — массив `views` (стр. 56–60) и SSR-safe гейт роли (стр. 40, 80/88).

**Точка 1 — добавить пункт «Быстрый набор»** в массив `views` (стр. 56–60), но показывать
его ТОЛЬКО роли `sales`. Паттерн гейта — тот же `ready && role === "sales"`, что уже применён
для подсветки роли (стр. 88):
```typescript
const views: { key: ViewMode; label: string }[] = [
  { key: "list", label: "☰ Список" },
  { key: "grid", label: "⊞ Сетка" },
  { key: "presentation", label: "◳ Презентация" },
  // «Быстрый набор» добавляем ниже условно — только для роли sales после ready
];
// при рендере:
const visibleViews = ready && role === "sales"
  ? [...views, { key: "quick" as ViewMode, label: "⚡ Набор" }]
  : views;
```

**Точка 2 — рендер кнопок** уже готов (стр. 112–122), просто маппить `visibleViews`
вместо `views`. Активная подсветка `viewMode === v.key` работает без изменений.

Иконка/подпись пункта — на усмотрение исполнителя (CONTEXT §Claude's Discretion).

---

### `app/catalog/[secret]/cart/page.tsx` (component, transform) — ПРАВКА D-10 (low-prio)

**Analog:** сам файл — `buildOrderSnapshot` (стр. 208–225).

**Точка — заменить жёсткий `'шт'`** (`cart/page.tsx:217`) на реальную единицу через `getUnit`.
Заметка планировщику (D-10): мелочь, НЕ блокирует этап; делать только если `getUnit` уже готов.
`getUnit` возвращает строку с предлогом («за шт») — для `unit` в снимке нужно, вероятно, срезать
`"за "` (см. заметку в разделе `lib/getUnit.ts`).
```typescript
// было:
unit: 'шт',
// станет (при наличии getUnit; product полный доступен в items):
unit: getUnit(product).replace(/^за\s+/, "") || 'шт',   // fallback 'шт' если правила нет
```
Проверить сигнатуру `buildOrderSnapshot`: сейчас `product` типизирован как
`Parameters<typeof effectivePrice>[0]` (стр. 209). Для `getUnit(product)` нужны поля
`group`/`name` — убедиться, что тип это допускает, иначе принять полный `Product`.

---

## Shared Patterns

### SSR-safe гейт по роли (`useRole` + `ready`)
**Source:** `lib/useRole.tsx:12–22, 56–63` (контракт `{ role, ready }`, `ready` в true последней
строкой `useEffect`) и применение `CatalogView.tsx:348–351`, `SettingsPanel.tsx:37–40, 80–88`.
**Apply to:** `CatalogView.tsx` (показ режима `quick`), `SettingsPanel.tsx` (пункт меню).
**Правило:** ветвиться ТОЛЬКО по `ready && role === "sales"`. До `ready` роль всегда `client` —
нельзя показывать/подсвечивать «набор» до `ready`, иначе первый кадр мигнёт и/или гидратация упадёт.
```typescript
const { role, ready } = useRole();
const showQuick = ready && role === "sales";   // единый инвариант этапа
```

### Кап по остатку (`stock`) — НЕ дублировать
**Source:** `lib/useCart.ts:77–91` (`updateQuantity`: `Math.min(quantity, item.product.stock)`),
`lib/useCart.ts:97–115` (`addToCartWithQuantity`: кап при добавлении),
`components/QuantityInput.tsx:51` (`if (n > max) n = max`),
`components/AddToCartButton.tsx:45` (`disabled={qty >= product.stock}` на «+»).
**Apply to:** `QuickOrderRow.tsx`. Компонент только ПЕРЕДАЁТ `max={product.stock}` и вызывает
`updateQuantity`/`addToCartWithQuantity` — новую логику капа не писать (D-08).

### Инлайн-количество (поле + «+/−»)
**Source:** `components/AddToCartButton.tsx:28–52` (готовый блок «− N +» с `QuantityInput`),
`components/QuantityInput.tsx` целиком (props `value`/`max`/`onCommit`, `inputMode="numeric"`,
`stopPropagation` на клике — стр. 75).
**Apply to:** `QuickOrderRow.tsx`. Рекомендация: переиспользовать `<AddToCartButton>` целиком —
он уже покрывает и первое добавление, и «− N +», и кап.

### Единица товара через единый хелпер
**Source:** новый `lib/getUnit.ts` поверх `lib/packaging.ts` (`getPackaging`).
**Apply to:** `QuickOrderRow.tsx` (подпись у цены + кнопка шага), `cart/page.tsx` (снимок заказа,
D-10). Единая точка под этап 21b — весь фронт читает единицу ТОЛЬКО через `getUnit`, не через
`getPackaging` напрямую (D-06).

### Персист настройки в localStorage
**Source:** `components/CatalogSettings.tsx:110–111` (валидация при чтении), `151–154`
(обёртка-сеттер `updateViewMode`).
**Apply to:** `CatalogSettings.tsx` — добавить `"quick"` в валидацию; сеттер и ключ `"viewMode"`
не меняются.

---

## No Analog Found

Файлов без аналога нет — все опираются на существующий код (режим «Список» `ProductCard`,
`getPackaging`, `useCart`/`QuantityInput`/`AddToCartButton`, `useRole`, persist `viewMode`).

---

## Metadata

**Analog search scope:** `components/`, `lib/`, `app/catalog/[secret]/cart/`
**Files scanned:** `ProductCard.tsx`, `CatalogView.tsx`, `CatalogSettings.tsx`, `SettingsPanel.tsx`,
`QuantityInput.tsx`, `AddToCartButton.tsx`, `useCart.ts`, `useRole.tsx`, `packaging.ts`,
`types.ts`, `cart/page.tsx`
**Pattern extraction date:** 2026-07-01
