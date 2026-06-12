// Конфигурация Next.js с подключением service worker через @serwist/next
import withSerwist from "@serwist/next";

// Параметры Serwist-плагина для сборки service worker
const serwistConfig = {
  // Путь к исходнику SW — компилируется webpack-плагином @serwist/next
  swSrc: "app/sw.ts",
  // Куда выгружать скомпилированный SW
  swDest: "public/sw.js",
  // D-13: отключаем SW в режиме разработки, чтобы кэш не мешал hot-reload
  disable: process.env.NODE_ENV === "development",
};

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

  // D-14: заголовки для /sw.js — защита от immutable-кэша Vercel.
  // Без этого Vercel «залипает» на старой версии SW после деплоя.
  async headers() {
    return [
      {
        source: "/sw.js",
        headers: [
          {
            key: "Cache-Control",
            // max-age=0 + must-revalidate: браузер всегда проверяет свежесть SW
            value: "max-age=0, must-revalidate",
          },
          {
            key: "Service-Worker-Allowed",
            // Разрешаем SW перехватывать запросы с корня сайта
            value: "/",
          },
        ],
      },
    ];
  },
};

// Оборачиваем конфигурацию Next.js в withSerwist — двухэтапный вызов
export default withSerwist(serwistConfig)(nextConfig);
