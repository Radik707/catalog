import { Suspense } from "react";
import CartIcon from "@/components/CartIcon";
import NavTabs from "@/components/NavTabs";

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
          <Suspense
            fallback={
              <span className="text-white font-semibold text-sm">Каталог</span>
            }
          >
            <NavTabs />
          </Suspense>
          <CartIcon secret={params.secret} />
        </div>
      </header>
      <main>{children}</main>
    </>
  );
}
