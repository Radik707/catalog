export interface Product {
  id: string;
  name: string;
  price: number;
  stock: number;
  category: string;
  group: string;
  supplier: string;
  badge?: string;        // колонка G — бейдж (хит / новинка / акция)
  imageUrl?: string;     // колонка H — URL фото в Cloudinary
  description?: string;  // колонка I — описание товара
  subgroup?: string;     // колонка J — «Подгруппа» (двухуровневая навигация)
  section?: string;      // колонка K — «Раздел» (верхний уровень навигации)
  hidden?: boolean;      // колонка L — «Скрыт» (1 = скрыт с витрины)
}

// Снимок позиции заказа в момент отправки (для истории заказов).
// id товара сохраняется как задел под «Повторить заказ» (v1.5, D-09).
// Не хранит полный Product — только поля, нужные для показа истории (D-07).
export interface OrderHistoryItem {
  id: string;            // id товара (Product.id) — задел под «Повторить заказ» (D-09)
  name: string;          // название на момент заказа
  quantity: number;
  priceAtOrder: number;  // эффективная цена, которую видел клиент: effectivePrice(product, priceForm) (D-08)
  unit: string;          // единица измерения
  imageUrl?: string;     // для мини-фото в списке истории; работает офлайн через кэш (D-10)
}

// Запись истории — один отправленный заказ.
// Не содержит полей статуса/доставки — только «что я отправил» (HIST-03, инвариант v1.4).
export interface OrderHistoryEntry {
  id: string;                     // уникальный id записи (crypto.randomUUID() или Date.now().toString())
  items: OrderHistoryItem[];
  total: number;                  // сумма по priceAtOrder × quantity (D-11)
  createdAt: string;              // ISO-строка (new Date().toISOString()) (D-11)
  channel: 'telegram' | 'max';   // канал отправки — по нажатой кнопке (D-02, D-11)
}
