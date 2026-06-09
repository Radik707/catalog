import { notFound } from "next/navigation";
import { getProducts } from "@/lib/sheets";
import CatalogView from "@/components/CatalogView";
import { NavMode } from "@/components/NavProvider";

// Кэш на 5 минут — данные обновляются раз в день, не нужен постоянный перечитка
export const revalidate = 300;

export default async function CatalogPage({
  params,
  searchParams,
}: {
  params: { secret: string };
  searchParams: { filter?: string };
}) {
  // Проверка секретной ссылки — не прошёл, показываем 404
  if (params.secret !== process.env.CATALOG_SECRET) {
    notFound();
  }

  const products = await getProducts();

  // Начальный режим из ссылки ?filter=hit|new (для внешних ссылок); по умолчанию — каталог
  const initialMode: NavMode =
    searchParams.filter === "hit"
      ? "hit"
      : searchParams.filter === "new"
      ? "new"
      : "catalog";

  return <CatalogView products={products} initialMode={initialMode} />;
}
