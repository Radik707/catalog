import { notFound } from "next/navigation";
import { getProducts } from "@/lib/sheets";
import CatalogView from "@/components/CatalogView";

export const revalidate = 300;

export default async function CatalogPage({
  params,
}: {
  params: { secret: string };
}) {
  if (params.secret !== process.env.CATALOG_SECRET) {
    notFound();
  }

  const products = await getProducts();
  return <CatalogView products={products} />;
}
