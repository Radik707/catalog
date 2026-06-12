import type { Metadata, Viewport } from "next";
import "./globals.css";
import { CartProvider } from "@/components/CartProvider";

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
