// Утилита умной предзагрузки фото каталога.
// Вызывается после успешной синхронизации данных (useCatalogSync.ts).
// Стратегия D-04: diff нового и прошлого списка ссылок → prefetch только новых.
// Первая синхронизация (prevImageUrls пуст) — НЕ качаем всё (~900 фото),
// кэш заполняется лениво по мере просмотра товаров (анти-паттерн №1).

"use client";

import type { Product } from "@/lib/types";
import { getMeta, saveMeta } from "@/lib/catalogDb";

/**
 * Синхронизирует кэш фото: докачивает только новые URL (diff против предыдущего списка).
 * SW перехватит prefetch-запросы и положит фото в CacheFirst "cloudinary-images".
 *
 * @param products — свежий список товаров из /api/products
 */
export async function syncPhotos(products: Product[]): Promise<void> {
  // Собираем актуальные ссылки на фото — отсекаем товары без imageUrl (Boolean-фильтр)
  const newUrls = products
    .map((p) => p.imageUrl)
    .filter((u): u is string => Boolean(u));

  // Читаем предыдущий список из meta-хранилища IDB (ключ зарезервирован на этапе 11)
  const prevUrls = (await getMeta<string[]>("prevImageUrls")) ?? [];

  // D-04: при ПЕРВОЙ синхронизации (prevUrls пуст) — НЕ качаем все ~900 фото.
  // Взрыв квоты iOS, долгая первая загрузка — анти-паттерн №1.
  // Кэш наполнится сам, лениво, когда агент просматривает товары (CacheFirst on-demand).
  if (prevUrls.length > 0) {
    // Используем Set для O(1) проверки вхождения (не Array.includes в цикле)
    const prevSet = new Set(prevUrls);

    // Отбираем только те URL, которых не было в прошлом списке
    const toFetch = newUrls.filter((url) => !prevSet.has(url));

    // Огонь-и-забыл: SW перехватит запрос и положит фото в кэш (CacheFirst).
    // URL — сырой product.imageUrl (подход 1: совпадает с unoptimized в ProductCard
    // и с matcher SW /^https:\/\/res\.cloudinary\.com\//).
    // Ошибки молча — как везде в офлайн-слое (D-04 этапа 11).
    for (const url of toFetch) {
      fetch(url).catch(() => {});
    }
  }

  // После любой синхронизации сохраняем текущий список для следующего diff
  await saveMeta("prevImageUrls", newUrls);
}
