"use client";

// Отдельная кнопка «в избранное» (сердечко) для роли Клиент.
// В режиме «Список» вынесена ЗА пределы миниатюры (рядом с ней), чтобы не
// перекрывать фото — раньше сердечко рисовалось поверх картинки в углу.
//
// До готовности роли (ready) резервируем место того же размера — иначе при
// появлении сердечка строка «дёргается» (тот же приём, что в CardCornerButton).

import { useRole } from "@/lib/useRole";
import { useFavoritesContext } from "@/components/FavoritesProvider";

interface FavoriteButtonProps {
  productId: string;
  className?: string;
}

export default function FavoriteButton({ productId, className = "" }: FavoriteButtonProps) {
  const { role, ready } = useRole();
  const { isFavorite, toggleFavorite } = useFavoritesContext();

  // До ready — пустое место того же размера (без мелькания/сдвига).
  if (!ready) {
    return <div className={`h-8 w-8 flex-shrink-0 ${className}`} aria-hidden />;
  }
  // Избранное — только для клиента. Для агента (в список он не попадёт) — ничего.
  if (role !== "client") return null;

  const fav = isFavorite(productId);

  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        toggleFavorite(productId);
      }}
      aria-label={fav ? "Убрать из избранного" : "В избранное"}
      aria-pressed={fav}
      className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full active:scale-90 transition-transform ${
        fav ? "text-red-500" : "text-gray-400"
      } ${className}`}
    >
      {/* Сердце: залитое — в избранном, контур — нет */}
      <svg
        className="h-6 w-6"
        viewBox="0 0 24 24"
        fill={fav ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth={2}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"
        />
      </svg>
    </button>
  );
}
