"use client";

import { useDeviceClass } from "@/lib/useDeviceClass";
import SyncButton from "./SyncButton";
import FavoritesIcon from "./FavoritesIcon";

// Главная кнопка в правой части шапки — зависит от устройства:
//   планшет (торговые)  → ↻ «Обновить каталог» (избранное им не нужно, места больше);
//   телефон/ПК (клиент) → ♥ «Избранное».
// До готовности определения устройства держим место пустым, чтобы на планшете
// не мелькнуло чужое сердечко.
export default function HeaderPrimaryAction({ secret }: { secret: string }) {
  const { isTabletLike, ready } = useDeviceClass();

  if (!ready) return <div className="h-9 w-9" />;
  return isTabletLike ? <SyncButton /> : <FavoritesIcon secret={secret} />;
}
