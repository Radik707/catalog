"use client";

import { useState } from "react";
import Image from "next/image";
import { Product } from "@/lib/types";
import { getPackaging } from "@/lib/packaging";
import AddToCartButton from "./AddToCartButton";

// Набор размеров для режима презентации — меняется вместе с плотностью сетки,
// чтобы шрифт и цена уменьшались вслед за фото (пропорциональная карточка).
export interface PresentationSizes {
  photoH: string; // высота фото
  bodyPad: string; // отступы блока текста
  nameCls: string; // размер названия
  priceCls: string; // размер цены
  pkgCls: string; // размер фасовки
}

// Размеры по умолчанию (на случай, если пресет не передан).
const DEFAULT_PRESENTATION_SIZES: PresentationSizes = {
  photoH: "h-56 sm:h-72",
  bodyPad: "px-3 pt-2.5 pb-3 gap-2",
  nameCls: "text-sm sm:text-base",
  priceCls: "text-lg sm:text-xl",
  pkgCls: "text-xs",
};

interface ProductCardProps {
  product: Product;
  showPhotos?: boolean;
  viewMode?: "list" | "grid" | "presentation";
  // Открыть полноэкранный просмотрщик фото на этом товаре.
  // Вызывается только если у товара есть фото.
  onPhotoOpen?: () => void;
  // Размеры элементов в режиме презентации (зависят от выбранной плотности сетки).
  presentationSizes?: PresentationSizes;
}

const BADGE_STYLES: Record<string, string> = {
  хит: "bg-red-500 text-white",
  новинка: "bg-green-500 text-white",
  акция: "bg-orange-500 text-white",
};

function PhotoPlaceholder({ iconSize = "w-6 h-6" }: { iconSize?: string }) {
  return (
    <div className="w-full h-full flex items-center justify-center bg-white">
      <svg
        className={`${iconSize} text-gray-300`}
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

export default function ProductCard({
  product,
  showPhotos = true,
  viewMode = "list",
  onPhotoOpen,
  presentationSizes,
}: ProductCardProps) {
  const [flipped, setFlipped] = useState(false);
  const inStock = product.stock > 0;
  const packaging = getPackaging(product.group, product.name);
  const badgeStyle = product.badge ? BADGE_STYLES[product.badge] : null;

  const flipStyle = {
    transformStyle: "preserve-3d" as const,
    transition: "transform 0.4s ease",
    transform: flipped ? "rotateY(180deg)" : "rotateY(0deg)",
  };

  // ── РЕЖИМ СЕТКИ и ПРЕЗЕНТАЦИИ ──
  // Одна разметка, размеры зависят от isPresentation (крупнее в презентации).
  // Фронт-сторона в нормальном потоке — определяет высоту контейнера.
  // Оборот — absolute inset-0, подстраивается под высоту фронта.
  if (viewMode === "grid" || viewMode === "presentation") {
    const isPresentation = viewMode === "presentation";
    const sizes = presentationSizes ?? DEFAULT_PRESENTATION_SIZES;

    // Размеры элементов под режим. В презентации берём из пресета плотности.
    const photoH = isPresentation ? sizes.photoH : "h-32";
    const bodyPad = isPresentation ? sizes.bodyPad : "px-2 pt-1.5 pb-2 gap-1.5";
    const nameCls = isPresentation ? sizes.nameCls : "text-xs";
    const priceCls = isPresentation ? sizes.priceCls : "text-sm";
    const pkgCls = isPresentation ? sizes.pkgCls : "text-[10px]";
    const badgeCls = isPresentation ? "text-xs px-1.5 py-0.5" : "text-[9px] px-1 py-0.5";
    const badgePos = isPresentation ? "top-2 left-2" : "top-1 left-1";
    const placeholderIcon = isPresentation ? "w-16 h-16" : "w-10 h-10";

    return (
      <div
        style={{ perspective: "1000px" }}
        className={`relative rounded-lg overflow-hidden border border-gray-100 shadow-sm${inStock ? "" : " opacity-60"}`}
      >
        <div style={flipStyle} className="relative">
          {/* ── ЛИЦЕВАЯ СТОРОНА (нормальный поток, задаёт высоту) ── */}
          <div
            style={{ backfaceVisibility: "hidden" }}
            className={`flex flex-col cursor-pointer${inStock ? " bg-white" : " bg-gray-50"}`}
            onClick={() => setFlipped(true)}
          >
            {/* Фото — только если showPhotos. Тап по фото открывает
                просмотрщик; если фото нет — клик уходит наверх и переворачивает карточку. */}
            {showPhotos && (
              <div
                className={`relative bg-white ${photoH}`}
                onClick={
                  product.imageUrl
                    ? (e) => {
                        e.stopPropagation();
                        onPhotoOpen?.();
                      }
                    : undefined
                }
              >
                {product.imageUrl ? (
                  <Image
                    src={product.imageUrl}
                    alt={product.name}
                    fill
                    className="object-contain p-1"
                  />
                ) : (
                  <PhotoPlaceholder iconSize={placeholderIcon} />
                )}
                {badgeStyle && (
                  <span
                    className={`absolute ${badgePos} font-medium rounded ${badgeCls} ${badgeStyle}`}
                  >
                    {product.badge}
                  </span>
                )}
              </div>
            )}

            {/* Название + цена + кнопка */}
            <div className={`flex flex-col ${bodyPad}`}>
              {!showPhotos && badgeStyle && (
                <span className={`self-start font-medium rounded ${badgeCls} ${badgeStyle}`}>
                  {product.badge}
                </span>
              )}
              <p className={`${nameCls} font-medium text-gray-900 leading-tight`}>
                {product.name}
              </p>
              <div className="flex items-end justify-between gap-1">
                <div>
                  <p className={`${priceCls} font-bold text-gray-900 leading-none whitespace-nowrap`}>
                    {product.price.toFixed(2)} ₽
                  </p>
                  {packaging && (
                    <p className={`${pkgCls} text-gray-400 mt-0.5`}>{packaging}</p>
                  )}
                </div>
                <div onClick={(e) => e.stopPropagation()}>
                  <AddToCartButton product={product} />
                </div>
              </div>
            </div>
          </div>

          {/* ── ОБОРОТНАЯ СТОРОНА (absolute, совпадает с высотой фронта) ── */}
          <div
            style={{ backfaceVisibility: "hidden", transform: "rotateY(180deg)" }}
            className="absolute inset-0 flex flex-col justify-between px-3 py-2 bg-amber-50 cursor-pointer"
            onClick={() => setFlipped(false)}
          >
            <p className={`${nameCls} font-semibold text-gray-700 truncate`}>
              {product.name}
            </p>
            <p className={`${isPresentation ? "text-sm" : "text-xs"} text-gray-600 leading-relaxed mt-1 flex-1 overflow-hidden`}>
              {product.description || "Описание не добавлено"}
            </p>
            <p className="text-[10px] text-gray-400 mt-1">
              Нажмите, чтобы вернуться
            </p>
          </div>
        </div>
      </div>
    );
  }

  // ── РЕЖИМ СПИСКА ──
  return (
    <div
      style={{ perspective: "1000px" }}
      className={`relative border-b border-gray-100${inStock ? "" : " opacity-60"}`}
    >
      {/* Вращающийся контейнер */}
      <div style={flipStyle} className="relative">
        {/* ── ЛИЦЕВАЯ СТОРОНА ── */}
        <div
          style={{ backfaceVisibility: "hidden" }}
          className={`flex items-center gap-3 px-4 py-3${inStock ? " bg-white" : " bg-gray-50"}`}
        >
          {badgeStyle && (
            <span className={`absolute top-1.5 right-1.5 text-[10px] font-medium px-1.5 py-0.5 rounded ${badgeStyle}`}>
              {product.badge}
            </span>
          )}

          {/* Миниатюра — только в режиме «С фото».
              Есть фото → открыть просмотрщик; нет фото → перевернуть карточку. */}
          {showPhotos && (
            <button
              onClick={() => {
                if (product.imageUrl) onPhotoOpen?.();
                else setFlipped(true);
              }}
              className="flex-shrink-0 w-14 h-14 rounded overflow-hidden border border-gray-100 bg-white focus:outline-none"
              aria-label={product.imageUrl ? "Открыть фото" : "Показать описание товара"}
            >
              {product.imageUrl ? (
                <Image
                  src={product.imageUrl}
                  alt={product.name}
                  width={56}
                  height={56}
                  className="w-full h-full object-contain"
                />
              ) : (
                <PhotoPlaceholder />
              )}
            </button>
          )}

          {/* Название + мета — клик открывает флип */}
          <button
            onClick={() => setFlipped(true)}
            className="flex-1 min-w-0 text-left focus:outline-none"
          >
            <p className="text-sm font-medium text-gray-900 leading-tight">
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
          </button>

          {/* Цена + кнопка — НЕ триггерят флип */}
          <div className="flex items-center gap-3 flex-shrink-0">
            <div className="text-right">
              <span className="text-sm font-bold text-gray-900 whitespace-nowrap">
                {product.price.toFixed(2)} ₽
              </span>
              {packaging && (
                <p className="text-xs text-gray-400">{packaging}</p>
              )}
            </div>
            <AddToCartButton product={product} />
          </div>
        </div>

        {/* ── ОБОРОТНАЯ СТОРОНА ── */}
        <div
          style={{
            backfaceVisibility: "hidden",
            transform: "rotateY(180deg)",
          }}
          className="absolute inset-0 flex flex-col justify-between px-4 py-3 bg-amber-50 cursor-pointer"
          onClick={() => setFlipped(false)}
        >
          <p className="text-xs font-semibold text-gray-700 truncate">
            {product.name}
          </p>
          <p className="text-xs text-gray-600 leading-relaxed mt-1 flex-1 overflow-hidden">
            {product.description || "Описание не добавлено"}
          </p>
          <p className="text-[10px] text-gray-400 mt-1">
            Нажмите, чтобы вернуться
          </p>
        </div>
      </div>
    </div>
  );
}
