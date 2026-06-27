import type { Metadata, Viewport } from "next";
import "./globals.css";
import { CartProvider } from "@/components/CartProvider";
import { FavoritesProvider } from "@/components/FavoritesProvider";
import { OrderHistoryProvider } from "@/components/OrderHistoryProvider";

export const metadata: Metadata = {
  title: "Каталог товаров",
  description: "B2B-каталог товаров для владельцев магазинов",
  robots: "noindex, nofollow",

  // PWA-метаданные для iOS (Android получает из app/manifest.ts)
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    // Короткое имя под иконкой на iOS (D-02)
    title: "Вкусный Дом",
  },

  // Иконки приложения для браузерных <link> тегов
  icons: {
    icon: [
      { url: "/icons/icon-192x192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512x512.png", sizes: "512x512", type: "image/png" },
    ],
    // Иконка для iOS — без прозрачности, iOS скругляет сам (D-04)
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180" }],
  },
};

// theme-color выносится в viewport (Next.js 14: themeColor не в metadata) (D-06)
export const viewport: Viewport = {
  // Фирменный синий #2563eb — совпадает с шапкой каталога bg-blue-600
  themeColor: "#2563eb",
  // viewport-fit=cover активирует env(safe-area-inset-*) для нижней шторки/баннера
  // в standalone-режиме на iPhone с чёлкой — без этого safe-area молча не работает (D-07)
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <body className="bg-gray-50 antialiased">
        <CartProvider>
          <FavoritesProvider>
            {/* Единый экземпляр истории заказов на всё дерево — без гонки кнопок отправки (CR-01) */}
            <OrderHistoryProvider>{children}</OrderHistoryProvider>
          </FavoritesProvider>
        </CartProvider>
      </body>
    </html>
  );
}
