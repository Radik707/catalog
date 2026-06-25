"use client";

import { useState, useEffect, useCallback } from "react";

// Избранное клиента — список id товаров в localStorage.
// Сделано по образцу useCart: одно состояние на провайдер, синхронно с localStorage.
const FAV_KEY = "catalog-favorites";

// Читаем избранное из localStorage (массив id товаров).
function loadFavorites(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(FAV_KEY);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr.map(String) : [];
  } catch {
    return [];
  }
}

// Сохраняем избранное в localStorage.
function saveFavorites(ids: string[]) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(FAV_KEY, JSON.stringify(ids));
  } catch {
    // localStorage может быть недоступен (приватный режим) — молча пропускаем
  }
}

export function useFavorites() {
  const [ids, setIds] = useState<string[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  // Загружаем при монтировании (только на клиенте)
  useEffect(() => {
    setIds(loadFavorites());
    setIsLoaded(true);
  }, []);

  // Сохраняем при каждом изменении (после первой загрузки)
  useEffect(() => {
    if (isLoaded) saveFavorites(ids);
  }, [ids, isLoaded]);

  // Переключить избранное у товара
  const toggleFavorite = useCallback((productId: string) => {
    setIds((prev) =>
      prev.includes(productId)
        ? prev.filter((id) => id !== productId)
        : [...prev, productId]
    );
  }, []);

  // Есть ли товар в избранном
  const isFavorite = useCallback(
    (productId: string): boolean => ids.includes(productId),
    [ids]
  );

  return {
    favoriteIds: ids,
    isLoaded,
    count: ids.length,
    toggleFavorite,
    isFavorite,
  };
}
