"use client";

import { useRole } from "@/lib/useRole";
import SyncButton from "./SyncButton";
import FavoritesIcon from "./FavoritesIcon";

// Главная кнопка в правой части шапки — зависит от роли:
//   sales (агент)  → ↻ «Обновить каталог»;
//   client (клиент) → ♥ «Избранное».
// До готовности определения роли держим место пустым, чтобы у агента
// не мелькнуло чужое сердечко (роль загружается в useEffect).
export default function HeaderPrimaryAction({ secret }: { secret: string }) {
  const { role, ready } = useRole();

  if (!ready) return <div className="h-9 w-9" />;
  return role === "sales" ? <SyncButton /> : <FavoritesIcon secret={secret} />;
}
