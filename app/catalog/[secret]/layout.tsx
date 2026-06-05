import { Suspense } from "react";
import CartIcon from "@/components/CartIcon";
import NavTabs from "@/components/NavTabs";
import TelegramButton from "@/components/TelegramButton";
import CatalogSettingsProvider from "@/components/CatalogSettings";
import SettingsButton from "@/components/SettingsButton";
import SettingsPanel from "@/components/SettingsPanel";

export default function CatalogLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { secret: string };
}) {
  return (
    <CatalogSettingsProvider>
      <header className="sticky top-0 z-50 bg-blue-600 shadow-sm">
        <div className="flex items-center justify-between px-4 h-12">
          <Suspense
            fallback={
              <span className="text-white font-semibold text-sm">Каталог</span>
            }
          >
            <NavTabs />
          </Suspense>
          <div className="flex items-center gap-1">
            <SettingsButton />
            <CartIcon secret={params.secret} />
          </div>
        </div>
      </header>
      {/* Выпадающая панель настроек (под шапкой, по кнопке-шестерёнке) */}
      <SettingsPanel />
      <main>{children}</main>
      <TelegramButton />
    </CatalogSettingsProvider>
  );
}
