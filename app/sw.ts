// Файл service worker для @serwist/next.
// Компилируется отдельно webpack-плагином @serwist/next в public/sw.js.
// ВАЖНО: здесь нельзя импортировать серверный код Next.js (next/server, @/lib/sheets и т.д.)

import { defaultCache } from "@serwist/next/worker";
import type { PrecacheEntry, SerwistGlobalConfig } from "serwist";
import {
  CacheFirst,
  ExpirationPlugin,
  NetworkFirst,
  Serwist,
} from "serwist";

// TypeScript: расширяем globalThis для SW-окружения (webpack-плагин инжектит __SW_MANIFEST)
declare global {
  interface ServiceWorkerGlobalScope extends SerwistGlobalConfig {
    __SW_MANIFEST: (PrecacheEntry | string)[] | undefined;
  }
}

declare const self: ServiceWorkerGlobalScope;

// Инициализация Serwist с precache app-shell и каркасом runtime-стратегий
const serwist = new Serwist({
  // Precache app-shell (JS/CSS/HTML-шелл) — генерируется @serwist/next при сборке.
  // НЕ должен содержать ~900 фото Cloudinary — это anti-pattern, нарушит iOS-квоту ~50 МБ.
  precacheEntries: self.__SW_MANIFEST,

  // D-12: skipWaiting: false — обновление SW только по явному согласию агента.
  // Форсированный skipWaiting при активной вкладке → ChunkLoadError / белый экран.
  skipWaiting: false,

  // Захватить все открытые клиенты после активации SW
  clientsClaim: true,

  // Navigation Preload — ускоряет переходы между страницами под SW
  navigationPreload: true,

  // Список стратегий кэширования: базовый defaultCache + кастомные (D-16)
  runtimeCaching: [
    // Стратегия NetworkFirst для API товаров:
    // при наличии сети — всегда свежие данные; при офлайн — кэш.
    // Timeout 5 с, чтобы не ждать при плохой сети.
    // Офлайн-эффект проверяется на этапе 11 (IndexedDB).
    // ВАЖНО: без якоря ^ — Serwist прогоняет regex по ПОЛНОМУ адресу (url.href,
    // т.е. https://домен/api/products), а не по пути. С ^ совпадения не будет
    // никогда (href начинается с https://, а не с /api). НЕ возвращать ^.
    {
      matcher: /\/api\/products/,
      handler: new NetworkFirst({
        networkTimeoutSeconds: 5,
        cacheName: "api-products",
      }),
    },

    // Стратегия CacheFirst для фото Cloudinary:
    // раз загружено — берём из кэша; обновление только если файл отсутствует.
    // maxEntries: 450 — защита от переполнения iOS-квоты ~50 МБ (критическая ловушка).
    // maxAgeSeconds: 7 дней — автоудаление устаревших фото.
    // Офлайн-эффект и iOS-квота проверяются на этапе 13 (Синхронизация фото).
    {
      matcher: /^https:\/\/res\.cloudinary\.com\//,
      handler: new CacheFirst({
        cacheName: "cloudinary-images",
        plugins: [
          new ExpirationPlugin({
            maxEntries: 450,
            maxAgeSeconds: 7 * 24 * 60 * 60, // 7 дней в секундах
          }),
        ],
      }),
    },

    // Базовые стратегии из defaultCache — кэш статики Next.js (JS, CSS, шрифты)
    ...defaultCache,
  ],
});

// Регистрируем все обработчики событий (install, activate, fetch и т.д.)
serwist.addEventListeners();
