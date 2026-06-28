'use client';

import { createContext, useContext, ReactNode } from 'react';
import { useCart, CartItem } from '@/lib/useCart';
import { Product } from '@/lib/types';

interface CartContextValue {
  items: CartItem[];
  totalItems: number;
  totalPrice: number;
  isLoaded: boolean;
  addToCart: (product: Product) => void;
  /** Добавить товар в заданном количестве с капом по текущему остатку (D-05, этап 19). */
  addToCartWithQuantity: (product: Product, quantity: number) => void;
  removeFromCart: (productId: string) => void;
  updateQuantity: (productId: string, quantity: number) => void;
  clearCart: () => void;
  getQuantity: (productId: string) => number;
  isInCart: (productId: string) => boolean;
}

const CartContext = createContext<CartContextValue | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const cart = useCart();
  return <CartContext.Provider value={cart}>{children}</CartContext.Provider>;
}

export function useCartContext(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error('useCartContext must be used inside CartProvider');
  return ctx;
}
