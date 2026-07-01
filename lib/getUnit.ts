// Единица счёта товара (D-06).
//
// Этап 21 — обёртка над getPackaging(): возвращает подпись единицы как есть
// («за шт» / «за блок» / «за коробку» / «за кг» / … / "" если правила нет).
//
// Этап 21b — сюда добавится приоритет ручной правки из админ-панели;
// getPackaging() останется значением по умолчанию.
// Быстрый набор при этом повторно не трогаем.
//
// Это единственная точка «шва»: весь фронт должен читать единицу товара
// ТОЛЬКО через getUnit, не через getPackaging напрямую (D-06).

import { Product } from "./types";
import { getPackaging } from "./packaging";

export function getUnit(product: Product): string {
  return getPackaging(product.group, product.name);
}
