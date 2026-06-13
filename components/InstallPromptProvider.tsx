"use client";

// Провайдер единственного экземпляра useInstallPrompt для всего дерева каталога.
// ПОЧЕМУ контекст нужен: баннер «Установить» и кнопка «Установить приложение»
// в настройках должны делить ОДНО перехваченное событие beforeinstallprompt.
// Два отдельных вызова useInstallPrompt() создали бы два ref — и второй вызов
// никогда не поймает событие, которое браузер посылает ровно один раз.
// Паттерн совпадает с CatalogSyncProvider (образец, этап 13).

import { createContext, useContext } from "react";
import { useInstallPrompt, UseInstallPromptResult } from "@/lib/useInstallPrompt";

// Контекст хранит полный результат useInstallPrompt.
// null — значение по умолчанию; хук-потребитель проверяет и бросает ошибку вне провайдера.
const InstallPromptContext = createContext<UseInstallPromptResult | null>(null);

/**
 * useInstallPromptContext — хук для потребителей контекста.
 * Используется в компонентах InstallBanner и SettingsPanel (план 02).
 * Бросает понятную ошибку, если вызван вне <InstallPromptProvider>.
 */
export function useInstallPromptContext(): UseInstallPromptResult {
  const ctx = useContext(InstallPromptContext);
  if (!ctx) {
    throw new Error(
      "useInstallPromptContext должен использоваться внутри <InstallPromptProvider>. " +
        "Убедитесь, что InstallPromptProvider обёртывает и шапку, и main в layout.tsx."
    );
  }
  return ctx;
}

/**
 * InstallPromptProvider — обёртка, которая создаёт ОДИН экземпляр useInstallPrompt
 * и раздаёт его через контекст всем дочерним компонентам (баннер, кнопка настроек).
 *
 * Размещается в app/catalog/[secret]/layout.tsx рядом с CatalogSyncProvider,
 * чтобы охватывать и шапку (где живёт SettingsPanel), и main (где живёт баннер).
 */
export default function InstallPromptProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  // Единственный вызов useInstallPrompt — именно здесь.
  // Баннер и кнопка настроек читают тот же перехваченный deferredPrompt.
  const installPrompt = useInstallPrompt();

  return (
    <InstallPromptContext.Provider value={installPrompt}>
      {children}
    </InstallPromptContext.Provider>
  );
}
