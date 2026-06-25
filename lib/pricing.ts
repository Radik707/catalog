import { Product } from "./types";

// Форма цен каталога:
//   "2" — базовые цены как в Google Sheet (по умолчанию);
//   "1" — на товары поставщика «Ефимова» наценка +5% (×1.05), остальные без изменений.
export type PriceForm = "1" | "2";

// Поставщик хранится как имя загруженного файла прайса. Оператор называет файлы
// сокращённо одной буквой: Ефимова → «е(2).xlsx», Лазуткина → «л…», Пелих → «п…».
// Иногда встречается и полное имя «Ефимова.xlsx». Поэтому «Ефимова» = имя файла,
// которое начинается с буквы «е» (кириллица или латиница) ИЛИ содержит «ефим».
// Лазуткина («л…») и Пелих («п…») под это не подпадают.
export function isEfimova(supplier?: string): boolean {
  if (!supplier) return false;
  const s = supplier.trim().toLowerCase();
  return /ефим/.test(s) || s.startsWith("е") || s.startsWith("e");
}

// Эффективная цена с учётом выбранной формы.
// Округляем до 2 знаков, чтобы не плодить длинные дроби после ×1.05.
export function effectivePrice(product: Product, form: PriceForm): number {
  if (form === "1" && isEfimova(product.supplier)) {
    return Math.round(product.price * 1.05 * 100) / 100;
  }
  return product.price;
}
