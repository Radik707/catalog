# Stack Research: PWA / Offline Layer

**Domain:** Offline PWA поверх существующего Next.js 14 (App Router) каталога на Vercel
**Researched:** 2026-06-12
**Confidence:** HIGH (Serwist, манифест, стратегии кэширования), MEDIUM (iOS-квоты, idb)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `@serwist/next` | ^9.0.0 (latest: 9.5.11) | Next.js-интеграция service worker, webpack-плагин, withSerwist-обёртка | Официальный наследник next-pwa и @ducanh2912/next-pwa. Рекомендован в официальной документации Next.js. Поддерживается активно, последний релиз — май 2026 |
| `serwist` (dev) | ^9.0.0 (latest: 9.5.11) | Движок SW в `app/sw.ts`: Serwist-класс, стратегии, плагины экспирации | Основная библиотека, @serwist/next — тонкая обёртка над ней для Next.js. Форк Workbox с активной разработкой |
| `app/manifest.ts` (встроенный Next.js) | Next.js 14+ built-in | Web App Manifest (имя, иконки, display: standalone) | Не нужна внешняя библиотека: `MetadataRoute.Manifest` генерирует корректный `/manifest.json` автоматически через App Router |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `idb` | ^8.0.0 | Promise-обёртка над IndexedDB | Хранение массива Product[] (~900 товаров, ~200 КБ JSON) в IndexedDB на клиенте для полного офлайн-доступа. Cache Storage не подходит для структурированных данных |
| `@serwist/precaching` | ^9.0.0 | Precache runtime-артефактов сборки | Уже тянется как зависимость @serwist/next, отдельно устанавливать не нужно — используется внутри sw.ts |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `realfavicongenerator.net` | Генерация иконок PWA | Создаёт 192×192 и 512×512 PNG + maskable-иконки для `public/`. Один раз, вручную |
| Chrome DevTools → Application → Service Workers | Отладка SW, проверка Cache Storage, симуляция офлайн | Встроено в Chrome/Edge, дополнительных пакетов не нужно |
| `next dev --experimental-https` | Локальная разработка с HTTPS | Service Worker требует HTTPS. Флаг запускает локальный сертификат через mkcert |

---

## Installation

```bash
# Основные зависимости (production + dev)
npm install @serwist/next
npm install -D serwist

# Для хранения товаров в IndexedDB
npm install idb
```

После установки — в `.gitignore` добавить:
```
public/sw.js
public/swe-worker*.js
```

---

## Integration Points с существующим кодом

### 1. next.config.mjs — обернуть withSerwist

```javascript
import withSerwistInit from "@serwist/next";

const withSerwist = withSerwistInit({
  swSrc: "app/sw.ts",        // исходник SW в App Router
  swDest: "public/sw.js",   // куда компилируется
  disable: process.env.NODE_ENV === "development", // SW в разработке мешает
});

export default withSerwist({
  // существующий next.config.mjs без изменений
  images: { remotePatterns: [{ hostname: "res.cloudinary.com" }] },
});
```

### 2. app/manifest.ts — новый файл (встроенный Next.js API)

```typescript
import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Каталог Вкусный Дом",
    short_name: "Каталог",
    start_url: `/catalog/${process.env.CATALOG_SECRET}`,
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#1d4ed8",   // синий из шапки
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
```

### 3. app/sw.ts — service worker с кэш-стратегиями

Ключевые стратегии для этого проекта:

**Данные каталога (`/api/products`):** `NetworkFirst` с `cacheName: "api-cache"`, `networkTimeoutSeconds: 5`. Агент всегда получает свежее при сети; в офлайн — последняя загруженная версия.

**Фото Cloudinary (`res.cloudinary.com`):** `CacheFirst` + `ExpirationPlugin({ maxEntries: 500, maxAgeSeconds: 7 * 24 * 60 * 60 })`. НЕ precache всё разом — фото попадают в кэш по мере просмотра (on-demand). Лимит 500 записей защищает от переполнения квоты.

**Страницы каталога:** precache через `defaultCache` (Serwist делает автоматически).

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| `@serwist/next` | `@ducanh2912/next-pwa` | Устаревший; сам автор рекомендует переходить на Serwist. Последние обновления — 2024 |
| `@serwist/next` | `next-pwa` (оригинальный от shadowwalker) | Не обновлялся с июля 2024. Нет поддержки App Router |
| `@serwist/next` | Ручной SW без библиотеки | Возможно (Next.js docs показывают базовый пример), но теряем Workbox-стратегии, precaching, ExpirationPlugin — придётся писать самостоятельно |
| `idb` | `localforage` | Старый API, не получает обновлений. idb — от Jake Archibald (создатель Workbox), активно поддерживается |
| `idb` | `Dexie.js` | Тяжелее (~45 КБ), много возможностей которые не нужны. idb (~5 КБ) достаточен для одного стора Product[] |
| Cache Storage для фото | IndexedDB для фото | Cache Storage — правильное место для HTTP-ответов (картинки по URL). IndexedDB — для структурированных данных (JSON товаров). Не мешать |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `next-pwa` (оригинальный) | Не обновлялся с 2024, нет поддержки App Router, не работает с Next.js 14+ без хаков | `@serwist/next` |
| Precache всех 900 фото при старте SW | iOS Safari: квота Cache Storage — ~50 МБ. 900 фото Cloudinary (WebP ~30–80 КБ каждое) = до 72 МБ — переполнит квоту и SW завершится с ошибкой | CacheFirst runtime caching: кэшировать по мере просмотра, лимит maxEntries: 500 |
| `capacitor` / `ionic` / `react-native-web` | Задача — PWA, не нативное приложение. Полная смена стека, переписывание компонентов | Остаёмся на Next.js PWA |
| `workbox` напрямую (без Serwist) | Serwist — форк Workbox с активной поддержкой; `workbox` в npm больше не обновляется (последний стабильный — 2023) | `serwist` (через @serwist/next) |
| Background Sync для заказов | Сложность без пользы: корзина в localStorage, заказ — Telegram deep-link. Deep-link не срабатывает в офлайн в любом случае | Показывать «нет сети — скопируй текст заказа» |
| Push Notifications | Не нужны для этой вехи; iOS требует iOS 16.4+ и установки на домашний экран | Отложить на будущие вехи |

---

## iOS Safari: Критические Ограничения

Это самая тонкая часть. Знать обязательно:

| Ограничение | Значение | Следствие для проекта |
|-------------|----------|-----------------------|
| Cache Storage квота | ~50 МБ на origin (Safari на iOS) | 900 фото WebP ~30–80 КБ = потенциально 70+ МБ. Нельзя кэшировать все заранее. Стратегия: CacheFirst on-demand + maxEntries: 400–500 |
| IndexedDB квота | До 500 МБ (если свободного места > 1 ГБ) | Достаточно для JSON товаров (~200 КБ) |
| 7-дневная экспирация | iOS очищает хранилище SW, если PWA не открывалась 7+ дней | Агент должен открывать PWA хотя бы раз в неделю. Документировать в инструкции |
| Установка на домашний экран | iOS: только через Safari → «Поделиться» → «На экран Домой». Браузерного `beforeinstallprompt` нет | В UI показать подсказку для iOS (компонент InstallPrompt — официальный пример Next.js) |
| Очистка при нехватке места | iOS может удалить кэш при заполнении диска | Graceful fallback: если фото нет в кэше — показать placeholder, не ошибку |

**Практическая стратегия для фото:** CacheFirst с `maxEntries: 450` и `maxAgeSeconds: 7 * 24 * 3600`. При прокрутке каталога (все товары видны) закэшируется ~450 последних просмотренных фото. Для полного первичного кэша — кнопка «Загрузить для офлайн», которая фоново запрашивает все URL фото через fetch (браузер добавит в Cache Storage при NetworkFirst/CacheFirst перехвате SW).

---

## Данные из Google Sheets: Офлайн-стратегия

Существующий маршрут данных: `GET /api/products` (force-dynamic) → `lib/sheets.ts` → Google Sheets API → Product[].

**Проблема:** force-dynamic — значит, данные не precache Serwist-ом автоматически.

**Решение: два слоя**

1. **SW NetworkFirst для `/api/products`:** при сети — свежий ответ + кладём в Cache Storage. При офлайн — SW отдаёт кэшированный JSON. Это работает автоматически через Serwist `NetworkFirst`.

2. **IndexedDB через idb (опционально, для надёжности):** клиентский код после успешной загрузки Product[] записывает их в IndexedDB (`catalog-products` store). При загрузке страницы в офлайн: проверить SW cache (через fetch) → если промах → достать из IndexedDB. Двойная страховка.

Для вехи v1.3 достаточен слой 1 (SW NetworkFirst). Слой 2 (idb) добавляет надёжность на iOS, где SW может быть очищен.

---

## Version Compatibility

| Package | Peer Dependency | Notes |
|---------|-----------------|-------|
| `@serwist/next@9.x` | Next.js 14, 15, 16 | Совместим с Next.js ^14.2.0 (текущий в проекте). Webpack-режим (не Turbopack) — требует webpack в проекте (по умолчанию в Next.js 14) |
| `serwist@9.x` | TypeScript ^5.0 | Совместим с TS 5.x (используется в проекте) |
| `idb@8.x` | Нет peer deps | Работает в любом современном браузере (iOS 12+, Android 6+) |

**Важно:** Serwist `@serwist/next` в официальной документации Next.js описан с оговоркой: *"this plugin currently requires webpack configuration"* — Turbopack не поддерживается. Проект на Next.js 14 использует webpack (Turbopack — экспериментальный), проблем нет.

---

## Sources

- `@serwist/next` официальная документация: https://serwist.pages.dev/docs/next/getting-started — HIGH confidence
- Next.js официальный гайд PWA: https://nextjs.org/docs/app/guides/progressive-web-apps — HIGH confidence (версия 16.2.9, обновлено 2026-02-11)
- WebKit Storage Policy Updates: https://webkit.org/blog/14403/updates-to-storage-policy/ — HIGH confidence
- iOS PWA limitations 2026: https://www.magicbell.com/blog/pwa-ios-limitations-safari-support-complete-guide — MEDIUM confidence
- LogRocket Next.js 16 PWA guide: https://blog.logrocket.com/nextjs-16-pwa-offline-support/ — MEDIUM confidence
- npm: `@serwist/next` — версия 9.5.11, последняя публикация май 2026 — HIGH confidence

---

*Stack research for: PWA / Offline Layer — веха v1.3*
*Researched: 2026-06-12*
