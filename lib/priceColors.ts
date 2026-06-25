// Палитра цвета цены на карточках. Цвет — общая настройка сайта, управляется
// из админ-панели (раздел «Оформление») и хранится во вкладке «Настройки»
// Google Sheet (ключ price_color). Каталог читает её через /api/settings.
//
// Tailwind-классы заданы литералами — иначе JIT их не соберёт.
export type PriceColor = "black" | "violet" | "green" | "blue" | "red";

export const PRICE_COLOR_CLASS: Record<PriceColor, string> = {
  black: "text-gray-900",
  violet: "text-violet-600",
  green: "text-green-600",
  blue: "text-blue-600",
  red: "text-red-600",
};

// По умолчанию (пока владелец не выбрал в админке) — фиолетовый (премиальный).
export const DEFAULT_PRICE_COLOR: PriceColor = "violet";

// Класс цвета по ключу. Неизвестный/пустой ключ → цвет по умолчанию.
export function priceColorClass(color?: string): string {
  return PRICE_COLOR_CLASS[(color as PriceColor)] ?? PRICE_COLOR_CLASS[DEFAULT_PRICE_COLOR];
}

// Список вариантов для админ-панели (порядок = порядок кнопок).
export const PRICE_COLOR_OPTIONS: { key: PriceColor; label: string }[] = [
  { key: "violet", label: "Фиолетовый" },
  { key: "green", label: "Зелёный" },
  { key: "blue", label: "Синий" },
  { key: "red", label: "Красный" },
  { key: "black", label: "Чёрный" },
];
