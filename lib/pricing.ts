import { Product } from "./types";

// Форма цен каталога:
//   "2" — базовые цены как в Google Sheet (по умолчанию);
//   "1" — на товары поставщика «Ефимова» наценка +5% (×1.05), остальные без изменений.
export type PriceForm = "1" | "2";

// Поставщик хранится как имя файла прайса, напр. «Ефимова.xlsx».
// Сравнение регистронезависимое по подстроке «ефим» — устойчиво к «Ефимова», «ефимова» и т.п.
export function isEfimova(supplier?: string): boolean {
  return !!supplier && /ефим/i.test(supplier);
}

// Эффективная цена с учётом выбранной формы.
// Округляем до 2 знаков, чтобы не плодить длинные дроби после ×1.05.
export function effectivePrice(product: Product, form: PriceForm): number {
  if (form === "1" && isEfimova(product.supplier)) {
    return Math.round(product.price * 1.05 * 100) / 100;
  }
  return product.price;
}
