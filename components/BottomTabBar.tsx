"use client";

// Нижняя панель вкладок для роли «Клиент».
// Три равные вкладки: Каталог · Избранное · Корзина.
// Монтируется в app/catalog/[secret]/layout.tsx (план 18-02).
// Для роли «Торговый» (sales) компонент НЕ рендерится (гейт D-11).

import { usePathname, useRouter } from "next/navigation";
import { useRole } from "@/lib/useRole";
import { useNav } from "@/components/NavProvider";
import { useCartContext } from "@/components/CartProvider";
import { useFavoritesContext } from "@/components/FavoritesProvider";

// Пропсы компонента: секрет для формирования маршрутов каталога/корзины.
interface BottomTabBarProps {
  secret: string;
}

export default function BottomTabBar({ secret }: BottomTabBarProps) {
  // SSR-safe гейт роли (D-11): до ready ничего не рисуем, чтобы не было
  // мелькания раскладки при гидратации (паттерн HeaderPrimaryAction/CardCornerButton).
  const { role, ready } = useRole();

  // Режим витрины (catalog / hit / new / fav) — для активной вкладки и переключения.
  const { mode, setMode } = useNav();

  // Счётчик корзины: число позиций (D-06, как CartIcon — items.length, НЕ totalItems).
  const { items } = useCartContext();

  // Счётчик избранного: count из FavoritesProvider.
  const { count: favCount } = useFavoritesContext();

  // Текущий путь — для определения активной вкладки «Корзина».
  const pathname = usePathname();
  const router = useRouter();

  // Базовый путь витрины каталога.
  const catalogPath = `/catalog/${secret}`;

  // Гейт: не рендерим до монтирования или если роль не «Клиент» (D-11).
  if (!ready || role !== "client") {
    return null;
  }

  // --- Определение активной вкладки (D-03) ---
  // Корзина активна, если путь оканчивается на '/cart'.
  const isCartActive = pathname.endsWith("/cart");
  // Избранное активно, если не в корзине и режим 'fav'.
  const isFavActive = !isCartActive && mode === "fav";
  // Каталог активен в остальных случаях (catalog / hit / new).
  const isCatalogActive = !isCartActive && !isFavActive;

  // --- Обработчики вкладок (D-02) ---

  // Вкладка «Каталог»: переход на витрину (если нужно) + режим 'catalog'.
  const handleCatalog = () => {
    if (pathname !== catalogPath) {
      router.push(catalogPath);
    }
    setMode("catalog");
  };

  // Вкладка «Избранное»: переход на витрину (если нужно) + режим 'fav'.
  // Аналогичен механизму FavoritesIcon в шапке.
  const handleFav = () => {
    if (pathname !== catalogPath) {
      router.push(catalogPath);
    }
    setMode("fav");
  };

  // Вкладка «Корзина»: переход на страницу корзины.
  const handleCart = () => {
    router.push(`/catalog/${secret}/cart`);
  };

  // --- Стили вкладок (D-03) ---
  // Активная вкладка — text-blue-600 (в тон шапке bg-blue-600), неактивная — text-gray-500.
  const activeClass = "text-blue-600";
  const inactiveClass = "text-gray-500";

  // Счётчик бейджа корзины = items.length (число позиций, не сумма).
  const cartCount = items.length;

  return (
    // Контейнер панели: фиксированный снизу, z-50 (под InstallPrompt z-[60]).
    // safe-area снизу через inline style — надёжнее на Safari (D-08, как InstallPrompt).
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-gray-200"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      aria-label="Нижняя навигация"
    >
      {/* Три равные колонки (D-01, D-05): высота h-16 = 64px, тап-зона вся колонка */}
      <div className="grid grid-cols-3 h-16">

        {/* Вкладка «Каталог» */}
        <button
          onClick={handleCatalog}
          aria-label="Каталог"
          aria-pressed={isCatalogActive}
          className={`flex flex-col items-center justify-center transition-colors ${
            isCatalogActive ? activeClass : inactiveClass
          }`}
        >
          {/* Иконка: сетка (grid) в стиле heroicons */}
          <svg
            className="w-6 h-6"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <rect x="3" y="3" width="7" height="7" />
            <rect x="14" y="3" width="7" height="7" />
            <rect x="14" y="14" width="7" height="7" />
            <rect x="3" y="14" width="7" height="7" />
          </svg>
          <span className="text-xs mt-0.5">Каталог</span>
        </button>

        {/* Вкладка «Избранное» */}
        <button
          onClick={handleFav}
          aria-label="Избранное"
          aria-pressed={isFavActive}
          className={`flex flex-col items-center justify-center transition-colors ${
            isFavActive ? activeClass : inactiveClass
          }`}
        >
          {/* Обёртка иконки: relative для позиционирования бейджа */}
          <span className="relative">
            {/* Иконка сердечко — тот же d-path, что в FavoritesIcon */}
            <svg
              className="w-6 h-6"
              viewBox="0 0 24 24"
              fill={isFavActive ? "currentColor" : "none"}
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" />
            </svg>
            {/* Бейдж избранного: показывать только при count > 0 (D-06) */}
            {favCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
                {favCount > 99 ? "99" : favCount}
              </span>
            )}
          </span>
          <span className="text-xs mt-0.5">Избранное</span>
        </button>

        {/* Вкладка «Корзина» */}
        <button
          onClick={handleCart}
          aria-label="Корзина"
          aria-pressed={isCartActive}
          className={`flex flex-col items-center justify-center transition-colors ${
            isCartActive ? activeClass : inactiveClass
          }`}
        >
          {/* Обёртка иконки: relative для позиционирования бейджа */}
          <span className="relative">
            {/* Иконка корзины — тот же d-path, что в CartIcon */}
            <svg
              className="w-6 h-6"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z" />
            </svg>
            {/* Бейдж корзины: items.length (число позиций, не totalItems) при > 0 (D-06) */}
            {cartCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
                {cartCount > 99 ? "99" : cartCount}
              </span>
            )}
          </span>
          <span className="text-xs mt-0.5">Корзина</span>
        </button>

      </div>
    </nav>
  );
}
