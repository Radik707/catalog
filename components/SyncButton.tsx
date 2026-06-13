"use client";

// Кнопка «Обновить каталог» (↻) в синей шапке каталога.
// Цель: агент жмёт ↻ → fetch свежих данных + diff-предзагрузка новых фото — одним нажатием (SYNC-01).
// Состояния: idle → (нажатие) → spin (крутится, busy) → done (галочка ≈1.5 с) → idle.
// Офлайн: кнопка disabled с понятным title — нечего тянуть без сети.
// НЕ создаёт второй экземпляр useCatalogSync — читает единственный из CatalogSyncProvider.

import { useState } from "react";
import { useCatalogSyncContext } from "@/components/CatalogSyncProvider";

export default function SyncButton() {
  // refetch — ручная синхронизация из общего провайдера (тот же экземпляр, что у CatalogView)
  // isOnline — состояние сети из того же хука; НЕ дублируем useOnlineStatus здесь
  const { refetch, isOnline } = useCatalogSyncContext();

  // Локальное состояние кнопки: идёт ли сейчас обновление
  const [busy, setBusy] = useState(false);
  // Кратковременный флаг «готово» — показывает галочку ≈1.5 с после успешного обновления (D-02)
  const [done, setDone] = useState(false);

  // Обработчик нажатия кнопки
  const handleRefresh = async () => {
    // Защита от двойного нажатия и от нажатия в офлайне (T-13-04)
    if (!isOnline || busy) return;

    setBusy(true);
    try {
      // refetch обновляет и данные каталога, и diff-предзагрузку новых фото (D-03)
      await refetch();
    } finally {
      // В любом случае (успех или ошибка) — снимаем состояние «крутится»
      setBusy(false);
      // Кратковременно показываем галочку «готово»; через 1.5 с возвращаемся в idle
      setDone(true);
      setTimeout(() => setDone(false), 1500);
    }
  };

  // Класс кнопки: при busy/done — активный фон (bg-white/30), иначе hover-подсветка
  const btnClass = `flex h-9 w-9 items-center justify-center rounded-full transition-colors ${
    busy || done
      ? "bg-white/30"
      : !isOnline
      ? "opacity-50 cursor-not-allowed"
      : "hover:bg-white/15"
  }`;

  return (
    <button
      onClick={handleRefresh}
      aria-label="Обновить каталог"
      disabled={!isOnline || busy}
      // Подсказка при офлайн — пользователь поймёт почему кнопка неактивна (D-03, T-13-04)
      title={!isOnline ? "Нужен интернет для обновления" : "Обновить каталог"}
      className={btnClass}
    >
      {done ? (
        /* Иконка «готово» — галочка (check), показывается ≈1.5 с после успешного обновления */
        <svg
          className="h-6 w-6 text-white"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M4.5 12.75l6 6 9-13.5"
          />
        </svg>
      ) : (
        /* Иконка «обновить» — стрелка-круговая (arrow-path из heroicons).
           Вращается при busy через animate-spin, иначе — статичная. */
        <svg
          className={`h-6 w-6 text-white${busy ? " animate-spin" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.8}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99"
          />
        </svg>
      )}
    </button>
  );
}
