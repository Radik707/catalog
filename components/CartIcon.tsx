"use client";

import { useRole } from "@/lib/useRole";
import { useCartContext } from './CartProvider';

// Иконка корзины в правой части шапки с бейджем числа позиций.
// Гейт роли: у client корзина продублирована в нижних табах (D-03),
// поэтому верхняя иконка у client скрыта — показывается только у sales.
// До готовности роли (ready=false) держим резерв места, чтобы шапка
// агента (sales) не дёргалась при гидратации (SSR-safe паттерн).
export default function CartIcon({ secret }: { secret: string }) {
  // Хуки вызываются БЕЗУСЛОВНО (правило хуков — выше любого раннего return)
  const { role, ready } = useRole();
  const { items } = useCartContext();

  // Бейдж показывает число ПОЗИЦИЙ (разных товаров), а не сумму количеств.
  const count = items.length;

  // До готовности роли — резерв места, чтобы шапка sales не прыгала
  if (!ready) return <span className="w-9 h-9" />;
  // У client корзина есть в нижних табах — верхнюю скрываем
  if (role === "client") return null;

  return (
    <a href={`/catalog/${secret}/cart`} className="relative p-2">
      <svg
        className="w-6 h-6 text-white"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z"
        />
      </svg>
      {count > 0 && (
        <span className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
          {count > 99 ? "99" : count}
        </span>
      )}
    </a>
  );
}
