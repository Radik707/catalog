import type { Metadata } from "next";
import "./globals.css";
import { CartProvider } from "@/components/CartProvider";
import CartIcon from "@/components/CartIcon";

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
        <CartProvider>
          <header className="sticky top-0 z-50 bg-blue-600 shadow-sm">
            <div className="flex items-center justify-between px-4 h-12">
              <a href="/" className="text-white font-semibold text-base">
                Каталог
              </a>
              <CartIcon />
            </div>
          </header>
          <main>{children}</main>
        </CartProvider>
      </body>
    </html>
  );
}
