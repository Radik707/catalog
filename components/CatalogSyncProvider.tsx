"use client";

// Провайдер единственного экземпляра useCatalogSync для всего дерева каталога.
// ПОЧЕМУ контекст нужен: кнопка ↻ живёт в layout (шапка, выше по дереву),
// а CatalogView — в main (ниже). Без контекста прямой проп невозможен, а два
// отдельных вызова useCatalogSync() создадут два независимых sync с гонками
// и двойным fetch. Решение: один экземпляр хука — в провайдере, все потребители
// читают из него. Паттерн совпадает с CatalogSettingsProvider и NavProvider.

import { createContext, useContext } from "react";
import { useCatalogSync, UseCatalogSyncResult } from "@/lib/useCatalogSync";

// Контекст хранит полный результат useCatalogSync — products, isOnline, status, refetch и т.д.
const CatalogSyncContext = createContext<UseCatalogSyncResult | null>(null);

/**
 * Хук для потребителей контекста: CatalogView и SyncButton.
 * Бросает понятную ошибку, если использован вне CatalogSyncProvider.
 */
export function useCatalogSyncContext(): UseCatalogSyncResult {
  const ctx = useContext(CatalogSyncContext);
  if (!ctx) {
    throw new Error(
      "useCatalogSyncContext должен использоваться внутри <CatalogSyncProvider>. " +
        "Убедитесь, что CatalogSyncProvider обёртывает и шапку, и main в layout.tsx."
    );
  }
  return ctx;
}

/**
 * CatalogSyncProvider — обёртка, которая создаёт ОДИН экземпляр useCatalogSync
 * и раздаёт его через контекст всем дочерним компонентам.
 * Размещается в layout.tsx вокруг шапки + main.
 */
export default function CatalogSyncProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  // Единственный вызов хука — именно здесь. Кнопка ↻ и витрина читают этот же экземпляр.
  const sync = useCatalogSync();

  return (
    <CatalogSyncContext.Provider value={sync}>
      {children}
    </CatalogSyncContext.Provider>
  );
}
