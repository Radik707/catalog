"use client";

import { useCartContext } from "@/components/CartProvider";

const TELEGRAM_USERNAME = "ZhukOleh";

export default function CartPage() {
  const { items, totalPrice, updateQuantity, removeFromCart, clearCart } =
    useCartContext();

  const isEmpty = items.length === 0;

  /* ---------- пустая корзина ---------- */
  if (isEmpty) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] px-4 text-center">
        <svg
          className="w-16 h-16 text-gray-200 mb-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z"
          />
        </svg>
        <p className="text-gray-400 text-lg">Корзина пуста</p>
        <a
          href="/"
          className="mt-3 text-blue-600 text-sm font-medium active:opacity-70"
        >
          Вернуться в каталог
        </a>
      </div>
    );
  }

  /* ---------- заполненная корзина ---------- */
  return (
    <div className="flex flex-col min-h-[calc(100vh-48px)]">
      {/* Заголовок страницы */}
      <div className="px-4 py-3 border-b border-gray-100 bg-white flex items-center justify-between">
        <h2 className="font-semibold text-gray-900">
          {items.length} {pluralItems(items.length)}
        </h2>
        <button
          onClick={() => {
            if (confirm("Вы действительно хотите очистить ВСЮ корзину?")) {
              clearCart();
            }
          }}
          className="text-xs text-red-500 font-medium active:opacity-70"
        >
          Очистить
        </button>
      </div>

      {/* Список товаров */}
      <div className="flex-1 bg-white">
        {items.map(({ product, quantity }) => (
          <div
            key={product.id}
            className="flex items-center gap-3 px-4 py-3 border-b border-gray-100"
          >
            {/* Название и цена */}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 leading-tight">
                {product.name}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                {product.price.toFixed(2)} ₽ / шт
              </p>
            </div>

            {/* Управление количеством */}
            <div className="flex items-center gap-1 flex-shrink-0">
              <button
                onClick={() => updateQuantity(product.id, quantity - 1)}
                className="w-7 h-7 rounded-lg bg-gray-100 text-gray-700 font-bold text-base flex items-center justify-center active:bg-gray-200"
              >
                −
              </button>
              <span className="w-6 text-center text-sm font-semibold text-gray-900">
                {quantity}
              </span>
              <button
                onClick={() => updateQuantity(product.id, quantity + 1)}
                disabled={quantity >= product.stock}
                className="w-7 h-7 rounded-lg bg-gray-100 text-gray-700 font-bold text-base flex items-center justify-center active:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                +
              </button>
            </div>

            {/* Сумма по строке */}
            <div className="flex-shrink-0 w-20 text-right">
              <p className="text-sm font-bold text-gray-900">
                {(product.price * quantity).toFixed(2)} ₽
              </p>
              <button
                onClick={() => removeFromCart(product.id)}
                className="text-xs text-red-400 active:opacity-70"
              >
                Удалить
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Итог + кнопка */}
      <div className="sticky bottom-0 bg-white border-t border-gray-200 px-4 py-4 shadow-[0_-4px_12px_rgba(0,0,0,0.06)]">
        <div className="flex items-center justify-between mb-3">
          <span className="text-base text-gray-600">Итого:</span>
          <span className="text-xl font-bold text-gray-900">
            {totalPrice.toFixed(2)} ₽
          </span>
        </div>
        <TelegramButton />
      </div>
    </div>
  );
}

/* ---------- Кнопка Telegram (заглушка до задачи 2) ---------- */
function TelegramButton() {
  const { items, totalPrice } = useCartContext();

  const handleSend = () => {
    const lines = items.map(
      ({ product, quantity }) =>
        `• ${product.name} × ${quantity} = ${(product.price * quantity).toFixed(2)} ₽`
    );
    const text = [
      "Заказ:",
      ...lines,
      "",
      `Итого: ${totalPrice.toFixed(2)} ₽`,
    ].join("\n");

    const url = `https://t.me/${TELEGRAM_USERNAME}?text=${encodeURIComponent(text)}`;
    window.open(url, "_blank");
  };

  return (
    <button
      onClick={handleSend}
      className="w-full py-3.5 bg-blue-600 text-white font-semibold rounded-xl text-base active:bg-blue-700"
    >
      Отправить заказ в Telegram
    </button>
  );
}

/* ---------- утилита ---------- */
function pluralItems(n: number): string {
  if (n % 10 === 1 && n % 100 !== 11) return "позиция";
  if ([2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100))
    return "позиции";
  return "позиций";
}
