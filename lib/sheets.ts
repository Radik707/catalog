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

  const res = await fetch(url, { next: { revalidate: 300 } }); // кеш 5 минут (ISR)

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
