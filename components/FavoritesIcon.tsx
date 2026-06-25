"use client";

import { usePathname, useRouter } from "next/navigation";
import { useNav } from "./NavProvider";
import { useFavoritesContext } from "./FavoritesProvider";

// Иконка-сердечко в шапке: включает режим «Избранное» (фильтр только избранных).
// Повторный тап в режиме fav — возврат в обычный каталог. Счётчик показывает
// число избранных товаров. Заняла место кнопки ↻ (она переехала в шестерёнку).
export default function FavoritesIcon({ secret }: { secret: string }) {
  const { mode, setMode } = useNav();
  const { count } = useFavoritesContext();
  const pathname = usePathname();
  const router = useRouter();
  const catalogPath = `/catalog/${secret}`;

  const active = mode === "fav";

  const handleClick = () => {
    // Тап в режиме fav возвращает в каталог, иначе — включает избранное
    setMode(active ? "catalog" : "fav");
    // Если мы не на витрине (например, в корзине) — перейти на неё.
    // Состояние навигации живёт в общем layout и переживёт переход.
    if (pathname !== catalogPath) router.push(catalogPath);
  };

  return (
    <button
      onClick={handleClick}
      aria-label="Избранное"
      aria-pressed={active}
      className={`relative flex h-9 w-9 items-center justify-center rounded-full transition-colors ${
        active ? "bg-white/30" : "hover:bg-white/15"
      }`}
    >
      <svg
        className="h-6 w-6 text-white"
        viewBox="0 0 24 24"
        fill={active ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth={2}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"
        />
      </svg>
      {count > 0 && (
        <span className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
          {count > 99 ? "99" : count}
        </span>
      )}
    </button>
  );
}
