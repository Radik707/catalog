# Phase 12: Офлайн-UX (индикаторы и корзина) — Pattern Map

**Mapped:** 2026-06-12
**Files analyzed:** 6 (3 новых + 3 модификации)
**Analogs found:** 6 / 6

---

## File Classification

| Новый / изменяемый файл | Роль | Data Flow | Ближайший аналог | Качество совпадения |
|-------------------------|------|-----------|-------------------|---------------------|
| `lib/useOnlineStatus.ts` | hook | event-driven | `lib/useCatalogSync.ts` | exact (те же события online/offline + SSR-guard) |
| `lib/formatSyncTime.ts` | utility | transform | `lib/nav.ts` | role-match (чистая функция, нет внешних зависимостей) |
| `components/OfflineBar.tsx` | component | event-driven | `components/ScrollToTop.tsx` + `components/CartIcon.tsx` | exact ("use client", Tailwind, useEffect) |
| `app/catalog/[secret]/layout.tsx` | layout | request-response | сам файл (модификация) | — |
| `app/catalog/[secret]/cart/page.tsx` | page/component | request-response | сам файл (модификация) | — |
| `components/TelegramButton.tsx` | component | request-response | сам файл (модификация) | — |

---

## Pattern Assignments

### `lib/useOnlineStatus.ts` (hook, event-driven)

**Аналог:** `lib/useCatalogSync.ts`

**Что копировать:** структуру "use client" хука, SSR-guard для `navigator`, регистрацию/снятие слушателей `online`/`offline` в `useEffect`, инициализацию `useState(true)` на сервере с исправлением в `useEffect`.

**Imports pattern** (строки 1, 10):
```typescript
"use client";

import { useState, useEffect } from "react";
```

**SSR-guard + начальное значение** (строки 47–52 в useCatalogSync.ts):
```typescript
// Инициализируем isOnline безопасно: на сервере navigator недоступен,
// поэтому начальное значение всегда true — на клиенте исправится в useEffect.
const [isOnline, setIsOnline] = useState<boolean>(true);
```

**Исправление значения в useEffect + слушатели событий** (строки 185–214 в useCatalogSync.ts):
```typescript
useEffect(() => {
  // Исправляем начальное значение isOnline — читаем настоящее состояние на клиенте
  if (typeof navigator !== "undefined") {
    setIsOnline(navigator.onLine);
  }

  const handleOnline = () => setIsOnline(true);
  const handleOffline = () => setIsOnline(false);

  window.addEventListener("online", handleOnline);
  window.addEventListener("offline", handleOffline);

  return () => {
    window.removeEventListener("online", handleOnline);
    window.removeEventListener("offline", handleOffline);
  };
}, []);
```

**Ключевые правила:**
- `useState(true)` — начальное значение на сервере (SSR-safe)
- `typeof navigator !== "undefined"` проверка ТОЛЬКО внутри `useEffect`, никогда на верхнем уровне модуля
- `useOnlineStatus` не дублирует `useCatalogSync` — это тонкая обёртка только для `navigator.onLine`; компоненты кнопок подключают этот хук напрямую, не поднимая весь `useCatalogSync`

---

### `lib/formatSyncTime.ts` (utility, transform)

**Аналог:** `lib/nav.ts`

**Что копировать:** структуру модуля — именованные экспортируемые функции, без `"use client"`, без внешних зависимостей, с комментариями на русском.

**Структура модуля** (строки 1–4 в nav.ts):
```typescript
import { Product } from "./types";

// Иконка для каждого раздела (emoji — без внешних библиотек иконок).
export const SECTION_ICONS: Record<string, string> = { ... };
```

**Паттерн чистой функции-утилиты** (строки 32–60 в nav.ts):
```typescript
// Построить данные навигации из товаров: ... (описание на русском)
export function buildNavData(products: Product[]): SectionNav[] {
  // ... чистая логика без side-effects
}
```

**Для `formatSyncTime` нужно реализовать** (логика по решению D-04 из CONTEXT.md):
- аргумент: `syncedAt: number | null` (unix-ms)
- результат: `string` — «данные за 08:30» / «данные за вчера, 08:30» / «данные за 10 июня, 08:30» / «данные не загружены» (когда null)
- Использовать только нативный `Date`, никакого dayjs/moment
- Порог «сегодня»: та же calendar-дата (не 24 ч скользящим окном)
- Порог «вчера»: вчерашняя calendar-дата
- Остальное: «10 июня, 08:30» (без года — текущий подразумевается)

---

### `components/OfflineBar.tsx` (component, event-driven)

**Аналоги:**
- `components/ScrollToTop.tsx` — паттерн "use client" + `useEffect` для событий браузера + условный рендер
- `components/CartIcon.tsx` — "use client" компонент в шапке, Tailwind-классы на `bg-`, `text-`

**Imports pattern** (строки 1–3 в ScrollToTop.tsx):
```typescript
"use client";

import { useState, useEffect, useRef } from "react";
```

**Условный рендер (показывать/скрывать)** (строки 44–73 в ScrollToTop.tsx):
```typescript
// Компонент возвращает null когда не нужен,
// или JSX с нужными Tailwind-классами.
if (!visible) return null;
return (
  <div className="...tailwind-классы...">
    ...
  </div>
);
```

**Tailwind-цвета в шапке** (строки 28–36 в layout.tsx):
```typescript
// Синяя шапка использует bg-blue-600.
// Полоска под ней — отдельный DOM-узел, НЕ внутри <header>.
// Нейтральный офлайн → bg-gray-100 text-gray-600 (или bg-gray-50)
// Устаревшие данные → bg-yellow-50 text-yellow-800
<header className="sticky top-0 z-50 bg-blue-600 shadow-sm">
  ...
</header>
// сразу после </header> вставляем <OfflineBar />
```

**Правила позиционирования** (из решения D-02 в CONTEXT.md):
- `sticky` под шапкой (НЕ `fixed`) — прокручивается вместе со страницей
- `z-40` (ниже шапки z-50)
- `w-full`, высота ~24px, текст `text-xs`
- `max-w-screen-2xl mx-auto` внутри — в тон контейнеру шапки

**Данные для компонента:** `OfflineBar` читает `syncedAt` напрямую из IDB через `getMeta("syncTimestamp")` из `lib/catalogDb.ts` (не запускает полный `useCatalogSync`), статус сети — через `useOnlineStatus()`.

Логика отображения (решение D-01):
- онлайн + данные свежие (< 24 ч) → `return null` (полоска скрыта)
- офлайн → серая полоска «Офлайн • {formatSyncTime(syncedAt)}»
- данные старше 24 ч (онлайн ИЛИ офлайн) → жёлтая полоска с тем же текстом

---

### `app/catalog/[secret]/layout.tsx` (модификация)

**Что менять:** вставить `<OfflineBar />` сразу после закрывающего `</header>`.

**Текущая структура вставки** (строки 38–46 в layout.tsx):
```typescript
        </header>

        {/* Полоса подгрупп выбранного раздела — выезжает под шапкой */}
        <SubgroupFlyout navData={navData} />
```

**После правки станет:**
```typescript
        </header>

        {/* Индикатор офлайн-режима и свежести данных — клиентский «остров» */}
        <OfflineBar />

        {/* Полоса подгрупп выбранного раздела — выезжает под шапкой */}
        <SubgroupFlyout navData={navData} />
```

**Правило:** `layout.tsx` — серверный компонент (`async`). `OfflineBar` — клиентский. Next.js App Router автоматически делает клиентский компонент «островом» при вставке в серверный layout — никакого дополнительного `"use client"` в layout.tsx не нужно. Паттерн уже используется: `CartIcon`, `CatalogNav`, `TelegramButton` — все клиентские компоненты вставлены в серверный layout без проблем.

---

### `app/catalog/[secret]/cart/page.tsx` — локальная функция `TelegramButton` (модификация)

**Что менять:** локальная функция `TelegramButton` (~строка 139) должна читать `useOnlineStatus()` и при `isOnline === false` рендерить кнопку `disabled` + подпись под ней.

**Текущий паттерн кнопки** (строки 139–166 в cart/page.tsx):
```typescript
function TelegramButton() {
  const { items, totalPrice } = useCartContext();

  const handleSend = () => {
    const url = `https://t.me/${TELEGRAM_USERNAME}?text=${encodeURIComponent(text)}`;
    window.open(url, "_blank");
  };

  return (
    <button
      onClick={handleSend}
      className="w-full py-3.5 bg-blue-600 text-white font-semibold rounded-xl text-base active:bg-blue-700"
    >
      Отправить заказ в Telegram
    </button>
  );
}
```

**Паттерн `disabled` кнопки** — уже применён в той же странице (строки 100–104):
```typescript
<button
  onClick={() => updateQuantity(product.id, quantity + 1)}
  disabled={quantity >= product.stock}
  className="w-7 h-7 rounded-lg bg-gray-100 text-gray-700 font-bold text-base flex items-center justify-center active:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed"
>
```

**Паттерн для офлайн-кнопки (решение D-05):**
```typescript
function TelegramButton() {
  const { items, totalPrice } = useCartContext();
  const isOnline = useOnlineStatus();
  // ... handleSend без изменений ...

  return (
    <div className="flex flex-col gap-2">
      <button
        onClick={handleSend}
        disabled={!isOnline}
        className="w-full py-3.5 bg-blue-600 text-white font-semibold rounded-xl text-base active:bg-blue-700 disabled:bg-gray-300 disabled:text-gray-500 disabled:cursor-not-allowed"
      >
        Отправить заказ в Telegram
      </button>
      {!isOnline && (
        <p className="text-xs text-gray-500 text-center leading-snug">
          Нет сети — заказ отправится, когда появится интернет. Корзина сохранена.
        </p>
      )}
    </div>
  );
}
```

---

### `components/TelegramButton.tsx` (модификация — плавающая кнопка)

**Текущий паттерн** (строки 1–52 в TelegramButton.tsx):
```typescript
"use client";

import { useEffect, useState } from "react";

const BOT_USERNAME = process.env.NEXT_PUBLIC_BOT_USERNAME;

export default function TelegramButton() {
  const [pulse, setPulse] = useState(false);
  // ...
  if (!BOT_USERNAME) return null;

  function handleClick(e: React.MouseEvent) { ... }

  return (
    <button
      onClick={handleClick}
      className={`fixed bottom-6 right-4 z-50 ... ${pulse ? "animate-pulse" : ""}`}
    >
      ...
    </button>
  );
}
```

**Что добавить:** хук `useOnlineStatus()` и атрибут `disabled` + визуальное приглушение при офлайн. Плавающая кнопка при офлайн — `disabled`, `opacity-50`, `cursor-not-allowed`. Подпись (tooltip) — `title` атрибут (не всплывающий блок, т.к. кнопка floating и место ограничено).

**Паттерн изменения** (добавляется к существующему):
```typescript
import { useOnlineStatus } from "@/lib/useOnlineStatus";

export default function TelegramButton() {
  const [pulse, setPulse] = useState(false);
  const isOnline = useOnlineStatus();
  // ... useEffect без изменений ...

  if (!BOT_USERNAME) return null;

  return (
    <button
      onClick={isOnline ? handleClick : undefined}
      disabled={!isOnline}
      title={!isOnline ? "Нет сети — откройте Telegram при подключении" : "Открыть Telegram-помощника"}
      className={`fixed bottom-6 right-4 z-50 flex items-center justify-center w-14 h-14 rounded-full shadow-lg bg-[#0088cc] text-white transition-transform
        ${isOnline ? "hover:scale-110 active:scale-95" : "opacity-50 cursor-not-allowed"}
        ${pulse && isOnline ? "animate-pulse" : ""}`}
      aria-label={isOnline ? "Открыть Telegram-помощника" : "Нет сети"}
    >
      ...
    </button>
  );
}
```

---

## Shared Patterns

### SSR-guard для navigator / window
**Источник:** `lib/useCatalogSync.ts` строки 47–51 и 103–106
**Применять к:** `lib/useOnlineStatus.ts`, `components/OfflineBar.tsx`
```typescript
// useState(true) — начальное значение безопасно для SSR
const [isOnline, setIsOnline] = useState<boolean>(true);

// В useEffect — можно читать navigator
useEffect(() => {
  if (typeof navigator !== "undefined") {
    setIsOnline(navigator.onLine);
  }
  // ...
}, []);
```

### localStorage SSR-guard
**Источник:** `lib/useCart.ts` строки 15–18
**Применять к:** любому новому коду, читающему localStorage
```typescript
function loadCart(): CartItem[] {
  if (typeof window === "undefined") return [];
  // ...
}
```

### Tailwind disabled-кнопка
**Источник:** `app/catalog/[secret]/cart/page.tsx` строки 100–104
**Применять к:** обеим кнопкам отправки заказа
```typescript
className="... disabled:opacity-40 disabled:cursor-not-allowed"
// или для primary-кнопки:
className="... disabled:bg-gray-300 disabled:text-gray-500 disabled:cursor-not-allowed"
```

### Комментарии на русском языке
**Источник:** все файлы `lib/` и `components/`
**Правило:** все комментарии в новых файлах — на русском (требование CLAUDE.md)

---

## No Analog Found

Файлов без аналогов нет. Все 6 файлов покрыты существующими паттернами.

---

## Metadata

**Analog search scope:** `lib/`, `components/`, `app/catalog/[secret]/`
**Files scanned:** 8 (useCatalogSync.ts, useCart.ts, ScrollToTop.tsx, TelegramButton.tsx, CartIcon.tsx, nav.ts, layout.tsx, cart/page.tsx)
**Pattern extraction date:** 2026-06-12
