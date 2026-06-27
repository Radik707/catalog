'use client';

// Страница «Отправленные заказы» — история отправленных через Telegram/MAX заказов.
// Данные хранятся в localStorage устройства (HIST-02, офлайн-совместимость).
// Не содержит слов «статус», «принято», «в доставке» — это история отправки, не статус поставщика (HIST-03, инвариант v1.4).

import { useOrderHistory } from '@/lib/useOrderHistory';
import type { OrderHistoryEntry, OrderHistoryItem } from '@/lib/types';

export default function OrdersPage({ params }: { params: { secret: string } }) {
  const { entries, isLoaded, removeEntry, clearHistory } = useOrderHistory();

  // Пока localStorage не загружен — не рендерим список, чтобы не было мелькания пустого состояния
  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-gray-400 text-sm">Загрузка…</p>
      </div>
    );
  }

  /* ---------- пустое состояние ---------- */
  if (entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] px-4 text-center">
        {/* Иконка «история/документ» */}
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
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <p className="text-gray-400 text-lg">Вы пока не отправляли заказов</p>
        <a
          href={`/catalog/${params.secret}`}
          className="mt-3 text-blue-600 text-sm font-medium active:opacity-70"
        >
          Вернуться в каталог
        </a>
        <a
          href={`/catalog/${params.secret}/cart`}
          className="mt-2 text-blue-500 text-sm active:opacity-70"
        >
          Перейти в корзину →
        </a>
      </div>
    );
  }

  /* ---------- заполненный список ---------- */
  return (
    <div className="flex flex-col min-h-[calc(100vh-48px)]">
      {/* Заголовок страницы */}
      <div className="px-4 py-3 border-b border-gray-100 bg-white flex items-center justify-between gap-2">
        <a
          href={`/catalog/${params.secret}/cart`}
          className="text-blue-600 text-sm font-medium active:opacity-70 flex-shrink-0"
        >
          ← Корзина
        </a>
        <h2 className="font-semibold text-gray-900 flex-1 text-center">
          Отправленные заказы
        </h2>
        {/* Кнопка очистки всей истории с подтверждением (D-12) */}
        <button
          onClick={() => {
            if (confirm('Удалить всю историю заказов?')) {
              clearHistory();
            }
          }}
          className="text-xs text-red-500 font-medium active:opacity-70 flex-shrink-0"
        >
          Очистить
        </button>
      </div>

      {/* Список записей — от новых к старым */}
      <div className="flex-1 bg-white">
        {[...entries].reverse().map((entry) => (
          <OrderCard
            key={entry.id}
            entry={entry}
            onRemove={() => {
              if (confirm('Удалить эту запись?')) {
                removeEntry(entry.id);
              }
            }}
          />
        ))}
      </div>

      {/* Итого заказов внизу */}
      <div className="sticky bottom-0 bg-white border-t border-gray-200 px-4 py-3 shadow-[0_-4px_12px_rgba(0,0,0,0.06)]">
        <p className="text-xs text-gray-400 text-center">
          {entries.length} {pluralOrders(entries.length)} в истории
        </p>
      </div>
    </div>
  );
}

/* ---------- Карточка одного заказа ---------- */
function OrderCard({
  entry,
  onRemove,
}: {
  entry: OrderHistoryEntry;
  onRemove: () => void;
}) {
  // Форматируем дату-время в русской локали
  const dateStr = new Date(entry.createdAt).toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  // Подпись канала по типу
  const channelLabel = entry.channel === 'telegram' ? 'Telegram' : 'MAX';

  // Итоговая сумма: если total сохранён в снимке — используем его; иначе считаем из позиций (защита D-14)
  const total =
    typeof entry.total === 'number'
      ? entry.total
      : entry.items.reduce(
          (sum, item) =>
            sum +
            (typeof item.priceAtOrder === 'number' && typeof item.quantity === 'number'
              ? item.priceAtOrder * item.quantity
              : 0),
          0
        );

  return (
    <div className="border-b border-gray-100 px-4 py-3">
      {/* Сводная строка: дата · канал · сумма */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <p className="text-xs text-gray-500">{dateStr}</p>
          <p className="text-xs text-gray-400 mt-0.5">
            {channelLabel} · {entry.items.length} {pluralItems(entry.items.length)}
          </p>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <p className="text-sm font-bold text-gray-900">{total.toFixed(2)} ₽</p>
          {/* Удаление отдельной записи с подтверждением (D-12) */}
          <button
            onClick={onRemove}
            className="text-xs text-red-400 active:opacity-70"
          >
            Удалить
          </button>
        </div>
      </div>

      {/* Список позиций заказа с мини-фото */}
      <div className="flex flex-col gap-2">
        {entry.items.map((item, idx) => (
          <OrderItem key={item.id ?? idx} item={item} />
        ))}
      </div>
    </div>
  );
}

/* ---------- Позиция внутри карточки заказа ---------- */
function OrderItem({ item }: { item: OrderHistoryItem }) {
  // Мягкая деградация (D-14): если у позиции нет name или priceAtOrder — показываем заглушку
  if (!item.name) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex-shrink-0 w-8 h-8 rounded border border-gray-100 bg-gray-50 flex items-center justify-center text-gray-300">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v13.5a1.5 1.5 0 001.5 1.5z" />
          </svg>
        </div>
        <p className="text-xs text-gray-400 italic">— позиция недоступна —</p>
      </div>
    );
  }

  // Сумма по позиции (если priceAtOrder отсутствует — показываем прочерк)
  const lineTotal =
    typeof item.priceAtOrder === 'number' && typeof item.quantity === 'number'
      ? (item.priceAtOrder * item.quantity).toFixed(2)
      : null;

  return (
    <div className="flex items-center gap-2">
      {/* Мини-фото 8×8 с SVG-заглушкой при ошибке (D-10) */}
      <div className="flex-shrink-0 w-8 h-8 rounded overflow-hidden border border-gray-100 bg-white">
        {item.imageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={item.imageUrl}
            alt={item.name}
            className="w-full h-full object-contain"
            loading="lazy"
            decoding="async"
            onError={(e) => {
              // При ошибке загрузки фото — скрываем img, показывается SVG-заглушка ниже
              (e.currentTarget as HTMLImageElement).style.display = 'none';
              const parent = (e.currentTarget as HTMLImageElement).parentElement;
              if (parent) parent.dataset.error = '1';
            }}
          />
        ) : (
          // SVG-заглушка при отсутствии imageUrl
          <div className="w-full h-full flex items-center justify-center text-gray-300">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v13.5a1.5 1.5 0 001.5 1.5z" />
            </svg>
          </div>
        )}
      </div>

      {/* Название и цена позиции */}
      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-800 leading-tight truncate">{item.name}</p>
      </div>
      <div className="flex-shrink-0 text-right">
        <p className="text-xs text-gray-500">×{item.quantity}</p>
        {lineTotal && (
          <p className="text-xs font-medium text-gray-800">{lineTotal} ₽</p>
        )}
      </div>
    </div>
  );
}

/* ---------- Утилиты склонения ---------- */

// Склонение слова «заказ»
function pluralOrders(n: number): string {
  if (n % 10 === 1 && n % 100 !== 11) return 'заказ';
  if ([2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100))
    return 'заказа';
  return 'заказов';
}

// Склонение слова «позиция» (для счётчика в сводке заказа)
function pluralItems(n: number): string {
  if (n % 10 === 1 && n % 100 !== 11) return 'позиция';
  if ([2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100))
    return 'позиции';
  return 'позиций';
}
