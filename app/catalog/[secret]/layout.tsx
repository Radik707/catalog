import CartIcon from "@/components/CartIcon";

export default function CatalogLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { secret: string };
}) {
  return (
    <>
      <header className="sticky top-0 z-50 bg-blue-600 shadow-sm">
        <div className="flex items-center justify-between px-4 h-12">
          <a
            href={`/catalog/${params.secret}`}
            className="text-white font-semibold text-base"
          >
            Каталог
          </a>
          <CartIcon secret={params.secret} />
        </div>
      </header>
      <main>{children}</main>
    </>
  );
}
