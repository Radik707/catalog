"use client";

import { useRole } from "@/lib/useRole";
import { useFavoritesContext } from "@/components/FavoritesProvider";

// Кнопка в правом верхнем углу фото карточки.
//   Агент (sales) + есть фото → стрелки «развернуть фото» (открывает Lightbox).
//   Клиент (client)           → сердечко «в избранное» (toggle).
// Решение по роли — из useRole; ready не нужен: до монтирования дефолт client
// = сердечко, что является корректным безопасным поведением при гидратации.
interface CardCornerButtonProps {
  productId: string;
  // Открыть полноэкранный просмотрщик (только при наличии фото) — для агента.
  onPhotoOpen?: () => void;
  // Есть ли что разворачивать. У агента без фото показываем сердечко,
  // чтобы избранное оставалось доступным (разворачивать нечего).
  canOpenPhoto?: boolean;
  // Размер кнопки: компактный для миниатюр списка.
  size?: "sm" | "md";
}

export default function CardCornerButton({
  productId,
  onPhotoOpen,
  canOpenPhoto = false,
  size = "md",
}: CardCornerButtonProps) {
  const { role } = useRole();
  const { isFavorite, toggleFavorite } = useFavoritesContext();

  const box =
    size === "sm"
      ? "h-7 w-7"
      : "h-8 w-8";
  const icon = size === "sm" ? "h-4 w-4" : "h-5 w-5";

  // ── Агент (sales) с фото: кнопка раскрытия фото ──
  if (role === "sales" && canOpenPhoto) {
    return (
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onPhotoOpen?.();
        }}
        aria-label="Открыть фото на весь экран"
        className={`absolute top-1 right-1 z-10 flex ${box} items-center justify-center rounded-full bg-white/80 text-gray-700 shadow-sm backdrop-blur-sm active:bg-white`}
      >
        {/* Стрелки в разные стороны (arrows-pointing-out, heroicons) */}
        <svg className={icon} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
          />
        </svg>
      </button>
    );
  }

  // ── Клиент: сердечко избранного ──
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
      className={`absolute top-1 right-1 z-10 flex ${box} items-center justify-center rounded-full bg-white/80 shadow-sm backdrop-blur-sm active:bg-white ${
        fav ? "text-red-500" : "text-gray-500"
      }`}
    >
      {/* Сердце: залитое когда в избранном, контур — когда нет */}
      <svg
        className={icon}
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
