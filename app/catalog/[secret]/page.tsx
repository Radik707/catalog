import { notFound } from "next/navigation";
import { getProducts } from "@/lib/sheets";
import CatalogView from "@/components/CatalogView";

export const revalidate = 300;

export default async function CatalogPage({
  params,
  searchParams,
}: {
  params: { secret: string };
  searchParams: { filter?: string; category?: string };
}) {
  if (params.secret !== process.env.CATALOG_SECRET) {
    notFound();
  }

  const allProducts = await getProducts();

  let products = allProducts;
  if (searchParams.filter === "hit") {
    products = allProducts.filter((p) => p.badge === "хит");
  } else if (searchParams.filter === "new") {
    products = allProducts.filter((p) => p.badge === "новинка");
  }

  return <CatalogView products={products} initialCategory={searchParams.category ?? ""} />;
}
