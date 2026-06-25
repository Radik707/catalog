import { Product } from "./types";
import { getCategoryIndex, PRODUCT_CATEGORY_OVERRIDES } from "./structure";

const SHEETS_ID = process.env.GOOGLE_SHEETS_ID;
const API_KEY = process.env.GOOGLE_API_KEY;

/**
 * Получить все товары из Google Sheet.
 * Лист "Товары", колонки: Наименование | Цена | Остаток | Категория | Группа | Поставщик | Badge | ImageUrl | Description | Подгруппа | Раздел
 */
export async function getProducts(): Promise<Product[]> {
  if (!SHEETS_ID || !API_KEY) {
    console.error("Не заданы GOOGLE_SHEETS_ID или GOOGLE_API_KEY в .env.local");
    return [];
  }

  // Диапазон расширен до A2:L для чтения колонок «Подгруппа» (J), «Раздел» (K) и «Скрыт» (L)
  const range = encodeURIComponent("Товары!A2:L");
  const url = `https://sheets.googleapis.com/v4/spreadsheets/${SHEETS_ID}/values/${range}?key=${API_KEY}`;

  // Без кэша: изменения из админ-панели («Применить сейчас» — скрытие, фото, перенос)
  // должны отражаться на витрине сразу, а не через 5 минут. Трафик B2B небольшой —
  // постоянное чтение Google Sheets при заходе допустимо.
  const res = await fetch(url, { cache: "no-store" });

  if (!res.ok) {
    console.error("Ошибка Google Sheets API:", res.status, await res.text());
    return [];
  }

  const data = await res.json();
  const rows: string[][] = data.values || [];

  const products: Product[] = rows.map((row, index) => ({
    id: String(index + 1),
    name: row[0] || "",
    price: parseFloat(row[1]) || 0,
    stock: parseInt(row[2]) || 0,
    category: row[3] || "",
    group: row[4] || "",
    supplier: row[5] || "",
    badge: row[6] || undefined,
    imageUrl: row[7] || undefined,
    description: row[8] || undefined,
    subgroup: row[9] || undefined, // J — «Подгруппа»
    section: row[10] || undefined, // K — «Раздел»
    hidden: row[11] === "1",       // L — «Скрыт» (строго "1" = скрыт; undefined/иное = виден)
  }));

  // Запасной механизм: пока в таблице нет колонки «Раздел» (у всех товаров пусто),
  // выводим раздел/подгруппу из structure_map.json по категории и сортируем по
  // структуре — так же, как это делает upload.py. Когда боевая перезаливка
  // заполнит колонки J/K, этот блок сам отключится (раздел перестанет быть пустым).
  const idx = getCategoryIndex();
  if (idx.size > 0 && products.every((p) => !p.section)) {
    // Точечные правки ошибочной категории отдельных товаров (до раскладки)
    for (const p of products) {
      for (const ov of PRODUCT_CATEGORY_OVERRIDES) {
        if (p.name.includes(ov.match)) {
          p.category = ov.category;
          break;
        }
      }
    }

    const FALLBACK = {
      section: "Прочее",
      subgroup: "Прочее",
      sort: [9999, 9999, 9999] as [number, number, number],
    };
    const sortKey = new Map<string, [number, number, number]>();
    for (const p of products) {
      const e = idx.get(p.category) ?? FALLBACK;
      p.section = e.section;
      p.subgroup = e.subgroup;
      sortKey.set(p.id, e.sort);
    }
    products.sort((a, b) => {
      const sa = sortKey.get(a.id)!;
      const sb = sortKey.get(b.id)!;
      return sa[0] - sb[0] || sa[1] - sb[1] || sa[2] - sb[2];
    });
  }

  // Фильтрация скрытых товаров на сервере (HIDE-05):
  // скрытые не попадают в ответ /api/products и не отправляются в браузер.
  // Применяется ПОСЛЕ fallback-блока восстановления section и сортировки.
  return products.filter((p) => !p.hidden);
}

/**
 * Прочитать настройки сайта из вкладки «Настройки» (колонки A=ключ, B=значение).
 * Управляются из админ-панели (раздел «Оформление»). Пример ключа: price_color.
 * Graceful: при отсутствии вкладки / ошибке / отсутствии ключей → пустой объект {}.
 */
export async function getSiteSettings(): Promise<Record<string, string>> {
  if (!SHEETS_ID || !API_KEY) return {};
  const range = encodeURIComponent("Настройки!A2:B");
  const url = `https://sheets.googleapis.com/v4/spreadsheets/${SHEETS_ID}/values/${range}?key=${API_KEY}`;
  try {
    // no-store: смена настройки в админке должна отражаться на витрине сразу
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return {}; // вкладки «Настройки» может ещё не быть — это норма
    const data = await res.json();
    const rows: string[][] = data.values || [];
    const out: Record<string, string> = {};
    for (const r of rows) {
      if (r[0]) out[String(r[0]).trim()] = (r[1] ?? "").toString().trim();
    }
    return out;
  } catch {
    return {};
  }
}
