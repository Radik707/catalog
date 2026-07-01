"use client";

// Плотная строка режима «Быстрый набор» (QORD-01..03, D-03, D-06..D-08).
//
// Раскладка: горизонтальный flex — миниатюра 56×56 слева, название + остаток
// в центре, цена с подписью единицы и инлайн-количество справа.
//
// Без флипа, без открытия галереи (D-03).
// Единица читается через getUnit() — шов под этап 21b (D-06).
// Запись идёт в общую корзину useCart через AddToCartButton (D-07).
// Кап по остатку stock не дублируем — он уже в AddToCartButton/useCart (D-08).

import { useState } from "react";
import Image from "next/image";
import { Product } from "@/lib/types";
import { effectivePrice, PriceForm } from "@/lib/pricing";
import { getUnit } from "@/lib/getUnit";
import AddToCartButton from "@/components/AddToCartButton";
// Увеличение фото «поближе» по тапу — показать клиенту / рассмотреть (не на весь экран)
import ImagePeek from "@/components/ImagePeek";

interface QuickOrderRowProps {
  product: Product;
  // Форма цен: "1" → +5% для Ефимовой; "2" → базовые цены (по умолчанию).
  priceForm: PriceForm;
}

// Локальная заглушка-иконка фото — аналог PhotoPlaceholder из ProductCard.
// Показывается, если у товара нет фото или оно не загрузилось (офлайн/ошибка).
function PhotoPlaceholder() {
  return (
    <div className="w-full h-full flex items-center justify-center bg-white">
      <svg
        className="w-5 h-5 text-gray-300"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.5}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v13.5a1.5 1.5 0 001.5 1.5z"
        />
      </svg>
    </div>
  );
}

export default function QuickOrderRow({ product, priceForm }: QuickOrderRowProps) {
  // Локальный флаг ошибки загрузки фото (офлайн без кэша или нет фото).
  const [imgError, setImgError] = useState(false);
  // Открыт ли увеличенный просмотр фото (по тапу на миниатюру).
  const [peekOpen, setPeekOpen] = useState(false);
  // Есть ли что показывать крупно (фото загрузилось).
  const hasImage = Boolean(product.imageUrl) && !imgError;

  const inStock = product.stock > 0;
  // Эффективная цена с учётом формы (наценка +5% для Ефимовой при priceForm="1").
  const displayPrice = effectivePrice(product, priceForm);
  // Подпись единицы товара: «за шт» / «за блок» / «за коробку» / «за кг» / "" (D-06).
  const unit = getUnit(product);

  return (
    <div
      className={`flex items-center gap-3 px-4 py-2.5 border-b border-gray-100${
        inStock ? " bg-white" : " bg-gray-50 opacity-60"
      }`}
    >
      {/* Миниатюра 56×56. Тап по фото → увеличение «поближе» (ImagePeek), не флип
          и не полноэкранная галерея. Набор заявки идёт кнопками «− N +» справа —
          они фото не увеличивают. */}
      <button
        type="button"
        onClick={() => hasImage && setPeekOpen(true)}
        aria-label={hasImage ? "Показать фото крупнее" : undefined}
        className={`relative flex-shrink-0 w-14 h-14 p-0 rounded overflow-hidden border border-gray-100 bg-white${
          hasImage ? " cursor-zoom-in" : " cursor-default"
        }`}
      >
        {hasImage ? (
          // unoptimized: прямой Cloudinary URL — тот же, что ловит SW-matcher (офлайн).
          <Image
            src={product.imageUrl!}
            alt={product.name}
            width={56}
            height={56}
            className="w-full h-full object-contain"
            unoptimized
            onError={() => setImgError(true)}
          />
        ) : (
          // Заглушка при отсутствии фото или ошибке загрузки.
          <PhotoPlaceholder />
        )}
      </button>

      {/* Увеличенный просмотр фото (по тапу на миниатюру) */}
      {peekOpen && hasImage && (
        <ImagePeek src={product.imageUrl!} alt={product.name} onClose={() => setPeekOpen(false)} />
      )}

      {/* Центр: название + скромный показ остатка (как в режиме «Список», без нового фильтра — это этап 22). */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 leading-tight line-clamp-2">
          {product.name}
        </p>
        <div className="mt-0.5">
          {inStock ? (
            <span className="text-xs text-emerald-600 font-medium">
              {product.stock} шт
            </span>
          ) : (
            <span className="text-xs text-gray-400">Нет в наличии</span>
          )}
        </div>
      </div>

      {/* Правая колонка: цена + подпись единицы + инлайн-количество. */}
      <div className="flex items-center gap-3 flex-shrink-0">
        {/* Цена с подписью единицы (QORD-02). */}
        <div className="text-right">
          <span className="text-sm font-bold text-gray-900 whitespace-nowrap">
            {displayPrice.toFixed(2)} ₽
          </span>
          {/* Подпись единицы рендерится только если getUnit вернул непустую строку. */}
          {unit && (
            <p className="text-xs text-gray-400">{unit}</p>
          )}
        </div>

        {/* Инлайн-количество: AddToCartButton даёт «+» для первого добавления
            и «− N +» с QuantityInput и капом по stock, когда товар уже в корзине.
            Покрывает QORD-01 и QORD-03; логику капа не дублируем (D-07, D-08). */}
        <AddToCartButton product={product} />
      </div>
    </div>
  );
}
