'use client';

// Страница «Отправленные заказы» — история отправленных через Telegram/MAX заказов.
// Данные хранятся в localStorage устройства (HIST-02, офлайн-совместимость).
// Не содержит слов «статус», «принято», «в доставке» — это история отправки, не статус поставщика (HIST-03, инвариант v1.4).

// ЭТАП 19 (план 02): добавлена кнопка «Повторить» на каждую карточку + сводка результата (D-06, D-07).
// Логика повтора — classifyReorder (lib/reorder.ts, план 19-01); корзина — addToCartWithQuantity.

import { useState, useCallback } from 'react';
// Через общий провайдер истории — единое состояние с кнопками отправки в корзине (CR-01)
import { useOrderHistoryContext } from '@/components/OrderHistoryProvider';
// Актуальный каталог из IndexedDB — офлайн-безопасно (D-09)
import { useCatalogSyncContext } from '@/components/CatalogSyncProvider';
// Форма цен — +5% Ефимовой через priceForm (D-03)
import { useCatalogSettings } from '@/components/CatalogSettings';
// Добавление в корзину с заданным количеством (D-05, план 19-01)
import { useCartContext } from '@/components/CartProvider';
// Чистый хелпер классификации позиций повтора (план 19-01)
import { classifyReorder, ReorderResult } from '@/lib/reorder';
import type { OrderHistoryEntry, OrderHistoryItem } from '@/lib/types';

export default function OrdersPage({ params }: { params: { secret: string } }) {
  const { entries, isLoaded, removeEntry, clearHistory } = useOrderHistoryContext();
  // Актуальный каталог из IDB — без новых сетевых вызовов (D-09)
  const { products } = useCatalogSyncContext();
  // Форма цен для расчёта актуальной цены (D-03)
  const { priceForm } = useCatalogSettings();
  // Метод добавления с количеством (D-05)
  const { addToCartWithQuantity } = useCartContext();

  // Сводка результата повтора: null — не показана; заполнена после нажатия «Повторить»
  const [reorderSummary, setReorderSummary] = useState<(ReorderResult & { secret: string }) | null>(null);

  // Обработчик кнопки «Повторить» — вызывается из OrderCard
  const handleRepeat = useCallback(
    (entry: OrderHistoryEntry) => {
      // Классифицируем позиции прошлого заказа против актуального каталога (D-01..D-04)
      const result = classifyReorder(entry.items, products, priceForm);

      // Добавляем в корзину позиции с исходом added и price_changed (D-06)
      for (const line of result.lines) {
        if ((line.outcome === 'added' || line.outcome === 'price_changed') && line.product) {
          addToCartWithQuantity(line.product, line.historyItem.quantity);
        }
      }

      // Открываем сводку результата (D-07)
      setReorderSummary({ ...result, secret: params.secret });
    },
    [products, priceForm, addToCartWithQuantity, params.secret],
  );

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
    <>
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
              onRepeat={handleRepeat}
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

      {/* Модалка сводки повтора (D-07) — рендерится поверх, когда reorderSummary != null */}
      {reorderSummary && (
        <ReorderSummaryModal
          result={reorderSummary}
          secret={reorderSummary.secret}
          onClose={() => setReorderSummary(null)}
        />
      )}
    </>
  );
}

/* ---------- Карточка одного заказа ---------- */
function OrderCard({
  entry,
  onRemove,
  onRepeat,
}: {
  entry: OrderHistoryEntry;
  onRemove: () => void;
  onRepeat: (entry: OrderHistoryEntry) => void;
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

      {/* Кнопка «Повторить» — D-06: повтор заказа в один тап */}
      <div className="mt-3">
        <button
          onClick={() => onRepeat(entry)}
          className="w-full py-2 bg-blue-600 text-white text-sm font-semibold rounded-xl active:bg-blue-700 transition-colors"
        >
          Повторить заказ
        </button>
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

/* ---------- Модалка сводки результата повтора (D-07) ---------- */
// Показывает: сколько добавлено + список пропущенных/изменённых с причиной.
// Кнопка «Перейти в корзину →» — только если addedCount > 0.
// Если добавить нечего — честное сообщение без кнопки перехода (D-07).
function ReorderSummaryModal({
  result,
  secret,
  onClose,
}: {
  result: ReorderResult;
  secret: string;
  onClose: () => void;
}) {
  const { lines, addedCount } = result;

  // Позиции, которые нужно показать в сводке (пропущенные/изменённые)
  // Показываем price_changed (добавлены, но цена изменилась) и пропущенные (out_of_stock, unavailable)
  const notableLines = lines.filter(
    (l) => l.outcome === 'price_changed' || l.outcome === 'out_of_stock' || l.outcome === 'unavailable',
  );

  return (
    /* Тёмная подложка — тап по ней закрывает модалку */
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40"
      onClick={onClose}
    >
      {/* Сама панель — прикреплена снизу; учитывает safe-area и нижние табы клиента */}
      <div
        className="w-full bg-white rounded-t-2xl shadow-2xl pb-safe max-h-[80vh] overflow-y-auto"
        style={{ paddingBottom: 'calc(env(safe-area-inset-bottom, 0px) + 5rem)' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Шапка панели */}
        <div className="flex items-center justify-between px-4 pt-4 pb-3 border-b border-gray-100">
          <h3 className="font-semibold text-gray-900 text-base">Результат повтора</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 active:opacity-70 p-1"
            aria-label="Закрыть"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="px-4 py-4 flex flex-col gap-4">
          {/* Итог: сколько добавлено */}
          {addedCount > 0 ? (
            <div className="flex items-center gap-2">
              {/* Зелёная галочка */}
              <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
              <p className="text-sm font-semibold text-gray-900">
                Добавлено {addedCount} {pluralGoods(addedCount)} в корзину
              </p>
            </div>
          ) : (
            /* Честное сообщение, если добавить нечего (D-07) */
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-amber-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
              </svg>
              <p className="text-sm font-semibold text-gray-700">
                Ни одного товара из заказа сейчас нельзя добавить
              </p>
            </div>
          )}

          {/* Список позиций с нотабельными исходами (price_changed / out_of_stock / unavailable) */}
          {notableLines.length > 0 && (
            <div className="flex flex-col gap-2">
              {notableLines.map((line, idx) => (
                <div key={line.historyItem.id ?? idx} className="flex items-start gap-2">
                  {/* Иконка исхода */}
                  <div className="flex-shrink-0 mt-0.5">
                    {line.outcome === 'price_changed' && (
                      // Синяя информационная иконка — добавлено, но цена изменилась
                      <svg className="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
                      </svg>
                    )}
                    {line.outcome === 'out_of_stock' && (
                      // Серая иконка — нет в наличии
                      <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                      </svg>
                    )}
                    {line.outcome === 'unavailable' && (
                      // Красная иконка — товар недоступен
                      <svg className="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    )}
                  </div>

                  {/* Описание исхода */}
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-gray-800 leading-snug font-medium truncate">
                      {line.historyItem.name}
                    </p>
                    <p className="text-xs text-gray-500 leading-snug mt-0.5">
                      {line.outcome === 'price_changed' && line.currentPrice !== undefined && (
                        // Добавлен в корзину, но цена изменилась — показываем было/стало
                        <>
                          добавлен · цена изменилась:{' '}
                          <span className="line-through text-gray-400">{line.oldPrice.toFixed(2)} ₽</span>
                          {' → '}
                          <span className="font-medium text-blue-600">{line.currentPrice.toFixed(2)} ₽</span>
                        </>
                      )}
                      {line.outcome === 'out_of_stock' && 'нет в наличии'}
                      {line.outcome === 'unavailable' && 'товар больше недоступен'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Кнопка перехода в корзину — только если что-то добавлено (D-07) */}
          {addedCount > 0 && (
            <a
              href={`/catalog/${secret}/cart`}
              className="block w-full py-3 text-center bg-blue-600 text-white text-sm font-semibold rounded-xl active:bg-blue-700 transition-colors"
            >
              Перейти в корзину →
            </a>
          )}

          {/* Кнопка закрытия */}
          <button
            onClick={onClose}
            className="block w-full py-2.5 text-center text-sm text-gray-500 font-medium active:opacity-70"
          >
            Закрыть
          </button>
        </div>
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

// Склонение слова «товар» (для сводки повтора — «добавлено N товаров»)
function pluralGoods(n: number): string {
  if (n % 10 === 1 && n % 100 !== 11) return 'товар';
  if ([2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100))
    return 'товара';
  return 'товаров';
}
