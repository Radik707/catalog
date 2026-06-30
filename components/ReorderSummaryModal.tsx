'use client';

// Общая модалка-сводка результата повтора заказа (этап 19, план 02; вынесена в этапе 20, план 02).
// Используется в «Мои заказы» (orders/page.tsx) и строке повтора (этап 20, план 03).
// Bottom-sheet, прикреплена снизу; safe-area + 5rem резерв под нижние табы клиента (D-07).
// Цвета иконок исходов зафиксированы UI-SPEC (§Color) — не менять.

import { ReorderResult } from '@/lib/reorder';
import { pluralGoods } from '@/lib/plural';

// Пропсы: результат повтора, секрет для ссылки в корзину, обработчик закрытия
export default function ReorderSummaryModal({
  result,
  secret,
  onClose,
}: {
  result: ReorderResult;
  secret: string;
  onClose: () => void;
}) {
  const { lines, addedCount } = result;

  // Позиции, которые нужно показать в сводке (пропущенные/изменённые/усечённые)
  // Показываем price_changed (добавлены, но цена изменилась), пропущенные (out_of_stock,
  // unavailable) и усечённые по остатку (capped) — WR-04: молчаливое урезание объёма
  // теперь честно отображается («добавлено N из M — ограничено остатком»).
  const notableLines = lines.filter(
    (l) =>
      l.outcome === 'price_changed' ||
      l.outcome === 'out_of_stock' ||
      l.outcome === 'unavailable' ||
      l.capped,
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

          {/* Список позиций с нотабельными исходами (price_changed / out_of_stock / unavailable / усечённые по остатку) */}
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
                    {/* WR-04: товар добавлен без смены цены, но усечён по остатку —
                        своя янтарная иконка, чтобы строка не осталась без значка */}
                    {line.capped && line.outcome === 'added' && (
                      <svg className="w-4 h-4 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
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
                          <span className="line-through text-gray-400">{(line.oldPrice ?? 0).toFixed(2)} ₽</span>
                          {' → '}
                          <span className="font-medium text-blue-600">{line.currentPrice.toFixed(2)} ₽</span>
                        </>
                      )}
                      {line.outcome === 'out_of_stock' && 'нет в наличии'}
                      {line.outcome === 'unavailable' && 'товар больше недоступен'}
                      {/* WR-04: усечение по остатку для строки added (без смены цены) */}
                      {line.capped && line.outcome === 'added' && (
                        <span className="text-amber-600 font-medium">
                          добавлено {line.addedQty} из {line.requestedQty} — ограничено остатком
                        </span>
                      )}
                      {/* WR-04: усечение для строки с изменённой ценой — отдельной строкой ниже */}
                      {line.capped && line.outcome === 'price_changed' && (
                        <span className="block text-amber-600 font-medium mt-0.5">
                          добавлено {line.addedQty} из {line.requestedQty} — ограничено остатком
                        </span>
                      )}
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
