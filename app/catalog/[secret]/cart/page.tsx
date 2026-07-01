"use client";

import { useState } from "react";
import { useCartContext } from "@/components/CartProvider";
import { useCatalogSettings } from "@/components/CatalogSettings";
import { effectivePrice } from "@/lib/pricing";
import { useOnlineStatus } from "@/lib/useOnlineStatus";
import QuantityInput from "@/components/QuantityInput";
// История заказов — запись снимка при отправке (план 16-02).
// Через общий провайдер (а не прямой хук) — иначе две кнопки отправки затирают записи друг друга (CR-01).
import { useOrderHistoryContext } from "@/components/OrderHistoryProvider";
import type { OrderHistoryEntry, OrderHistoryItem, Product } from "@/lib/types";
// Реальная единица товара в снимке заказа: «шт» / «блок» / «кг» / … (D-10, план 21-02).
import { getUnit } from "@/lib/getUnit";

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
  const { items, updateQuantity, removeFromCart, clearCart } =
    useCartContext();
  // Форма цен — для +5% на товары Ефимовой (форма «1»)
  const { priceForm } = useCatalogSettings();

  // Итог с учётом формы цен (а не базовый totalPrice из контекста)
  const totalPrice = items.reduce(
    (sum, { product, quantity }) => sum + effectivePrice(product, priceForm) * quantity,
    0
  );

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
        {/* Заметная зелёная кнопка-рамка по центру: переход в отправленные заказы.
            После очистки корзины это главный понятный путь «куда дальше» — выделяем
            рамкой, крупным шрифтом и фоном, чтобы было явно видно, что сюда можно нажать. */}
        <a
          href={`/catalog/${params.secret}/orders`}
          className="mt-6 inline-flex items-center justify-center gap-2 border-2 border-green-500 bg-green-50 text-green-700 text-base font-semibold rounded-xl px-6 py-3 shadow-sm active:opacity-70"
        >
          Мои отправленные заказы →
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
        <div className="flex items-center gap-3 flex-shrink-0">
          {/* Ссылка на историю заказов из заполненной корзины (D-05).
              Овальная «таблетка» с бирюзовым фоном — выделяем как отдельный вход в историю. */}
          <a
            href={`/catalog/${params.secret}/orders`}
            className="text-xs font-medium text-white bg-teal-500 rounded-full px-3 py-1 active:opacity-70 whitespace-nowrap"
          >
            История заказов
          </a>
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
      </div>

      {/* Список товаров */}
      <div className="flex-1 bg-white">
        {items.map(({ product, quantity }) => (
          <div
            key={product.id}
            className="flex items-center gap-3 px-4 py-3 border-b border-gray-100"
          >
            {/* Мини-фото слева */}
            <div className="flex-shrink-0 w-12 h-12 rounded overflow-hidden border border-gray-100 bg-white">
              {product.imageUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={product.imageUrl}
                  alt={product.name}
                  className="w-full h-full object-contain"
                  loading="lazy"
                  decoding="async"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-gray-300">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v13.5a1.5 1.5 0 001.5 1.5z" />
                  </svg>
                </div>
              )}
            </div>

            {/* Название и цена */}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 leading-tight">
                {product.name}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                {effectivePrice(product, priceForm).toFixed(2)} ₽ / шт
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
              <QuantityInput
                value={quantity}
                max={product.stock}
                onCommit={(v) => updateQuantity(product.id, v)}
                className="w-8 text-sm text-gray-900"
              />
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
                {(effectivePrice(product, priceForm) * quantity).toFixed(2)} ₽
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

/* ---------- Хелпер: сборка снимка заказа для истории ---------- */
// Строит массив OrderHistoryItem из корзины с ценами через effectivePrice (D-07, D-08).
// Снимок сохраняет «цену, которую видел клиент», совпадающую с текстом заказа (D-08).
// Тип параметра product расширен до Product — для getUnit нужны поля group/name (D-10, план 21-02).
function buildOrderSnapshot(
  items: Array<{ product: Product; quantity: number }>,
  priceForm: Parameters<typeof effectivePrice>[1]
): { snapshot: OrderHistoryItem[]; total: number } {
  const snapshot: OrderHistoryItem[] = items.map(({ product, quantity }) => {
    // Реальная единица через getUnit: «за шт» → «шт», «за блок» → «блок», fallback «шт» (D-10).
    // getUnit возвращает строку с предлогом «за …» — срезаем его перед записью в снимок.
    const rawUnit = getUnit(product);
    const unit = rawUnit ? rawUnit.replace(/^за\s+/i, "") || "шт" : "шт";
    return {
      id: product.id,
      name: product.name,
      quantity,
      priceAtOrder: effectivePrice(product, priceForm), // цена «как видел клиент» (D-08)
      unit,
      imageUrl: product.imageUrl,
    };
  });
  const total = snapshot.reduce(
    (sum, item) => sum + item.priceAtOrder * item.quantity,
    0
  );
  return { snapshot, total };
}

/* ---------- Кнопка Telegram ---------- */
function TelegramButton() {
  const { items } = useCartContext();
  // Форма цен — текст заказа должен совпадать с тем, что видит клиент
  const { priceForm } = useCatalogSettings();
  // Хук состояния сети — true при наличии подключения, false в офлайне.
  // Обновляется автоматически по событиям online/offline без перезагрузки страницы.
  const isOnline = useOnlineStatus();
  // Хук истории заказов — addEntry записывает снимок при отправке (D-01, D-02).
  // Общий экземпляр через контекст: обе кнопки делят одно состояние истории (CR-01).
  const { addEntry } = useOrderHistoryContext();

  // Сборка текста заказа и открытие Telegram (с учётом формы цен)
  const handleSend = () => {
    const totalPrice = items.reduce(
      (sum, { product, quantity }) => sum + effectivePrice(product, priceForm) * quantity,
      0
    );
    const lines = items.map(
      ({ product, quantity }) =>
        `• ${product.name} × ${quantity} = ${(effectivePrice(product, priceForm) * quantity).toFixed(2)} ₽`
    );
    const text = [
      "Заказ:",
      ...lines,
      "",
      `Итого: ${totalPrice.toFixed(2)} ₽`,
    ].join("\n");

    const url = `https://t.me/${TELEGRAM_USERNAME}?text=${encodeURIComponent(text)}`;
    window.open(url, "_blank");

    // Записываем снимок заказа в историю ПОСЛЕ открытия Telegram (D-01, D-02, D-03).
    // clearCart НЕ вызывается — корзина остаётся (D-03).
    const { snapshot, total } = buildOrderSnapshot(items, priceForm);
    const entry: OrderHistoryEntry = {
      id: typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : Date.now().toString(),
      items: snapshot,
      total,
      createdAt: new Date().toISOString(),
      channel: 'telegram', // канал по нажатой кнопке (D-02)
    };
    addEntry(entry);
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
  const { items } = useCartContext();
  // Форма цен — текст заказа должен совпадать с тем, что видит клиент
  const { priceForm } = useCatalogSettings();
  // Хук состояния сети — офлайн блокирует кнопку, как у Telegram.
  const isOnline = useOnlineStatus();
  // Локальное состояние «идёт отправка» — пока ждём короткий id от сервера.
  const [sending, setSending] = useState(false);
  // Хук истории заказов — addEntry записывает снимок при отправке (D-01, D-02).
  // Общий экземпляр через контекст: обе кнопки делят одно состояние истории (CR-01).
  const { addEntry } = useOrderHistoryContext();

  // Фича выключена, если не заданы ник бота и эндпоинт приёма заказа.
  if (!MAX_BOT || !MAX_ORDER_URL) return null;

  // Сборка текста заказа — формат тот же, что у Telegram-кнопки (с учётом формы цен).
  const buildText = () => {
    const totalPrice = items.reduce(
      (sum, { product, quantity }) => sum + effectivePrice(product, priceForm) * quantity,
      0
    );
    const lines = items.map(
      ({ product, quantity }) =>
        `• ${product.name} × ${quantity} = ${(effectivePrice(product, priceForm) * quantity).toFixed(2)} ₽`
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

    // Строим снимок заказа один раз до ветвления try/catch (D-01, D-02, D-03).
    // Запись в историю происходит ровно один раз вне зависимости от успеха fetch.
    // clearCart НЕ вызывается — корзина остаётся (D-03).
    const { snapshot, total } = buildOrderSnapshot(items, priceForm);
    const historyEntry: OrderHistoryEntry = {
      id: typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : Date.now().toString(),
      items: snapshot,
      total,
      createdAt: new Date().toISOString(),
      channel: 'max', // канал по нажатой кнопке (D-02)
    };
    addEntry(historyEntry);

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
