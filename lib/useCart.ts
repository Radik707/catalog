'use client';

import { useState, useEffect, useCallback } from 'react';
import { Product } from './types';

// Товар в корзине = товар + количество
export interface CartItem {
  product: Product;
  quantity: number;
}

const CART_KEY = 'catalog-cart';

// Читаем корзину из localStorage
function loadCart(): CartItem[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(CART_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

// Сохраняем корзину в localStorage
function saveCart(items: CartItem[]) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(CART_KEY, JSON.stringify(items));
  } catch {
    // localStorage может быть недоступен (приватный режим и т.д.)
  }
}

export function useCart() {
  const [items, setItems] = useState<CartItem[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  // Загружаем корзину при монтировании (только на клиенте)
  useEffect(() => {
    setItems(loadCart());
    setIsLoaded(true);
  }, []);

  // Сохраняем при каждом изменении (после первой загрузки)
  useEffect(() => {
    if (isLoaded) {
      saveCart(items);
    }
  }, [items, isLoaded]);

  // Добавить товар в корзину
  const addToCart = useCallback((product: Product) => {
    if (product.stock <= 0) return;

    setItems((prev) => {
      const existing = prev.find((item) => item.product.id === product.id);
      if (existing) {
        // Не больше, чем остаток
        const newQty = Math.min(existing.quantity + 1, product.stock);
        return prev.map((item) =>
          item.product.id === product.id
            ? { ...item, quantity: newQty }
            : item
        );
      }
      return [...prev, { product, quantity: 1 }];
    });
  }, []);

  // Удалить товар из корзины
  const removeFromCart = useCallback((productId: string) => {
    setItems((prev) => prev.filter((item) => item.product.id !== productId));
  }, []);

  // Изменить количество товара
  const updateQuantity = useCallback((productId: string, quantity: number) => {
    if (quantity <= 0) {
      setItems((prev) => prev.filter((item) => item.product.id !== productId));
      return;
    }

    setItems((prev) =>
      prev.map((item) => {
        if (item.product.id !== productId) return item;
        // Не больше, чем остаток
        const newQty = Math.min(quantity, item.product.stock);
        return { ...item, quantity: newQty };
      })
    );
  }, []);

  // Очистить корзину
  const clearCart = useCallback(() => {
    setItems([]);
  }, []);

  // Получить количество конкретного товара в корзине
  const getQuantity = useCallback(
    (productId: string): number => {
      const item = items.find((i) => i.product.id === productId);
      return item ? item.quantity : 0;
    },
    [items]
  );

  // Проверить, есть ли товар в корзине
  const isInCart = useCallback(
    (productId: string): boolean => {
      return items.some((item) => item.product.id === productId);
    },
    [items]
  );

  // Общее количество товаров (сумма всех quantity)
  const totalItems = items.reduce((sum, item) => sum + item.quantity, 0);

  // Итоговая сумма
  const totalPrice = items.reduce(
    (sum, item) => sum + item.product.price * item.quantity,
    0
  );

  return {
    items,
    isLoaded,
    addToCart,
    removeFromCart,
    updateQuantity,
    clearCart,
    getQuantity,
    isInCart,
    totalItems,
    totalPrice,
  };
}
