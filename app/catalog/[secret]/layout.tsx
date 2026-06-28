import CartIcon from "@/components/CartIcon";
// Объединённая раскрывающаяся иконка связи: основная → Telegram + MAX
import ContactFab from "@/components/ContactFab";
// Провайдер роли (client/sales) — монтируется снаружи CatalogSettingsProvider,
// чтобы CatalogSettings мог читать роль для дефолта gridPreset (D-10).
import RoleProvider from "@/lib/useRole";
import CatalogSettingsProvider from "@/components/CatalogSettings";
import SettingsButton from "@/components/SettingsButton";
import SettingsPanel from "@/components/SettingsPanel";
import { NavProvider } from "@/components/NavProvider";
import CatalogNav from "@/components/CatalogNav";
import SubgroupFlyout from "@/components/SubgroupFlyout";
import OfflineBar from "@/components/OfflineBar";
// Главная кнопка шапки: планшет → ↻ «Обновить», телефон/ПК → ♥ «Избранное»
import HeaderPrimaryAction from "@/components/HeaderPrimaryAction";
// Провайдер единственного экземпляра useCatalogSync — шарится между SyncButton и CatalogView
import CatalogSyncProvider from "@/components/CatalogSyncProvider";
// Провайдер состояния установки PWA — шарится между баннером и кнопкой настроек (D-06)
import InstallPromptProvider from "@/components/InstallPromptProvider";
// Баннер установки Android + bottom-sheet инструкции iOS (PWA-02)
import InstallPrompt from "@/components/InstallPrompt";
// Нижняя панель вкладок (Каталог · Избранное · Корзина) — только для роли «Клиент» (план 18-02, D-12)
import BottomTabBar from "@/components/BottomTabBar";
// Резерв нижнего отступа под панелью вкладок — только для роли «Клиент» (план 18-02, D-09)
import ClientBottomSpacer from "@/components/ClientBottomSpacer";
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
    <RoleProvider>
      <CatalogSettingsProvider>
      <NavProvider>
        {/*
          CatalogSyncProvider обёртывает всё дерево (шапку + main), чтобы SyncButton
          и CatalogView читали ОДИН экземпляр useCatalogSync — без двойного fetch и гонок.
          Размещается внутри NavProvider/CatalogSettingsProvider, которые нужны шапке.
        */}
        <CatalogSyncProvider>
          {/*
            InstallPromptProvider обёртывает всё дерево внутри CatalogSyncProvider,
            чтобы и SettingsPanel (шапка), и InstallPrompt (рядом с OfflineBar)
            делили ОДНО перехваченное событие beforeinstallprompt (D-06).
          */}
          <InstallPromptProvider>
            {/* Синяя шапка: переключатель режима + иконки разделов слева, кнопки справа */}
            <header className="sticky top-0 z-50 bg-blue-600 shadow-sm">
              {/* Внутренний контейнер шапки ограничен max-w для центрирования на широких мониторах */}
              <div className="flex items-center justify-between px-2 h-12 gap-2 max-w-screen-2xl mx-auto w-full">
                <CatalogNav navData={navData} secret={params.secret} />
                <div className="flex items-center gap-1 shrink-0">
                  {/* Планшет → ↻ «Обновить» (для торговых); телефон/ПК → ♥ «Избранное» */}
                  <HeaderPrimaryAction secret={params.secret} />
                  <SettingsButton />
                  <CartIcon secret={params.secret} />
                </div>
              </div>
            </header>

            {/* Индикатор офлайн-режима и свежести данных — клиентский остров */}
            <OfflineBar />

            {/* Баннер установки PWA — рядом с OfflineBar (D-06, PWA-02) */}
            <InstallPrompt />

            {/* Полоса подгрупп выбранного раздела — выезжает под шапкой */}
            <SubgroupFlyout navData={navData} />

            {/* Выпадающая панель настроек (по кнопке-шестерёнке) */}
            <SettingsPanel />

            {/* Контейнер витрины: ограничение ширины и центрирование на десктопе */}
            <main className="max-w-screen-2xl mx-auto w-full">
              {children}
              {/* Резерв высоты под панелью вкладок — только для роли «Клиент» (D-09) */}
              <ClientBottomSpacer />
            </main>
            {/* Раскрывающаяся иконка связи: основная (Telegram+MAX) → две иконки */}
            <ContactFab />
            {/* Нижняя панель вкладок: Каталог · Избранное · Корзина (только client, D-12) */}
            <BottomTabBar secret={params.secret} />
          </InstallPromptProvider>
        </CatalogSyncProvider>
      </NavProvider>
      </CatalogSettingsProvider>
    </RoleProvider>
  );
}
