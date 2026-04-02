export interface Product {
  id: string;
  name: string;
  price: number;
  stock: number;
  category: string;
  group: string;
  supplier: string;
  badge?: string;
  imageUrl?: string;
  description?: string;
}
