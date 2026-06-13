import CartIcon from "@/components/CartIcon";
import TelegramButton from "@/components/TelegramButton";
import CatalogSettingsProvider from "@/components/CatalogSettings";
import SettingsButton from "@/components/SettingsButton";
import SettingsPanel from "@/components/SettingsPanel";
import { NavProvider } from "@/components/NavProvider";
import CatalogNav from "@/components/CatalogNav";
import SubgroupFlyout from "@/components/SubgroupFlyout";
import OfflineBar from "@/components/OfflineBar";
// Кнопка ↻ «Обновить каталог» — клиентский остров в синей шапке (SYNC-01, D-01)
import SyncButton from "@/components/SyncButton";
// Провайдер единственного экземпляра useCatalogSync — шарится между SyncButton и CatalogView
import CatalogSyncProvider from "@/components/CatalogSyncProvider";
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
        {/*
          CatalogSyncProvider обёртывает всё дерево (шапку + main), чтобы SyncButton
          и CatalogView читали ОДИН экземпляр useCatalogSync — без двойного fetch и гонок.
          Размещается внутри NavProvider/CatalogSettingsProvider, которые нужны шапке.
        */}
        <CatalogSyncProvider>
          {/* Синяя шапка: переключатель режима + иконки разделов слева, кнопки справа */}
          <header className="sticky top-0 z-50 bg-blue-600 shadow-sm">
            {/* Внутренний контейнер шапки ограничен max-w для центрирования на широких мониторах */}
            <div className="flex items-center justify-between px-2 h-12 gap-2 max-w-screen-2xl mx-auto w-full">
              <CatalogNav navData={navData} secret={params.secret} />
              <div className="flex items-center gap-1 shrink-0">
                {/* Кнопка ↻ «Обновить» — слева от шестерёнки (D-01 из CONTEXT.md) */}
                <SyncButton />
                <SettingsButton />
                <CartIcon secret={params.secret} />
              </div>
            </div>
          </header>

          {/* Индикатор офлайн-режима и свежести данных — клиентский остров */}
          <OfflineBar />

          {/* Полоса подгрупп выбранного раздела — выезжает под шапкой */}
          <SubgroupFlyout navData={navData} />

          {/* Выпадающая панель настроек (по кнопке-шестерёнке) */}
          <SettingsPanel />

          {/* Контейнер витрины: ограничение ширины и центрирование на десктопе */}
          <main className="max-w-screen-2xl mx-auto w-full">{children}</main>
          <TelegramButton />
        </CatalogSyncProvider>
      </NavProvider>
    </CatalogSettingsProvider>
  );
}
