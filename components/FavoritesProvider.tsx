"use client";

import { createContext, useContext, ReactNode } from "react";
import { useFavorites } from "@/lib/useFavorites";

// Контекст избранного — общий для сердечек на карточках, иконки в шапке
// и вида «Избранное». Один экземпляр useFavorites на всё дерево.
interface FavoritesContextValue {
  favoriteIds: string[];
  isLoaded: boolean;
  count: number;
  toggleFavorite: (productId: string) => void;
  isFavorite: (productId: string) => boolean;
}

const FavoritesContext = createContext<FavoritesContextValue | null>(null);

export function FavoritesProvider({ children }: { children: ReactNode }) {
  const fav = useFavorites();
  return (
    <FavoritesContext.Provider value={fav}>{children}</FavoritesContext.Provider>
  );
}

export function useFavoritesContext(): FavoritesContextValue {
  const ctx = useContext(FavoritesContext);
  if (!ctx) throw new Error("useFavoritesContext должен использоваться внутри FavoritesProvider");
  return ctx;
}
