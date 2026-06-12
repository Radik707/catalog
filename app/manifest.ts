// Web App Manifest для PWA «Каталог Вкусный Дом».
// Next.js 14 встроенный механизм (D-15) — Content-Type: application/manifest+json
// отдаётся автоматически по /manifest.webmanifest.

import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    // Полное имя приложения (D-01)
    name: "Каталог Вкусный Дом",

    // Короткое имя под иконкой на домашнем экране (D-02)
    short_name: "Вкусный Дом",

    // Стартовый URL — секретная ссылка каталога (D-09).
    // Секрет берётся из переменной окружения, НЕ хардкодится.
    start_url: `/catalog/${process.env.CATALOG_SECRET ?? ""}`,

    // Режим отображения без адресной строки браузера (D-08)
    display: "standalone",

    // Ориентация экрана — агент работает с телефоном вертикально (D-10)
    orientation: "portrait",

    // Цвет полоски статуса в standalone-режиме (D-06) — фирменный синий #2563eb
    theme_color: "#2563eb",

    // Фон splash-заставки при запуске (D-07) — белый, как карточки каталога
    background_color: "#ffffff",

    // Иконки приложения (D-04):
    // - purpose "any" — обычное использование
    // - purpose "maskable" — Android adaptive icons с safe-zone ~80%
    icons: [
      {
        src: "/icons/icon-192x192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/icon-512x512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/icon-512x512-maskable.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
