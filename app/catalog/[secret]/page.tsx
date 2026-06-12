import { notFound } from "next/navigation";
import CatalogView from "@/components/CatalogView";
import { NavMode } from "@/components/NavProvider";

// Динамический рендер без кэша: изменения из админ-панели («Применить сейчас» —
// скрытие глазиком, смена фото, перенос) появляются на витрине сразу, без задержки.
// Данные каталога больше НЕ прокидываются с сервера — при офлайн-запуске
// force-dynamic не сериализует данные в HTML-шелл и массив был бы пустым.
// Теперь CatalogView сам читает товары из IndexedDB через useCatalogSync (офлайн-источник).
export const dynamic = "force-dynamic";

export default function CatalogPage({
  params,
  searchParams,
}: {
  params: { secret: string };
  searchParams: { filter?: string };
}) {
  // Проверка секретной ссылки — не прошёл, показываем 404.
  // Эта серверная проверка СОХРАНЯЕТСЯ независимо от перехода на офлайн-источник.
  if (params.secret !== process.env.CATALOG_SECRET) {
    notFound();
  }

  // Начальный режим из ссылки ?filter=hit|new (для внешних ссылок); по умолчанию — каталог
  const initialMode: NavMode =
    searchParams.filter === "hit"
      ? "hit"
      : searchParams.filter === "new"
      ? "new"
      : "catalog";

  // products не передаётся — CatalogView возьмёт данные из useCatalogSync (IndexedDB)
  return <CatalogView initialMode={initialMode} />;
}
