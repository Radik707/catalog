"use client";

import { useRole } from "@/lib/useRole";
import SyncButton from "./SyncButton";

// Главная кнопка в правой части шапки — зависит от роли:
//   sales (агент)  → ↻ «Обновить каталог»;
//   client (клиент) → ничего (♥ Избранное уже есть в нижних табах, D-03).
// До готовности определения роли держим резерв места (h-9 w-9), чтобы
// раскладка шапки не дёргалась при гидратации (SSR-safe паттерн).
export default function HeaderPrimaryAction({ secret: _secret }: { secret: string }) {
  const { role, ready } = useRole();

  if (!ready) return <div className="h-9 w-9" />;
  return role === "sales" ? <SyncButton /> : null;
}
