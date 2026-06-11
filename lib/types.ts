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
