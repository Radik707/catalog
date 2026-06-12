"use client";

// Лёгкий клиентский хук для чтения состояния сети.
// Единственная отвественность: отслеживать navigator.onLine через события online/offline.
// НЕ запускает useCatalogSync и НЕ обращается к IndexedDB — это тонкая обёртка.
// Используется в OfflineBar, TelegramButton и кнопке отправки в cart/page.tsx.

import { useState, useEffect } from "react";

/**
 * useOnlineStatus — возвращает текущее состояние сети.
 * SSR-safe: на сервере navigator недоступен, начальное значение всегда true
 * (исправляется в useEffect на клиенте).
 */
export function useOnlineStatus(): boolean {
  // Инициализируем true — безопасно для SSR/гидратации.
  // На сервере navigator нет, поэтому ставим «онлайн» как дефолт.
  const [isOnline, setIsOnline] = useState<boolean>(true);

  useEffect(() => {
    // Исправляем начальное значение — читаем реальное состояние на клиенте.
    // Проверка typeof нужна для защиты от окружений без navigator (тесты, SSR).
    if (typeof navigator !== "undefined") {
      setIsOnline(navigator.onLine);
    }

    // Обработчики событий сети — реагируем мгновенно при изменении подключения.
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    // Cleanup: снимаем подписки при размонтировании компонента.
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []); // эффект без зависимостей — запускается один раз при монтировании

  return isOnline;
}
