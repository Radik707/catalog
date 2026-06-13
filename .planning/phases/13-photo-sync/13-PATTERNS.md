# Phase 13: Синхронизация фото - Pattern Map

**Mapped:** 2026-06-13
**Files analyzed:** 6 (2 new, 4 modified) + 1 критический INSPECT
**Analogs found:** 6 / 6

> Весь новый код — с русскими комментариями (CLAUDE.md). Только Tailwind. Компоненты — PascalCase, функциональные с хуками. Никаких правок серверного кода данных (`lib/sheets.ts`, `/api/products` — `force-dynamic` остаётся как есть).

---

## ⚠ КРИТИЧЕСКАЯ НАХОДКА (решить ДО планирования) — стыковка `next/image` ↔ SW

Это центральный интеграционный риск этапа. Проверено по коду, не по предположению:

- **`components/ProductCard.tsx`** рендерит фото через `next/image` (`<Image src={product.imageUrl} fill .../>`, строки 139-144 в сетке; `<Image width={56} height={56}/>`, строки 284-290 в списке).
- **`next.config.mjs`** НЕ содержит `images.unoptimized` и НЕ задаёт кастомный `loader` (проверено grep по всему репозиторию — совпадения только в `.planning/` и `.gitignore`, в исходном коде нет). Значит Next.js Image Optimizer **активен**: браузер фактически запрашивает `/_next/image?url=https%3A%2F%2Fres.cloudinary.com%2F...&w=…&q=…`, а НЕ прямой `res.cloudinary.com`.
- **SW-matcher** в `app/sw.ts` (строка 62): `/^https:\/\/res\.cloudinary\.com\//` — ловит только **прямой** Cloudinary-URL. Запросы карточек (`/_next/image?...`) под него **НЕ попадают** → фото из сетки/списка в текущем виде в `cloudinary-images` кэш НЕ кладутся.
- **`components/Lightbox.tsx`** (строки 26-28, 194-200) использует сырой `<img src={getHiResUrl(p.imageUrl)}>`, где `getHiResUrl` вставляет `/upload/f_auto,q_auto,w_1600/` → URL остаётся `https://res.cloudinary.com/...` → **матчер ловит, кэш работает**. НО это ДРУГОЙ URL, чем тот, что у Optimizer'а в карточке (hi-res 1600px vs thumbnail). Значит карточка и лайтбокс — **разные записи кэша** для одного товара (важно для diff/prefetch и для потолка 450).
- **Prefetch «огонь-и-забыл»** по сырым `product.imageUrl` (как в псевдокоде ARCHITECTURE.md Pattern 3) закэширует ТРЕТИЙ вариант URL (оригинал без трансформаций) — снова не тот, что реально запрашивает карточка через Optimizer. Без согласования матчера, рендера и prefetch офлайн-фото в карточках **не заработает вообще**.

**Три согласованных подхода (выбрать ОДИН, единый для рендера + matcher + prefetch):**

1. **`images.unoptimized: true` (для фото каталога) + raw Cloudinary URL везде** — карточка, лайтбокс и prefetch используют один формат URL (`res.cloudinary.com/...`), текущий matcher `^https://res.cloudinary.com/` ловит всё. Минимум кода, минимум «разных URL». Минус: теряется автоматическая оптимизация размеров Next.js (но фото уже WebP ~30-80КБ из Cloudinary, и `getHiResUrl` сам делает `f_auto,q_auto`). **Рекомендация мэппера: самый простой и предсказуемый для офлайна.**
2. **Кастомный `loader`, отдающий прямой Cloudinary-URL с трансформацией** — `next/image` остаётся, но `src` уходит на `res.cloudinary.com` напрямую (без `/_next/image`). Matcher ловит. Минус: разные `w`/`q` карточки = разные записи кэша, prefetch должен повторять ТУ ЖЕ трансформацию, что и loader.
3. **Расширить matcher на `/_next/image`** (matcher по `url.pathname === "/_next/image"`) + prefetch фактических `/_next/image?url=...&w=…&q=…` URL. Минус: каждый `w`/`q` = отдельная запись (взрыв числа записей против потолка 450), prefetch должен точно воспроизвести параметры, которые сгенерит Optimizer на устройстве агента (хрупко). **Наименее предпочтительно.**

Планировщик ОБЯЗАН зафиксировать выбор в плане; от него зависит matcher в `app/sw.ts`, формат URL в prefetch (`lib/syncPhotos.ts` / `useCatalogSync`), и нужна ли правка `next.config.mjs`/`ProductCard.tsx`.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `components/SyncButton.tsx` (NEW) | component (client island в шапке) | event-driven (клик → refetch) | `components/SettingsButton.tsx` + `components/OfflineBar.tsx` | exact (роль) |
| `lib/syncPhotos.ts` (NEW, либо внутри useCatalogSync) | utility / service | batch + diff + fire-and-forget fetch | `lib/useCatalogSync.ts` (sync-логика) + `lib/catalogDb.ts` (meta API) | role-match |
| `lib/useCatalogSync.ts` (MODIFY) | hook | request-response + orchestration | сам себя (расширение `sync()`, экспонирование `refetch`) | self |
| `app/sw.ts` (MODIFY) | config (service worker) | request-response (CacheFirst) | сам себя (matcher Cloudinary уже стоит) | self |
| `app/catalog/[secret]/layout.tsx` (MODIFY) | layout (server) | — (встраивание клиент-острова) | сам себя (`SettingsButton`/`CartIcon`/`OfflineBar` уже встроены) | self |
| `components/ProductCard.tsx` (INSPECT / возможно MODIFY) | component | request-response (рендер фото) | сам себя | self |
| `components/Lightbox.tsx` (INSPECT) | component | request-response (рендер hi-res) | сам себя | self |

---

## Pattern Assignments

### `components/SyncButton.tsx` (NEW — client island, кнопка ↻ в синей шапке)

**Аналоги:** `components/SettingsButton.tsx` (кнопка в шапке, стиль), `components/OfflineBar.tsx` (паттерн client-острова + чтение состояния синхронизации).

**Imports / директива** (копировать форму из `SettingsButton.tsx:1-3` и `OfflineBar.tsx:12-15`):
```typescript
"use client";

import { useState } from "react";
// источник refetch — расширенный хук (см. ниже); НЕ создавать второй экземпляр sync
```

**Паттерн кнопки в шапке** (форма и Tailwind из `components/SettingsButton.tsx:9-37` — точная база для стиля синей шапки `blue-600`, размеры `h-9 w-9`, белая иконка, hover):
```typescript
<button
  onClick={handleRefresh}
  aria-label="Обновить каталог"
  disabled={!isOnline || busy}
  className={`flex h-9 w-9 items-center justify-center rounded-full transition-colors ${
    busy ? "bg-white/30" : "hover:bg-white/15"
  }`}
>
  {/* SVG ↻ (heroicons arrow-path), белый, w-6 h-6 text-white — как в SettingsButton.
      Состояния (Claude's Discretion D-02): busy → animate-spin; done → короткая галочка ✓. */}
</button>
```
Иконку рисовать тем же приёмом, что в `SettingsButton.tsx:18-35` (`<svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>`). Вращение — Tailwind `animate-spin`. Галочка «готово» — кратковременный state-флаг (≈1.5 c), как тик в `OfflineBar.tsx:49-53`.

**Disabled-офлайн** (D-03): паттерн уже применён к кнопке отправки заказа этапа 12 — `disabled={!isOnline}` + `title`. Состояние сети брать через `useOnlineStatus()` (`lib/useOnlineStatus.ts:15`) — НЕ читать `navigator.onLine` напрямую.

**Размещение в шапке** — см. layout ниже: рядом с `<SettingsButton />` и `<CartIcon />` в правом блоке `app/catalog/[secret]/layout.tsx:33-36`.

---

### `lib/syncPhotos.ts` (NEW utility) ИЛИ блок внутри `useCatalogSync` (Claude's Discretion)

**Аналог:** псевдокод ARCHITECTURE.md Pattern 3 (строки 188-201) + готовый API `lib/catalogDb.ts`.

**meta-API уже готов** — `lib/catalogDb.ts:95-107` (`getMeta`/`saveMeta`), ключ `prevImageUrls` заложен на этапе 11 (комментарий `catalogDb.ts:92-93`):
```typescript
import { getMeta, saveMeta } from "@/lib/catalogDb";
// чтение прошлого списка ссылок для diff:
const prev = (await getMeta<string[]>("prevImageUrls")) ?? [];
// сохранение нового списка после синхронизации:
await saveMeta("prevImageUrls", newUrls);
```

**Diff + гибридный prefetch** (D-04 — новые сразу, первая загрузка лениво):
```typescript
// Русские комментарии обязательны
export async function syncPhotos(products: Product[]): Promise<void> {
  // Собираем актуальные ссылки на фото (Boolean — отсекаем товары без imageUrl)
  const newUrls = products.map((p) => p.imageUrl).filter((u): u is string => Boolean(u));

  const prevUrls = (await getMeta<string[]>("prevImageUrls")) ?? [];

  // D-04: при ПЕРВОЙ синхронизации (prevUrls пуст) — НЕ качаем все ~900 фото
  // (взрыв квоты iOS, анти-паттерн №1). Кэш наполнится лениво по просмотру.
  if (prevUrls.length > 0) {
    const toFetch = newUrls.filter((url) => !prevUrls.includes(url));
    // Огонь-и-забыл: SW перехватит и закэширует. Ошибки — молча (как офлайн, D-04 этапа 11).
    for (const url of toFetch) {
      fetch(url /* формат URL — ПО ВЫБРАННОМУ ПОДХОДУ из критической находки */).catch(() => {});
    }
  }

  // После любой синхронизации — обновляем список для следующего diff
  await saveMeta("prevImageUrls", newUrls);
}
```
**⚠ Формат URL в `fetch(url)` ОБЯЗАН совпадать с тем, что matcher SW ловит и что реально запрашивает рендер** (см. критическую находку). Если выбран подход 1 (raw Cloudinary) — `fetch(product.imageUrl)`. Если подход 2/3 — prefetch должен повторять трансформацию loader'а / параметры Optimizer'а.

**Обработка ошибок** — молча, как везде в офлайн-слое: `lib/useCatalogSync.ts:161-170` (catch → `console.warn`, UI не трогаем). Тот же дух для prefetch.

---

### `lib/useCatalogSync.ts` (MODIFY — экспонировать `refetch()` + вызвать `syncPhotos`)

**Аналог:** сам файл. Сейчас `sync()` приватная (`useCatalogSync.ts:72-174`), наружу не отдаётся (контракт `UseCatalogSyncResult`, строки 30-39 — без refetch).

**Точка вставки prefetch фото** — после успешного `setProducts(fresh)` + `saveProducts(fresh)` (строки 143-148, внутри `if (isCurrent())`), порядок строго по Потоку 4 ARCHITECTURE.md (строки 281-298): fetch → saveProducts → saveMeta(syncTimestamp) → **diff+prefetch новых** → saveMeta(prevImageUrls) → setProducts. Вызвать `syncPhotos(fresh)` здесь же (он сам читает/пишет `prevImageUrls`).

**Экспонирование `refetch`** — `sync` уже стабилен через `useCallback([])` (строка 174), достаточно вернуть его. Расширить контракт:
```typescript
export interface UseCatalogSyncResult {
  products: Product[];
  isOnline: boolean;
  syncedAt: number | null;
  status: CatalogStatus;
  refetch: () => Promise<void>; // НОВОЕ: ручная синхронизация для кнопки «Обновить» (D-01)
}
// ...
return { products, isOnline, syncedAt, status, refetch: sync };
```
**Защита от гонки уже встроена** — `syncGenRef` / `isCurrent()` (строки 63-76, 137-149): ручной refetch и авто-sync по событию `online` не перезатрут друг друга. Ничего нового изобретать не надо.

**Как SyncButton получает `refetch`:** `useCatalogSync` сейчас вызывается внутри `CatalogView` (`CatalogView.tsx:32`), а кнопка живёт в `layout.tsx` (выше по дереву). Прямой проп невозможен. Планировщику решить (Claude's Discretion): либо поднять состояние синхронизации в React Context (как `CatalogSettings`/`NavProvider` в layout), либо SyncButton вызывает собственный лёгкий триггер. **Рекомендация мэппера:** контекст-провайдер вокруг шапки и витрины (паттерн уже массово используется — `CatalogSettingsProvider`, `NavProvider` в `layout.tsx:26-27`), чтобы и кнопка, и `OfflineBar`, и `CatalogView` делили один экземпляр sync. Это попутно решает D-02 (метка свежести в `OfflineBar` обновляется после ручного refetch — сейчас `OfflineBar` читает `syncTimestamp` из IDB независимо, `OfflineBar.tsx:32-44`).

---

### `app/sw.ts` (MODIFY — согласовать matcher с реальным URL фото)

**Аналог:** сам файл, блок CacheFirst (`app/sw.ts:61-72`) + блок NetworkFirst (строки 48-54).

**Готовая основа** — matcher Cloudinary, `cacheName: "cloudinary-images"`, `ExpirationPlugin({ maxEntries: 450, maxAgeSeconds: 7*24*60*60 })` уже стоят. D-05: потолок 450 + 7 дней НЕ снимать.

**⚠ Урок про якорь `^`** (комментарий `app/sw.ts:45-47`): Serwist прогоняет regex по `url.href` (полный адрес `https://домен/path`), а НЕ по pathname. Поэтому:
- NetworkFirst использует `/\/api\/products/` (БЕЗ `^`) — строка 49.
- CacheFirst Cloudinary использует `/^https:\/\/res\.cloudinary\.com\//` (`^` тут валиден, т.к. href сам начинается с `https://res.cloudinary.com` для прямого Cloudinary).
- Если выбран подход 3 (кэшировать `/_next/image`) — matcher писать как функцию `({ url }) => url.pathname === "/_next/image"` (БЕЗ regex-якоря по pathname), по образцу комментария про href. Это нетривиально — учесть при выборе подхода.

**Изменение** зависит от выбранного подхода (см. критическую находку): подход 1/2 → matcher остаётся как есть (raw Cloudinary), правок в `sw.ts` минимум/нет; подход 3 → добавить новый matcher на `/_next/image`.

---

### `app/catalog/[secret]/layout.tsx` (MODIFY — встроить `<SyncButton />` в шапку)

**Аналог:** сам файл — `OfflineBar`/`SettingsButton`/`CartIcon` уже встроены (паттерн client-острова в server-layout).

**Серверный layout** (`layout.tsx:13`, `async function`) — кнопка добавляется как готовый клиентский компонент в правый блок шапки рядом с настройками/корзиной (строки 33-36):
```tsx
<div className="flex items-center gap-1 shrink-0">
  <SyncButton />        {/* НОВОЕ: кнопка ↻ (D-01) — слева от шестерёнки */}
  <SettingsButton />
  <CartIcon secret={params.secret} />
</div>
```
Импорт — рядом с остальными (`layout.tsx:1-9`). Если выбран контекст-провайдер (см. useCatalogSync выше) — обернуть им шапку+`<main>`, по образцу `CatalogSettingsProvider`/`NavProvider` (строки 26-27, 52-53).

---

### `components/ProductCard.tsx` (INSPECT — заглушка D-06; возможно MODIFY под выбранный подход)

**Заглушка «нет фото» (D-06) — ПЕРЕИСПОЛЬЗОВАТЬ, не создавать новую.** Готовый компонент `PhotoPlaceholder` (`ProductCard.tsx:52-70`): SVG-иконка картинки, `text-gray-300`, центрирована на белом фоне. Уже рендерится когда `!product.imageUrl` (строки 138-147 сетка, 283-293 список). Для D-06 (фото не закэшировано офлайн) показывать ТУ ЖЕ иконку — без особых пометок.

> Примечание: `next/image` при сетевой ошибке (офлайн, фото не в кэше) сам по себе НЕ переключается на `PhotoPlaceholder` (он рендерит `<img>`, который покажет «битое фото»). Если D-06 требует именно иконку-заглушку при незакэшированном фото офлайн — нужен `onError`-фолбэк на `PhotoPlaceholder` ЛИБО переход на raw `<img>` (подход 1). Планировщику учесть: при подходе 1 проще всего навесить `onError`. Это связано с выбором подхода из критической находки.

**Рендер фото** (`ProductCard.tsx:139-144` сетка, 284-290 список) — точка изменения, если выбран подход 1 (`unoptimized`/raw `<img>`) или 2 (custom loader).

---

### `components/Lightbox.tsx` (INSPECT — IMG-02, путь URL подтверждён)

**Аналог:** сам файл.
- `getHiResUrl` (`Lightbox.tsx:26-28`): `url.replace("/upload/", "/upload/f_auto,q_auto,w_1600/")` → результат остаётся `https://res.cloudinary.com/...` → **текущий matcher SW ловит, кэш CacheFirst работает офлайн** (IMG-02 выполним без правок рендера лайтбокса).
- Рендер — сырой `<img src={getHiResUrl(...)}>` (строки 193-200), НЕ `next/image` → НЕ идёт через Optimizer. Это и хорошо (matcher ловит), и важно для diff: **hi-res URL лайтбокса ≠ URL карточки** → две записи кэша на товар. Учесть в потолке 450 (D-05) и при prefetch: prefetch сырого `product.imageUrl` закэширует ОРИГИНАЛ, а лайтбокс запросит `.../w_1600/...` — снова разные записи. Чтобы офлайн-лайтбокс работал по prefetch, prefetch должен бить по `getHiResUrl(url)`, а не по сырому url (либо просто полагаться на ленивое кэширование при онлайн-просмотре до ухода в офлайн — что соответствует критерию приёмки: «просмотреть 5-10 → авиарежим → открыть те же»).

---

## Shared Patterns

### Состояние сети
**Source:** `lib/useOnlineStatus.ts:15` (`useOnlineStatus(): boolean`)
**Apply to:** `SyncButton` (disabled офлайн, D-03). Не дублировать `navigator.onLine` — использовать готовый хук (он уже SSR-safe и слушает события).

### Молчаливая обработка ошибок офлайн-слоя
**Source:** `lib/useCatalogSync.ts:161-170` (catch → `console.warn`, UI не ломаем)
**Apply to:** prefetch фото в `syncPhotos`, любой `fetch` нового URL — `.catch(() => {})`. Дух D-04 этапа 11: сбой сети = «как офлайн», без ошибок в UI.

### Доступ к IndexedDB только через `catalogDb`
**Source:** `lib/catalogDb.ts:95-107` (`getMeta`/`saveMeta`)
**Apply to:** чтение/запись `prevImageUrls` — ТОЛЬКО через эти функции (единственная точка доступа к IDB, комментарий `catalogDb.ts:1-2`). Ключ `prevImageUrls` уже зарезервирован.

### Client-остров в server-layout
**Source:** `app/catalog/[secret]/layout.tsx:9,41` (`OfflineBar`), `SettingsButton`/`CartIcon` в шапке
**Apply to:** `SyncButton` — `"use client"` компонент, встраивается в серверный layout как готовый JSX-узел.

### Стиль кнопки в синей шапке
**Source:** `components/SettingsButton.tsx:9-37`
**Apply to:** `SyncButton` — `h-9 w-9 rounded-full`, белая SVG `w-6 h-6 text-white`, hover `bg-white/15`, активное состояние `bg-white/30`.

---

## No Analog Found

Нет файлов без аналога — все паттерны этапа имеют прямой прецедент в кодовой базе (этапы 10-12 заложили SW, IDB, хук синхронизации, client-острова и стиль кнопок шапки). Этап 13 в основном «оживляет» готовый каркас.

---

## Metadata

**Analog search scope:** `lib/`, `components/`, `app/`, `app/sw.ts`, `next.config.mjs`
**Files scanned:** useCatalogSync.ts, catalogDb.ts, OfflineBar.tsx, sw.ts, ProductCard.tsx, Lightbox.tsx, next.config.mjs, layout.tsx, SettingsButton.tsx, CartIcon.tsx, useOnlineStatus.ts, CatalogView.tsx, types.ts + grep `unoptimized|loader|_next/image`
**Pattern extraction date:** 2026-06-13
