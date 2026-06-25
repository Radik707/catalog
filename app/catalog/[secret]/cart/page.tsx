"use client";

import { useState } from "react";
import { useCartContext } from "@/components/CartProvider";
import { useOnlineStatus } from "@/lib/useOnlineStatus";

const TELEGRAM_USERNAME = "ZhukOleh";
// Параметры MAX: ник бота (для ссылки) и эндпоинт приёма заказа на daniella.
// Если переменные не заданы — кнопка MAX не рендерится (фича выключена).
const MAX_BOT = process.env.NEXT_PUBLIC_MAX_BOT;
const MAX_ORDER_URL = process.env.NEXT_PUBLIC_MAX_ORDER_URL;

export default function CartPage({
  params,
}: {
  params: { secret: string };
}) {
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
          href={`/catalog/${params.secret}`}
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
      <div className="px-4 py-3 border-b border-gray-100 bg-white flex items-center justify-between gap-2">
        <a
          href={`/catalog/${params.secret}`}
          className="text-blue-600 text-sm font-medium active:opacity-70 flex-shrink-0"
        >
          ← Каталог
        </a>
        <h2 className="font-semibold text-gray-900 flex-1 text-center">
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
        {/* Два канала отправки заказа: Telegram (как было) и MAX (новый) */}
        <div className="flex flex-col gap-2">
          <TelegramButton />
          <MaxOrderButton />
        </div>
      </div>
    </div>
  );
}

/* ---------- Кнопка Telegram ---------- */
function TelegramButton() {
  const { items, totalPrice } = useCartContext();
  // Хук состояния сети — true при наличии подключения, false в офлайне.
  // Обновляется автоматически по событиям online/offline без перезагрузки страницы.
  const isOnline = useOnlineStatus();

  // Сборка текста заказа и открытие Telegram — без изменений
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
    // Обёртка для кнопки + подписи офлайн-статуса
    <div className="flex flex-col gap-2">
      <button
        onClick={handleSend}
        // Офлайн-блокировка (D-05): кнопка неактивна без сети
        disabled={!isOnline}
        className="w-full py-3.5 bg-blue-600 text-white font-semibold rounded-xl text-base active:bg-blue-700 disabled:bg-gray-300 disabled:text-gray-500 disabled:cursor-not-allowed"
      >
        Отправить заказ в Telegram
      </button>
      {/* Постоянная подпись при офлайне — текст по решению D-05 */}
      {!isOnline && (
        <p className="text-xs text-gray-500 text-center leading-snug">
          Нет сети — заказ отправится, когда появится интернет. Корзина сохранена.
        </p>
      )}
    </div>
  );
}

/* ---------- Кнопка MAX ---------- */
function MaxOrderButton() {
  const { items, totalPrice } = useCartContext();
  // Хук состояния сети — офлайн блокирует кнопку, как у Telegram.
  const isOnline = useOnlineStatus();
  // Локальное состояние «идёт отправка» — пока ждём короткий id от сервера.
  const [sending, setSending] = useState(false);

  // Фича выключена, если не заданы ник бота и эндпоинт приёма заказа.
  if (!MAX_BOT || !MAX_ORDER_URL) return null;

  // Сборка текста заказа — формат тот же, что у Telegram-кнопки.
  const buildText = () => {
    const lines = items.map(
      ({ product, quantity }) =>
        `• ${product.name} × ${quantity} = ${(product.price * quantity).toFixed(2)} ₽`
    );
    return ["Заказ:", ...lines, "", `Итого: ${totalPrice.toFixed(2)} ₽`].join("\n");
  };

  const handleSend = async () => {
    const text = buildText();
    // Базовый URL каталога (без хвоста /cart) — нужен серверу для кнопок
    // «Редактировать» (→ корзина) и «В каталог» в подтверждении заказа в MAX.
    const catalogUrl =
      window.location.origin +
      window.location.pathname.replace(/\/cart\/?$/, "");
    setSending(true);
    try {
      // 1. Кладём заказ на сервер (daniella) и получаем короткий id.
      //    В ссылку ?start= помещается лишь 128 символов — весь заказ туда не влезает,
      //    поэтому передаём боту только id, а сам заказ он заберёт с сервера.
      const res = await fetch(MAX_ORDER_URL as string, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, catalog_url: catalogUrl }),
      });
      if (!res.ok) throw new Error(`status ${res.status}`);
      const { id } = await res.json();
      // 2. Открываем чат с ботом MAX. По start=<id> бот возьмёт заказ
      //    и перешлёт владельцу вместе с контактом покупателя (Модель A).
      window.open(`https://max.ru/${MAX_BOT}?start=${id}`, "_blank");
    } catch {
      // Запасной путь: сервер недоступен — открываем системный «Поделиться» MAX
      //    с уже подставленным текстом заказа (получателя покупатель выберёт сам).
      //    Так заказ не теряется, даже если бэкенд лежит.
      window.open(`https://max.ru/:share?text=${encodeURIComponent(text)}`, "_blank");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <button
        onClick={handleSend}
        // Блокируем в офлайне и на время отправки
        disabled={!isOnline || sending}
        // Фирменный сине-фиолетовый градиент MAX
        className="w-full py-3.5 bg-gradient-to-br from-[#2D9CFF] to-[#9B4DFF] text-white font-semibold rounded-xl text-base active:opacity-90 disabled:from-gray-300 disabled:to-gray-300 disabled:text-gray-500 disabled:cursor-not-allowed"
      >
        {sending ? "Открываем MAX…" : "Отправить заказ в MAX"}
      </button>
    </div>
  );
}

/* ---------- утилита ---------- */
function pluralItems(n: number): string {
  if (n % 10 === 1 && n % 100 !== 11) return "позиция";
  if ([2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100))
    return "позиции";
  return "позиций";
}
