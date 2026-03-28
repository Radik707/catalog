'use client';

import { useCartContext } from './CartProvider';
import { Product } from '@/lib/types';

interface AddToCartButtonProps {
  product: Product;
}

export default function AddToCartButton({ product }: AddToCartButtonProps) {
  const { isInCart, getQuantity, addToCart, updateQuantity } = useCartContext();
  const inStock = product.stock > 0;
  const inCart = isInCart(product.id);
  const qty = getQuantity(product.id);

  if (!inStock) {
    return (
      <span className="px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-200 text-gray-400">
        Нет
      </span>
    );
  }

  if (inCart) {
    return (
      <div className="flex items-center gap-1">
        <button
          onClick={() => updateQuantity(product.id, qty - 1)}
          className="w-7 h-7 rounded-lg bg-blue-100 text-blue-700 font-bold text-base flex items-center justify-center active:bg-blue-200"
        >
          −
        </button>
        <span className="w-5 text-center text-sm font-semibold text-gray-900">
          {qty}
        </span>
        <button
          onClick={() => updateQuantity(product.id, qty + 1)}
          disabled={qty >= product.stock}
          className="w-7 h-7 rounded-lg bg-blue-100 text-blue-700 font-bold text-base flex items-center justify-center active:bg-blue-200 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          +
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={() => addToCart(product)}
      className="px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-600 text-white active:bg-blue-700"
    >
      В корзину
    </button>
  );
}
