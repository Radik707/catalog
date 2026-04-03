import { Product } from "../../lib/types";

const SHEETS_ID = process.env.GOOGLE_SHEETS_ID;
const API_KEY = process.env.GOOGLE_API_KEY;

const CACHE_TTL_MS = 15 * 60 * 1000; // 15 минут

let cachedProducts: Product[] = [];
let cacheTimestamp = 0;

export async function getProducts(): Promise<Product[]> {
  const now = Date.now();
  if (cachedProducts.length > 0 && now - cacheTimestamp < CACHE_TTL_MS) {
    return cachedProducts;
  }

  if (!SHEETS_ID || !API_KEY) {
    console.error("Не заданы GOOGLE_SHEETS_ID или GOOGLE_API_KEY");
    return cachedProducts;
  }

  try {
    const range = encodeURIComponent("Товары!A2:I");
    const url = `https://sheets.googleapis.com/v4/spreadsheets/${SHEETS_ID}/values/${range}?key=${API_KEY}`;
    const res = await fetch(url, { cache: "no-store" });

    if (!res.ok) {
      console.error("Ошибка Google Sheets API:", res.status);
      return cachedProducts;
    }

    const data = await res.json();
    const rows: string[][] = data.values || [];

    const products: Product[] = rows
      .map((row, index) => ({
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
      }))
      .filter((p) => p.stock > 1 && p.name); // скрываем остаток ≤ 1

    cachedProducts = products;
    cacheTimestamp = now;
    return products;
  } catch (err) {
    console.error("Ошибка получения товаров:", err);
    return cachedProducts;
  }
}

export async function getCategories(): Promise<string[]> {
  const products = await getProducts();
  const groups = new Set(products.map((p) => p.group).filter(Boolean));
  return Array.from(groups).sort();
}

export async function getProductsByCategory(category: string): Promise<Product[]> {
  const products = await getProducts();
  return products.filter((p) => p.group === category);
}

export async function searchProducts(query: string): Promise<Product[]> {
  const products = await getProducts();
  const q = query.toLowerCase();
  return products.filter(
    (p) =>
      p.name.toLowerCase().includes(q) ||
      p.category.toLowerCase().includes(q) ||
      p.group.toLowerCase().includes(q) ||
      (p.description?.toLowerCase().includes(q) ?? false)
  );
}
