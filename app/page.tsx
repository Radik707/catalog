import { getProducts } from "@/lib/sheets";
import CatalogView from "@/components/CatalogView";

export const revalidate = 300; // ISR: обновлять каждые 5 минут

export default async function Home() {
  const products = await getProducts();
  return <CatalogView products={products} />;
}
