"use client";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  count: number;
}

export default function SearchBar({ value, onChange, count }: SearchBarProps) {
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
        />

        {/* Счётчик + кнопка очистки */}
        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
          <span className="text-xs text-gray-400">{count}</span>
          {value && (
            <button
              onClick={() => onChange("")}
              className="w-5 h-5 flex items-center justify-center rounded-full
                         bg-gray-300 text-white text-xs active:bg-gray-400"
            >
              ✕
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
