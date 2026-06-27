'use client';

// Провайдер истории заказов — единственный экземпляр useOrderHistory на всё приложение.
// Зачем: useOrderHistory хранит состояние в useState, поэтому каждый прямой вызов хука
// создаёт НЕЗАВИСИМУЮ копию. На странице корзины кнопки Telegram и MAX вызывали хук
// по отдельности — два разных состояния, которые затирали записи друг друга в localStorage
// (потеря заказа при отправке двумя каналами подряд, CR-01). Общий провайдер, как у корзины
// (CartProvider), даёт всем потребителям ОДНО состояние истории.

import { createContext, useContext, ReactNode } from 'react';
import { useOrderHistory } from '@/lib/useOrderHistory';

// Тип значения контекста = ровно то, что возвращает хук-store
type OrderHistoryContextValue = ReturnType<typeof useOrderHistory>;

const OrderHistoryContext = createContext<OrderHistoryContextValue | null>(null);

export function OrderHistoryProvider({ children }: { children: ReactNode }) {
  // Единственный вызов хука — его состояние раздаётся через контекст
  const history = useOrderHistory();
  return (
    <OrderHistoryContext.Provider value={history}>
      {children}
    </OrderHistoryContext.Provider>
  );
}

// Доступ к общей истории заказов из любого потребителя внутри провайдера
export function useOrderHistoryContext(): OrderHistoryContextValue {
  const ctx = useContext(OrderHistoryContext);
  if (!ctx) {
    throw new Error('useOrderHistoryContext должен использоваться внутри OrderHistoryProvider');
  }
  return ctx;
}
