"use client";

import { Product } from "@/lib/types";
import AddToCartButton from "./AddToCartButton";

interface ProductCardProps {
  product: Product;
}

export default function ProductCard({ product }: ProductCardProps) {
  const inStock = product.stock > 0;

  return (
    <div
      className={`flex items-center justify-between gap-3 px-4 py-3 border-b border-gray-100 ${
        inStock ? "bg-white" : "bg-gray-50 opacity-60"
      }`}
    >
      {/* Левая часть: название + мета */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 leading-tight truncate">
          {product.name}
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-gray-400">{product.category}</span>
          {inStock ? (
            <span className="text-xs text-emerald-600 font-medium">
              {product.stock} шт
            </span>
          ) : (
            <span className="text-xs text-gray-400">Нет в наличии</span>
          )}
        </div>
      </div>

      {/* Правая часть: цена + кнопка */}
      <div className="flex items-center gap-3 flex-shrink-0">
        <span className="text-sm font-bold text-gray-900 whitespace-nowrap">
          {product.price.toFixed(2)} ₽
        </span>
        <AddToCartButton product={product} />
      </div>
    </div>
  );
}
