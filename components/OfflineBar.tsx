"use client";

// Клиентский компонент-«остров»: полоска статуса под синей шапкой каталога.
// Три состояния (решение D-01 из CONTEXT.md):
//   1. Онлайн + данные свежие (< 24 ч) → return null (полоска скрыта, чистая шапка).
//   2. Офлайн → нейтральная серая полоска «Офлайн • данные за ЧЧ:ММ» (D-03).
//   3. Данные старше 24 ч (онлайн ИЛИ офлайн) → жёлтая предупреждающая полоска.
//
// Позиционирование (D-02): sticky под шапкой (top-12 = высота шапки h-12),
// z-40 (ниже шапки z-50), прокручивается со страницей (не fixed).

import { useState, useEffect } from "react";
import { useOnlineStatus } from "@/lib/useOnlineStatus";
import { getMeta } from "@/lib/catalogDb";
import { formatSyncTime } from "@/lib/formatSyncTime";

/** Порог устаревания данных: 24 часа в миллисекундах */
const STALE_THRESHOLD_MS = 24 * 60 * 60 * 1000;

export default function OfflineBar() {
  const isOnline = useOnlineStatus();

  // Unix-ms последней синхронизации; null до первой синхронизации или при ошибке IDB
  const [syncedAt, setSyncedAt] = useState<number | null>(null);

  useEffect(() => {
    // Читаем timestamp последней синхронизации из IndexedDB.
    // Обёрнуто в try/catch: getMeta может бросить в приватном режиме iOS (T-12-02).
    const load = async () => {
      try {
        const ts = await getMeta<number>("syncTimestamp");
        // ts может быть undefined (ключ ещё не записан) — оставляем null
        if (ts !== undefined) {
          setSyncedAt(ts);
        }
      } catch {
        // При ошибке IDB оставляем syncedAt = null — полоска не сломает шапку
      }
    };

    void load();
  }, []); // запускаем один раз при монтировании

  // Вычисляем «устаревшесть»: данные старше 24 ч — нужно предупредить.
  // Если syncedAt === null (нет данных) — не считаем устаревшими: агент ещё не синхронизировался.
  const isStale =
    syncedAt !== null && Date.now() - syncedAt > STALE_THRESHOLD_MS;

  // Состояние 1: онлайн + данные свежие → полоска скрыта.
  // Также скрываем пока syncedAt === null и онлайн — не мигаем при первом запуске.
  if (isOnline && !isStale) {
    return null;
  }

  // Определяем цвет и текст по состоянию (D-03):
  //   устаревшие данные → жёлтый (предупреждение, самое важное);
  //   офлайн со свежими → нейтральный серый (рабочая норма для агента).
  const isYellowState = isStale;

  const containerClass = isYellowState
    ? "bg-yellow-50 text-yellow-800"
    : "bg-gray-100 text-gray-600";

  // Текст: офлайн добавляет «Офлайн •» перед меткой свежести.
  // При устаревших данных в онлайне — только метка (без «Офлайн»).
  const label = !isOnline
    ? `Офлайн • ${formatSyncTime(syncedAt)}`
    : formatSyncTime(syncedAt);

  return (
    // Внешний div: sticky под шапкой (top-12), полная ширина, над прокруткой контента (z-40)
    <div className={`sticky top-12 z-40 w-full ${containerClass}`}>
      {/* Внутренний контейнер: ограничение ширины + центрирование, как у шапки */}
      <div className="max-w-screen-2xl mx-auto w-full px-2 py-1 text-xs text-center">
        {label}
      </div>
    </div>
  );
}
