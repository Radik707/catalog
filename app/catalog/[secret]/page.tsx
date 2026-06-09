import { notFound } from "next/navigation";
import { getProducts } from "@/lib/sheets";
import CatalogView from "@/components/CatalogView";

// Кэш на 5 минут — данные обновляются раз в день, не нужен постоянный перечитка
export const revalidate = 300;

export default async function CatalogPage({
  params,
  searchParams,
}: {
  params: { secret: string };
  // category убран — навигация теперь через scroll-to-anchor, не через URL
  searchParams: { filter?: string };
}) {
  // Проверка секретной ссылки — не прошёл, показываем 404
  if (params.secret !== process.env.CATALOG_SECRET) {
    notFound();
  }

  const allProducts = await getProducts();

  // Фильтр по бейджу для вкладок «Хит» и «Новинка» в шапке
  let products = allProducts;
  if (searchParams.filter === "hit") {
    products = allProducts.filter((p) => p.badge === "хит");
  } else if (searchParams.filter === "new") {
    products = allProducts.filter((p) => p.badge === "новинка");
  }

  // Флаг активного фильтра — переключает витрину в плоский список (D-06)
  const isFiltered =
    searchParams.filter === "hit" || searchParams.filter === "new";

  // initialCategory убран — групп-фильтр заменён якорной навигацией
  return <CatalogView products={products} isFiltered={isFiltered} />;
}
