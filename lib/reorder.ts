// Ядро механики «Повторить заказ» (этап 19, план 01).
// Чистая функция без побочных эффектов — только аргументы → результат.
// Не читает localStorage/DOM; переиспользуется на «Главной» (этап 20).

import { Product, OrderHistoryItem } from './types';
import { PriceForm, effectivePrice } from './pricing';

// ─── Типы исходов классификации ────────────────────────────────────────────

/**
 * Четыре честных исхода для позиции повторяемого заказа (D-04):
 *   added          — найдена, в наличии, цена не изменилась (добавляем молча)
 *   price_changed  — найдена, в наличии, цена изменилась (добавляем, помечаем)
 *   out_of_stock   — найдена, но нет в наличии (НЕ добавляем)
 *   unavailable    — не найдена в каталоге (НЕ добавляем)
 */
export type ReorderOutcome = 'added' | 'price_changed' | 'out_of_stock' | 'unavailable';

/** Результат классификации одной позиции прошлого заказа. */
export interface ReorderLineResult {
  /** Исход классификации (один из четырёх). */
  outcome: ReorderOutcome;
  /** Исходная позиция из истории заказа. */
  historyItem: OrderHistoryItem;
  /**
   * Текущий товар из каталога (если найден по id или имени).
   * undefined — при исходе unavailable.
   */
  product?: Product;
  /**
   * Актуальная эффективная цена из effectivePrice (учитывает +5% Ефимовой).
   * undefined — при исходе unavailable.
   */
  currentPrice?: number;
  /** Замороженная цена из истории — только для сравнения «было → стало». */
  oldPrice: number;
  /**
   * Запрошенное количество из истории заказа (WR-04).
   * Заполняется только для добавляемых исходов (added / price_changed).
   */
  requestedQty?: number;
  /**
   * Фактически добавленное количество с учётом капа по текущему остатку (WR-04).
   * Совпадает с requestedQty, когда остатка хватает; меньше — когда был усечён.
   * Заполняется только для добавляемых исходов (added / price_changed).
   */
  addedQty?: number;
  /**
   * true — количество было урезано остатком (addedQty < requestedQty), WR-04.
   * Модалка сводки показывает по этому флагу «добавлено N из M — ограничено остатком».
   */
  capped?: boolean;
}

/** Агрегированный результат повтора всего заказа. */
export interface ReorderResult {
  /** Классификация каждой позиции в том же порядке, что и historyItems. */
  lines: ReorderLineResult[];
  /**
   * Число позиций, которые будут добавлены в корзину
   * (исходы: added + price_changed).
   */
  addedCount: number;
}

// ─── Вспомогательные функции ───────────────────────────────────────────────

/**
 * Нормализует название товара для фолбэк-матчинга по имени (D-02):
 *   - trim
 *   - toLowerCase
 *   - схлопывание любых последовательностей пробельных символов в один пробел
 */
function normalizeName(name: string): string {
  return name.trim().toLowerCase().replace(/\s+/g, ' ');
}

/**
 * Округляет цену до 2 знаков для точного сравнения «было → стало».
 * Устраняет погрешности float при ×1.05.
 */
function roundPrice(price: number): number {
  return Math.round(price * 100) / 100;
}

// ─── Основная функция классификации ───────────────────────────────────────

/**
 * classifyReorder — чистая функция классификации позиций прошлого заказа
 * против актуального каталога (D-01..D-04).
 *
 * @param historyItems  Позиции из снимка прошлого заказа (OrderHistoryItem[])
 * @param catalog       Текущий список товаров (Product[]) из IndexedDB/витрины
 * @param priceForm     Выбранная форма цен ("1" = с надбавкой Ефимовой, "2" = базовая)
 * @returns ReorderResult — классифицированные строки + счётчик добавляемых позиций
 */
export function classifyReorder(
  historyItems: OrderHistoryItem[],
  catalog: Product[],
  priceForm: PriceForm,
): ReorderResult {
  // Строим индекс каталога по id для O(1) матчинга (D-02, шаг 1)
  const catalogById = new Map<string, Product>(catalog.map((p) => [p.id, p]));

  // Строим индекс каталога по нормализованному имени для фолбэк-матчинга (D-02, шаг 2).
  // WR-02: храним МАССИВ кандидатов на каждое имя, а не один товар. Если в каталоге
  // два товара с одинаковым нормализованным именем (разные поставщики/фасовки), Map<…,Product>
  // молча оставлял бы только последний и мог подставить чужой SKU. Фолбэк по имени применяем
  // только при единственном кандидате (см. ниже) — при коллизии честнее оставить unavailable.
  const catalogByName = new Map<string, Product[]>();
  for (const p of catalog) {
    const key = normalizeName(p.name);
    const arr = catalogByName.get(key);
    if (arr) {
      arr.push(p);
    } else {
      catalogByName.set(key, [p]);
    }
  }

  let addedCount = 0;

  const lines: ReorderLineResult[] = historyItems.map((historyItem) => {
    // Нормализуем замороженную цену на входе (WR-01): в старых/повреждённых
    // записях localStorage priceAtOrder может быть undefined/строкой/NaN.
    // Остальной экран истории уже обороняется через typeof === 'number' —
    // здесь делаем то же, иначе roundPrice(undefined) → NaN (ложный
    // price_changed), а oldPrice.toFixed() в модалке сводки бросает TypeError.
    const oldPrice =
      typeof historyItem.priceAtOrder === 'number' && Number.isFinite(historyItem.priceAtOrder)
        ? historyItem.priceAtOrder
        : 0;

    // ── Шаг 1: матчинг по id (основной путь) ──────────────────────────────
    let matched: Product | undefined = catalogById.get(historyItem.id);

    // ── Шаг 2: фолбэк по нормализованному имени, если по id не нашли ──────
    // WR-02: матчим только при ЕДИНСТВЕННОМ кандидате с таким именем. Если имя
    // неоднозначно (несколько товаров) — не угадываем, оставляем unavailable.
    if (!matched) {
      const candidates = catalogByName.get(normalizeName(historyItem.name));
      if (candidates && candidates.length === 1) {
        matched = candidates[0];
      }
    }

    // ── Исход: не найдено ни по id, ни по имени → unavailable (D-02) ──────
    if (!matched) {
      return {
        outcome: 'unavailable',
        historyItem,
        oldPrice,
      } satisfies ReorderLineResult;
    }

    // Актуальная эффективная цена (учитывает форму Ефимовой через +5%, D-03)
    const currentPrice = effectivePrice(matched, priceForm);

    // ── Исход: товар есть, но остаток ≤ 1 → out_of_stock (D-04) ──────────
    // Порог тот же, что скрытие товаров на витрине каталога (stock <= 1).
    if (matched.stock <= 1) {
      return {
        outcome: 'out_of_stock',
        historyItem,
        product: matched,
        currentPrice, // вычисляем всё равно — может потребоваться UI для показа
        oldPrice,
      } satisfies ReorderLineResult;
    }

    // ── Исход: найден, в наличии — определяем изменилась ли цена (D-04) ───
    const priceChanged = roundPrice(currentPrice) !== roundPrice(oldPrice);
    const outcome: ReorderOutcome = priceChanged ? 'price_changed' : 'added';

    // Позиции added и price_changed попадают в корзину → учитываем счётчик
    addedCount++;

    // WR-04: вычисляем фактически добавляемое количество с капом по остатку —
    // тем же правилом, что addToCartWithQuantity для НОВОЙ позиции (Math.min(qty, stock)).
    // requestedQty нормализуем: в повреждённой истории quantity может быть не числом.
    const requestedQty =
      typeof historyItem.quantity === 'number' && Number.isFinite(historyItem.quantity)
        ? historyItem.quantity
        : 0;
    const addedQty = Math.min(requestedQty, matched.stock);
    const capped = addedQty < requestedQty;

    return {
      outcome,
      historyItem,
      product: matched,
      currentPrice,
      oldPrice,
      requestedQty,
      addedQty,
      capped,
    } satisfies ReorderLineResult;
  });

  return { lines, addedCount };
}
