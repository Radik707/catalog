"use client";

// ClientBottomSpacer — резерв нижнего отступа контента под фиксированной панелью вкладок.
// Рендерится ТОЛЬКО для роли «Клиент» (role === 'client') и только после гидратации (ready).
// Для роли «Торговый» (sales) возвращает null — никакого лишнего отступа.
//
// Высота = 64px (h-16, высота BottomTabBar) + env(safe-area-inset-bottom).
// Через inline style — надёжнее на Safari, чем Tailwind pb-[env(...)], паттерн InstallPrompt/BottomTabBar.
//
// Монтируется внутри <main> после {children} в app/catalog/[secret]/layout.tsx (план 18-02, D-09).

import { useRole } from "@/lib/useRole";

export default function ClientBottomSpacer() {
  // SSR-safe гейт роли: до ready не рендерим ничего (без мелькания раскладки при гидратации).
  const { role, ready } = useRole();

  // Не client или ещё не готов — отступ не нужен.
  if (!ready || role !== "client") {
    return null;
  }

  // Резервируем высоту панели (4rem = h-16 = 64px) плюс зону home-indicator на iOS.
  return (
    <div
      aria-hidden="true"
      style={{ height: "calc(4rem + env(safe-area-inset-bottom))" }}
    />
  );
}
