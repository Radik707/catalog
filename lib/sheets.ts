import { Product } from "./types";

const SHEETS_ID = process.env.GOOGLE_SHEETS_ID;
const API_KEY = process.env.GOOGLE_API_KEY;

/**
 * Получить все товары из Google Sheet.
 * Лист "Товары", колонки: Наименование | Цена | Остаток | Категория | Группа | Поставщик | Badge | ImageUrl | Description
 */
export async function getProducts(): Promise<Product[]> {
  if (!SHEETS_ID || !API_KEY) {
    console.error("Не заданы GOOGLE_SHEETS_ID или GOOGLE_API_KEY в .env.local");
    return [];
  }

  const range = encodeURIComponent("Товары!A2:I");
  const url = `https://sheets.googleapis.com/v4/spreadsheets/${SHEETS_ID}/values/${range}?key=${API_KEY}`;

  const res = await fetch(url, { next: { revalidate: 300 } }); // кеш 5 минут (ISR)

  if (!res.ok) {
    console.error("Ошибка Google Sheets API:", res.status, await res.text());
    return [];
  }

  const data = await res.json();
  const rows: string[][] = data.values || [];

  return rows.map((row, index) => ({
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
  }));
}
