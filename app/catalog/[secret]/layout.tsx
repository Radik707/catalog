import CartIcon from "@/components/CartIcon";
import TelegramButton from "@/components/TelegramButton";
import CatalogSettingsProvider from "@/components/CatalogSettings";
import SettingsButton from "@/components/SettingsButton";
import SettingsPanel from "@/components/SettingsPanel";
import { NavProvider } from "@/components/NavProvider";
import CatalogNav from "@/components/CatalogNav";
import SubgroupFlyout from "@/components/SubgroupFlyout";
import { getProducts } from "@/lib/sheets";
import { buildNavData } from "@/lib/nav";

export default async function CatalogLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { secret: string };
}) {
  // Данные навигации (разделы + их подгруппы) собираем из товаров.
  // getProducts кэшируется, поэтому повторный вызов в page.tsx — без лишней сети.
  const products = await getProducts();
  const navData = buildNavData(products);

  return (
    <CatalogSettingsProvider>
      <NavProvider>
        {/* Синяя шапка: переключатель режима + иконки разделов слева, шестерёнка/корзина справа */}
        <header className="sticky top-0 z-50 bg-blue-600 shadow-sm">
          <div className="flex items-center justify-between px-2 h-12 gap-2">
            <CatalogNav navData={navData} />
            <div className="flex items-center gap-1 shrink-0">
              <SettingsButton />
              <CartIcon secret={params.secret} />
            </div>
          </div>
        </header>

        {/* Полоса подгрупп выбранного раздела — выезжает под шапкой */}
        <SubgroupFlyout navData={navData} />

        {/* Выпадающая панель настроек (по кнопке-шестерёнке) */}
        <SettingsPanel />

        <main>{children}</main>
        <TelegramButton />
      </NavProvider>
    </CatalogSettingsProvider>
  );
}
