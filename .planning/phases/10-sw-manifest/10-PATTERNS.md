# Phase 10: Фундамент SW и Manifest — Pattern Map

**Mapped:** 2026-06-12
**Files analyzed:** 6 (новых/изменяемых файлов этапа)
**Analogs found:** 4 / 6 (2 файла — без аналога в кодовой базе)

---

## File Classification

| Новый / изменяемый файл | Роль | Data Flow | Ближайший аналог | Качество совпадения |
|---|---|---|---|---|
| `next.config.mjs` | config | request-response | `next.config.mjs` (сам файл — расширяется) | exact |
| `app/manifest.ts` | config | request-response | `app/api/products/route.ts` | role-match (серверный модуль-экспорт) |
| `app/sw.ts` | service | event-driven | **нет аналога** — только Serwist docs | none |
| `app/layout.tsx` | component | request-response | `app/layout.tsx` (сам файл — расширяется) | exact |
| `public/` иконки | config | — | **нет аналога** — статические ассеты | none |
| `.gitignore` | config | — | `.gitignore` (сам файл — дополняется) | exact |

---

## Pattern Assignments

### `next.config.mjs` (config, расширение)

**Аналог:** сам файл `next.config.mjs` — оборачивается в `withSerwist`.

**Текущий файл** (строки 1–13):
```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "res.cloudinary.com",
      },
    ],
  },
};

export default nextConfig;
```

**Паттерн после изменений — обёртка withSerwist + заголовки:**

Файл переходит с `export default nextConfig` на двухэтапную обёртку:
1. Импортируем `withSerwist` из `@serwist/next`.
2. Создаём конфиг Serwist с обязательными полями (D-13 `disable:dev`, D-12 `skipWaiting:false`).
3. Добавляем `async headers()` с двумя правилами для `/sw.js` (D-14): `Cache-Control: max-age=0, must-revalidate` и `Service-Worker-Allowed: /`.
4. `withSerwist(serwistConfig)(nextConfig)` — экспортируем результат.

Ключевые точки:
- Блок `images.remotePatterns` (строки 3–9) сохраняется без изменений.
- Добавляется `swSrc: "app/sw.ts"` — путь к SW-файлу.
- `disable: process.env.NODE_ENV === "development"` — обязательно (критическая ловушка #5).

---

### `app/manifest.ts` (config, request-response)

**Аналог:** `app/api/products/route.ts` — серверный модуль Next.js, который экспортирует функцию, возвращающую данные с автоматическим Content-Type.

**Паттерн аналога** `app/api/products/route.ts` (строки 1–10):
```ts
import { NextResponse } from "next/server";
import { getProducts } from "@/lib/sheets";

export const dynamic = 'force-dynamic';

export async function GET() {
  const products = await getProducts();
  return NextResponse.json(products);
}
```

**Паттерн для `app/manifest.ts`** — Next.js built-in manifest (НЕ Route Handler, а специальный модуль):
```ts
// Возвращает объект — Next.js сам выставит Content-Type: application/manifest+json
import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return { ... };
}
```

**Критические поля (из решений D-01…D-10):**
- `name`: `"Каталог Вкусный Дом"` (D-01)
- `short_name`: `"Вкусный Дом"` (D-02)
- `theme_color`: `"#2563eb"` (D-06, совпадает с `bg-blue-600` в `app/catalog/[secret]/layout.tsx:28`)
- `background_color`: `"#ffffff"` (D-07)
- `display`: `"standalone"` (D-08)
- `start_url`: берётся из `process.env.CATALOG_SECRET` — паттерн как в `app/catalog/[secret]/page.tsx:18`
- `orientation`: `"portrait"` (D-10)

**Паттерн чтения env-переменной** (аналог из `app/catalog/[secret]/page.tsx`, строки 17–19):
```ts
// Проверка секретной ссылки — не прошёл, показываем 404
if (params.secret !== process.env.CATALOG_SECRET) {
  notFound();
}
```
Для `manifest.ts` — читаем без проверки: `` `/catalog/${process.env.CATALOG_SECRET}` ``.

---

### `app/sw.ts` (service, event-driven)

**Аналога в кодовой базе нет.** Ни одного event-driven сервиса (SW, воркер, event listener) в проекте не существует.

**Источник паттернов:** Serwist официальная документация — https://serwist.pages.dev/docs/next/getting-started

**Скелет файла из документации:**
```ts
import { defaultCache } from "@serwist/next/worker";
import type { PrecacheEntry, SerwistGlobalConfig } from "serwist";
import { Serwist } from "serwist";

// TypeScript: объявляем globalThis для SW-окружения
declare const self: ServiceWorkerGlobalScope & {
  __SW_MANIFEST: (PrecacheEntry | string)[] | undefined;
};

const serwist = new Serwist({
  precacheEntries: self.__SW_MANIFEST,
  skipWaiting: false,           // D-12: НЕ форсировать — иначе ChunkLoadError
  clientsClaim: true,
  navigationPreload: true,
  runtimeCaching: defaultCache, // базовый кэш app-shell
});

serwist.addEventListeners();
```

**Кастомные стратегии кэширования (добавляются к `defaultCache` — D-16):**
```ts
import { NetworkFirst, CacheFirst, ExpirationPlugin } from "serwist";

// NetworkFirst для API товаров: свежие данные при сети, кэш при офлайн
{
  matcher: /^\/api\/products/,
  handler: new NetworkFirst({
    networkTimeoutSeconds: 5,
    cacheName: "api-products",
  }),
}

// CacheFirst для Cloudinary фото: лимит на количество (iOS квота ~50 МБ)
{
  matcher: /^https:\/\/res\.cloudinary\.com\//,
  handler: new CacheFirst({
    cacheName: "cloudinary-images",
    plugins: [
      new ExpirationPlugin({
        maxEntries: 450,    // не превышать iOS-лимит ~50 МБ (критическая ловушка #1)
        maxAgeSeconds: 7 * 24 * 60 * 60, // 7 дней
      }),
    ],
  }),
}
```

**Важно:** `app/sw.ts` — это РАБОЧИЙ ФАЙЛ SERVICE WORKER, НЕ серверный код Next.js. Он компилируется отдельно webpack-плагином `@serwist/next` и выгружается как `public/sw.js`. Серверные импорты (`next/server`, `@/lib/sheets`) здесь недопустимы.

---

### `app/layout.tsx` (component, расширение)

**Аналог:** сам файл `app/layout.tsx` — дополняется PWA-метаданными.

**Текущий файл** (строки 1–23):
```tsx
import type { Metadata } from "next";
import "./globals.css";
import { CartProvider } from "@/components/CartProvider";

export const metadata: Metadata = {
  title: "Каталог товаров",
  description: "B2B-каталог товаров для владельцев магазинов",
  robots: "noindex, nofollow",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <body className="bg-gray-50 antialiased">
        <CartProvider>{children}</CartProvider>
      </body>
    </html>
  );
}
```

**Паттерн расширения `metadata`** — добавляются поля для PWA и iOS:
```tsx
export const metadata: Metadata = {
  title: "Каталог товаров",
  description: "B2B-каталог товаров для владельцев магазинов",
  robots: "noindex, nofollow",
  // PWA-метаданные для iOS (Android получает из manifest.ts)
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Вкусный Дом",         // D-02: short_name
  },
};
```

**Паттерн добавления `<link>` иконок в `<head>`** — через Next.js `icons` в `metadata` (предпочтительно) или через явные теги в JSX. Next.js 14 App Router поддерживает `metadata.icons`:
```tsx
export const metadata: Metadata = {
  // ...
  icons: {
    icon: [
      { url: "/icons/icon-192x192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512x512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [
      { url: "/icons/apple-touch-icon.png", sizes: "180x180" },
    ],
  },
};
```

**Паттерн theme-color** из `app/catalog/[secret]/layout.tsx:28` (`bg-blue-600` = `#2563eb`):
```tsx
// В metadata или через тег:
<meta name="theme-color" content="#2563eb" />
```

---

### `public/` иконки (статические ассеты)

**Аналога нет.** Папка `public/` не существует (подтверждено Glob). Иконок/логотипа в проекте нет.

**Источник:** иконки генерируются вручную или скриптом. Параметры из решений D-03…D-05:
- `public/icons/icon-192x192.png` — синий квадрат `#2563eb`, белые буквы «ВД», 192×192 px
- `public/icons/icon-512x512.png` — то же, 512×512 px
- `public/icons/icon-512x512-maskable.png` — с safe-zone ~80% для Android adaptive icons
- `public/icons/apple-touch-icon.png` — 180×180 px, без прозрачности, фон синий `#2563eb`

**Правило именования:** файлы кладутся в `public/icons/` (подпапка, не в корень `public/`), чтобы не смешиваться с генерируемыми `sw.js` / `swe-worker*.js`.

---

### `.gitignore` (config, дополнение)

**Аналог:** сам файл `.gitignore` — дополняется двумя строками.

**Текущий файл** (строки 1–42) показывает стиль: блоки с комментариями `# раздел`.

**Паттерн добавления** — новый блок в конце файла в том же стиле:
```gitignore
# PWA: сгенерированные service worker файлы (собираются из app/sw.ts при build)
public/sw.js
public/swe-worker*.js
```

---

## Shared Patterns

### Чтение переменных окружения на сервере
**Источник:** `app/catalog/[secret]/page.tsx` (строки 17–19), `lib/sheets.ts` (строки 4–5)
**Применить к:** `app/manifest.ts` для формирования `start_url`
```ts
// Паттерн из lib/sheets.ts (строки 4–5):
const SHEETS_ID = process.env.GOOGLE_SHEETS_ID;
const API_KEY = process.env.GOOGLE_API_KEY;

// Паттерн из page.tsx (строка 18):
process.env.CATALOG_SECRET
// В manifest.ts: `/catalog/${process.env.CATALOG_SECRET ?? ""}`
```

### Фирменный синий цвет `#2563eb`
**Источник:** `app/catalog/[secret]/layout.tsx` (строка 28), класс `bg-blue-600`
**Применить к:** `app/manifest.ts` (`theme_color`), иконкам (`background`), `app/layout.tsx` (`theme-color` meta)
```tsx
// layout.tsx:28
<header className="sticky top-0 z-50 bg-blue-600 shadow-sm">
// bg-blue-600 = #2563eb
```

### Стиль комментариев в коде
**Источник:** все файлы проекта — комментарии на русском языке (CLAUDE.md)
**Применить к:** всем новым файлам (`app/sw.ts`, `app/manifest.ts`, изменениям в `next.config.mjs`)

Пример из `app/api/products/route.ts` (строка 5–6):
```ts
export const dynamic = 'force-dynamic';
// Без ISR-кэша: ответ всегда отражает актуальный лист «Товары»
```

### ES-модули в конфигурации Next.js
**Источник:** `next.config.mjs` (строки 1, 13) — файл `.mjs`, синтаксис `import`/`export`
**Применить к:** `next.config.mjs` после добавления `withSerwist`
```js
// Используем import/export, НЕ require/module.exports
import withSerwist from "@serwist/next";
// ...
export default withSerwist(serwistConfig)(nextConfig);
```

### TypeScript-типизация
**Источник:** все `.tsx`/`.ts` файлы — строгая типизация, `import type` где возможно
**Применить к:** `app/sw.ts`, `app/manifest.ts`
```ts
// Из app/layout.tsx строка 1:
import type { Metadata } from "next";
// В manifest.ts аналогично:
import type { MetadataRoute } from "next";
```

---

## No Analog Found

| Файл | Роль | Data Flow | Причина |
|---|---|---|---|
| `app/sw.ts` | service | event-driven | Service Worker — принципиально иная среда выполнения (SW global scope, не Node.js/браузер). В проекте нет ни одного воркера или event-driven сервиса. Паттерн — Serwist docs. |
| `public/` иконки | static asset | — | Папки `public/` не существует. Статических ассетов/иконок/логотипа в проекте нет. Иконки создаются с нуля по параметрам D-03…D-05. |

---

## Metadata

**Область поиска аналогов:** `app/`, `lib/`, `components/`, корень проекта
**Файлов просканировано:** 14 (все `.ts`/`.tsx` + конфиги)
**Дата маппинга:** 2026-06-12
