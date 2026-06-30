'use client';

import { useState, useEffect, useCallback } from 'react';

// Ключ localStorage — в стиле catalog-* (D-08, паттерн useOrderHistory)
const HISTORY_KEY = 'catalog-search-history';

// Максимальное количество запросов в истории (FIFO-потолок, D-08)
const MAX_HISTORY_ENTRIES = 10;

// Читаем историю поиска из localStorage.
// SSR-безопасно: при typeof window === 'undefined' возвращаем [].
// Мягкая деградация: битый JSON и нестроковые записи не бросают исключение (T-20-06).
function loadHistory(): string[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    const arr = raw ? JSON.parse(raw) : [];
    // Фильтруем только непустые строки — защита от инъекций/повреждённых данных (T-20-06)
    return Array.isArray(arr) ? arr.filter((q) => typeof q === 'string' && q.trim()) : [];
  } catch {
    // Битый JSON — возвращаем пустой список, не падаем
    return [];
  }
}

// Сохраняем историю поиска в localStorage.
// Тихий try/catch: localStorage может быть недоступен в приватном режиме iOS (D-09).
function saveHistory(entries: string[]) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(entries));
  } catch {
    // localStorage недоступен (приватный режим) — молча пропускаем
  }
}

// Хук истории поиска.
// Хранит недавние поисковые запросы в localStorage — без сетевых вызовов (D-09, офлайн-совместимость).
// Структура по образцу useOrderHistory: load-on-mount + save-on-change + isLoaded-флаг (SSR-safe).
// Отличия от useOrderHistory: свежие СВЕРХУ ([q, ...without]); дедуп по тексту (регистронезависимо);
// потолок 10 вместо 20; тип записи — string вместо OrderHistoryEntry.
export function useSearchHistory() {
  const [entries, setEntries] = useState<string[]>([]);
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

  // Добавить запрос в историю (дедуп регистронезависимо, свежие сверху, FIFO-потолок 10)
  const addQuery = useCallback((q: string) => {
    const query = q.trim();
    // Пустые запросы не сохраняем (D-08)
    if (!query) return;
    setEntries((prev) => {
      // Удаляем предыдущий вариант того же запроса (дедуп, регистронезависимо)
      const without = prev.filter((x) => x.toLowerCase() !== query.toLowerCase());
      // Кладём свежий вариант сверху (не снизу — как в Ozon/WB)
      const next = [query, ...without];
      return next.slice(0, MAX_HISTORY_ENTRIES);
    });
  }, []);

  // Удалить один запрос из истории (по точному совпадению)
  const removeQuery = useCallback((q: string) => {
    setEntries((prev) => prev.filter((x) => x !== q));
  }, []);

  // Очистить всю историю поиска
  const clearHistory = useCallback(() => {
    setEntries([]);
  }, []);

  return {
    entries,
    isLoaded,
    addQuery,
    removeQuery,
    clearHistory,
  };
}
