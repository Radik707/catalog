'use client';

import { useState, useEffect, useCallback } from 'react';
import { OrderHistoryEntry } from './types';

// Ключ localStorage — в стиле catalog-* (паттерн useCart/useFavorites)
const HISTORY_KEY = 'catalog-order-history';

// Максимальное количество записей истории (FIFO-потолок, D-13)
const MAX_HISTORY_ENTRIES = 20;

// Проверяем, что запись истории содержит обязательные поля (мягкая деградация, D-14).
// Битые/неполные записи (повреждённый JSON, отсутствующие поля) молча пропускаются.
function isValidEntry(entry: unknown): entry is OrderHistoryEntry {
  if (!entry || typeof entry !== 'object') return false;
  const e = entry as Record<string, unknown>;
  return (
    typeof e.id === 'string' &&
    Array.isArray(e.items) &&
    typeof e.createdAt === 'string' &&
    (e.channel === 'telegram' || e.channel === 'max')
  );
}

// Читаем историю заказов из localStorage.
// SSR-безопасно: при typeof window === 'undefined' возвращаем [].
// Битый JSON или неполные записи не бросают исключение — мягкая деградация (D-14).
function loadHistory(): OrderHistoryEntry[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    const arr = raw ? JSON.parse(raw) : [];
    // Array.isArray-проверка + фильтрация невалидных записей (мягкая деградация D-14)
    return Array.isArray(arr) ? arr.filter(isValidEntry) : [];
  } catch {
    return [];
  }
}

// Сохраняем историю заказов в localStorage.
// Тихий try/catch: localStorage может быть недоступен в приватном режиме iOS.
function saveHistory(entries: OrderHistoryEntry[]) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(entries));
  } catch {
    // localStorage может быть недоступен (приватный режим) — молча пропускаем
  }
}

// Хук истории заказов.
// Работает только через localStorage — без сетевых вызовов (HIST-02, офлайн-совместимость).
// Структура по образцу useCart: load-on-mount + save-on-change + isLoaded-флаг.
export function useOrderHistory() {
  const [entries, setEntries] = useState<OrderHistoryEntry[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  // Загружаем историю при монтировании (только на клиенте)
  useEffect(() => {
    setEntries(loadHistory());
    setIsLoaded(true);
  }, []);

  // Сохраняем при каждом изменении (после первой загрузки)
  useEffect(() => {
    if (isLoaded) {
      saveHistory(entries);
    }
  }, [entries, isLoaded]);

  // Добавить запись в историю (FIFO-вытеснение при превышении потолка 20, D-13)
  const addEntry = useCallback((entry: OrderHistoryEntry) => {
    setEntries((prev) => {
      const next = [...prev, entry];
      // При превышении потолка убираем самые старые записи (slice с начала)
      return next.length > MAX_HISTORY_ENTRIES
        ? next.slice(next.length - MAX_HISTORY_ENTRIES)
        : next;
    });
  }, []);

  // Удалить одну запись из истории по id (D-12)
  const removeEntry = useCallback((entryId: string) => {
    setEntries((prev) => prev.filter((e) => e.id !== entryId));
  }, []);

  // Очистить всю историю заказов (D-12)
  const clearHistory = useCallback(() => {
    setEntries([]);
  }, []);

  return {
    entries,
    isLoaded,
    addEntry,
    removeEntry,
    clearHistory,
  };
}
