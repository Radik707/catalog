"use client";

import { useState, useRef } from "react";

// Пропсы компонента строки поиска.
// Пропсы истории ОПЦИОНАЛЬНЫ — вызов без них (на ветке loading) не ломается.
interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  count: number;
  // История поиска (опционально) — список недавних запросов из useSearchHistory
  history?: string[];
  // Тап по запросу из истории — подставляет его в строку поиска
  onPickHistory?: (q: string) => void;
  // Удалить один запрос из истории (крестик у пункта)
  onRemoveHistory?: (q: string) => void;
  // Очистить всю историю поиска
  onClearHistory?: () => void;
}

export default function SearchBar({
  value,
  onChange,
  count,
  history,
  onPickHistory,
  onRemoveHistory,
  onClearHistory,
}: SearchBarProps) {
  // Флаг фокуса на поле поиска — управляет видимостью выпадашки истории
  const [focused, setFocused] = useState(false);
  // Ref для отслеживания: нажал ли пользователь внутри выпадашки (чтобы blur не закрыл её до тапа)
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Показывать выпадашку: поле в фокусе + история непуста + поле пустое
  const showHistory = focused && (history?.length ?? 0) > 0 && !value.trim();

  return (
    <div className="px-4 py-2 bg-white border-b border-gray-100">
      <div className="relative">
        {/* Иконка поиска */}
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>

        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Поиск товара..."
          className="w-full pl-10 pr-16 py-2.5 bg-gray-50 rounded-xl text-sm
                     border border-gray-200 focus:border-blue-500 focus:bg-white
                     focus:outline-none transition-colors"
          onFocus={() => setFocused(true)}
          onBlur={() => {
            // Задержка blur: даём тапу по пункту истории сработать раньше закрытия
            setTimeout(() => setFocused(false), 150);
          }}
        />

        {/* Счётчик + кнопка очистки */}
        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
          <span className="text-xs text-gray-400">{count}</span>
          {value && (
            <button
              onClick={() => onChange("")}
              className="w-5 h-5 flex items-center justify-center rounded-full
                         bg-gray-300 text-white text-xs active:bg-gray-400"
              aria-label="Очистить строку поиска"
            >
              ✕
            </button>
          )}
        </div>

        {/* Выпадашка недавних запросов — absolute под инпутом, z-40 (ниже шапки z-50) */}
        {showHistory && (
          <div
            ref={dropdownRef}
            className="absolute top-full left-0 right-0 z-40 mt-1 bg-white rounded-xl shadow-lg border border-gray-100"
          >
            {/* Заголовок: «Недавние запросы» + «Очистить» */}
            <div className="flex items-center justify-between px-3 pt-2 pb-1">
              <span className="text-xs text-gray-400">Недавние запросы</span>
              {onClearHistory && (
                <button
                  onPointerDown={(e) => {
                    // Предотвращаем потерю фокуса до срабатывания onClearHistory
                    e.preventDefault();
                    onClearHistory();
                  }}
                  className="text-xs text-red-500 font-medium active:opacity-70"
                  aria-label="Очистить историю поиска"
                >
                  Очистить
                </button>
              )}
            </div>

            {/* Список запросов */}
            {history?.map((q) => (
              <div
                key={q}
                className="flex items-center px-3 py-2.5 active:bg-gray-100 cursor-pointer"
                onPointerDown={(e) => {
                  // Предотвращаем потерю фокуса до срабатывания onPickHistory
                  e.preventDefault();
                  onPickHistory?.(q);
                  setFocused(false);
                }}
              >
                {/* Иконка часов — нейтральная палитра, не соперничает с синей кнопкой повтора */}
                <svg
                  className="w-4 h-4 text-gray-400 shrink-0 mr-2.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>

                {/* Текст запроса */}
                <span className="flex-1 text-sm text-gray-800 truncate">{q}</span>

                {/* Крестик удаления пункта */}
                {onRemoveHistory && (
                  <button
                    onPointerDown={(e) => {
                      // Останавливаем всплытие: крестик не должен запускать onPickHistory
                      e.stopPropagation();
                      e.preventDefault();
                      onRemoveHistory(q);
                    }}
                    className="ml-2 text-gray-400 text-sm active:text-gray-600 shrink-0"
                    aria-label={`Удалить запрос «${q}» из истории`}
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
