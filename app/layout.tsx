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
