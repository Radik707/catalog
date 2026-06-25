"use client";

import { useState } from "react";
import Image from "next/image";
import { Product } from "@/lib/types";
import { getPackaging } from "@/lib/packaging";
import { PriceForm, effectivePrice } from "@/lib/pricing";
import { priceColorClass } from "@/lib/priceColors";
import AddToCartButton from "./AddToCartButton";
import CardCornerButton from "./CardCornerButton";

// Набор размеров для режима презентации — меняется вместе с плотностью сетки,
// чтобы шрифт и цена уменьшались вслед за фото (пропорциональная карточка).
export interface PresentationSizes {
  photoH: string; // высота фото
  bodyPad: string; // отступы блока текста
  nameCls: string; // размер названия
  nameLines: string; // ограничение строк названия (line-clamp)
  priceCls: string; // размер цены
  pkgCls: string; // размер фасовки
  compactCart: boolean; // компактная кнопка корзины (иконка «+»)
}

// Размеры по умолчанию (на случай, если пресет не передан).
const DEFAULT_PRESENTATION_SIZES: PresentationSizes = {
  photoH: "h-56 sm:h-72",
  bodyPad: "px-3 pt-2.5 pb-3 gap-2",
  nameCls: "text-sm sm:text-base",
  nameLines: "line-clamp-2",
  priceCls: "text-base sm:text-lg",
  pkgCls: "text-xs",
  compactCart: false,
};

interface ProductCardProps {
  product: Product;
  showPhotos?: boolean;
  // Показывать ли цену и фасовку на лицевой стороне карточки.
  // При false — режим «только картинки» (на обороте цена остаётся).
  showPrices?: boolean;
  viewMode?: "list" | "grid" | "presentation";
  // Открыть полноэкранный просмотрщик фото на этом товаре.
  // Вызывается только если у товара есть фото.
  onPhotoOpen?: () => void;
  // Размеры элементов в режиме презентации (зависят от выбранной плотности сетки).
  presentationSizes?: PresentationSizes;
  // Форма цен: "1" → +5% на товары Ефимовой; "2" → базовые цены (по умолчанию).
  priceForm?: PriceForm;
  // Цвет цены на карточке (ключ из палитры priceColors) — настройка сайта из админки.
  priceColor?: string;
}

const BADGE_STYLES: Record<string, string> = {
  хит: "bg-red-500 text-white",
  новинка: "bg-green-500 text-white",
  акция: "bg-orange-500 text-white",
};

// Подпись бейджа на карточке. Значение в данных — «новинка», но на карточке
// показываем «NEW» (по просьбе владельца). Остальные метки — как есть.
function badgeLabel(badge?: string): string | undefined {
  if (!badge) return undefined;
  return badge === "новинка" ? "NEW" : badge;
}

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
  showPrices = true,
  viewMode = "list",
  onPhotoOpen,
  presentationSizes,
  priceForm = "2",
  priceColor,
}: ProductCardProps) {
  const [flipped, setFlipped] = useState(false);
  // Цена с учётом выбранной формы (для Ефимовой при форме «1» — +5%)
  const displayPrice = effectivePrice(product, priceForm);
  // Класс цвета цены из настройки сайта (по умолчанию — фиолетовый)
  const priceCol = priceColorClass(priceColor);
  // Флаг ошибки загрузки фото (D-06): при офлайн и незакэшированном фото
  // браузер не может загрузить изображение — показываем иконку-заглушку.
  const [imgError, setImgError] = useState(false);
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
    // Фото — КВАДРАТ (aspect-square), как в админ-панели: подгонка фото в панели
    // (квадратный кроп через Cloudinary) совпадает с показом в каталоге.
    const bodyPad = isPresentation ? sizes.bodyPad : "px-2 pt-1.5 pb-2 gap-1.5";
    const nameCls = isPresentation ? sizes.nameCls : "text-xs";
    const priceCls = isPresentation ? sizes.priceCls : "text-sm";
    const pkgCls = isPresentation ? sizes.pkgCls : "text-[10px]";
    const compactCart = isPresentation ? sizes.compactCart : false;
    const badgeCls = isPresentation ? "text-xs px-1.5 py-0.5" : "text-[9px] px-1 py-0.5";
    const badgePos = isPresentation ? "top-2 left-2" : "top-1 left-1";
    const placeholderIcon = isPresentation ? "w-16 h-16" : "w-10 h-10";

    // ── Авто-fit названия на телефоне ──
    // Карточки должны быть одинаковой высоты, а имя — помещаться целиком.
    // Размер шрифта подбираем по длине названия (без JS-измерений — быстро на 800+
    // карточках и без мигания), блок имени фиксированной высоты (≈3 строки),
    // line-clamp-3 — страховка от выхода за блок у самых длинных имён.
    // На планшете/ПК (sm+) — прежнее поведение: размер из пресета, 2 строки.
    const len = product.name.length;
    const phoneNameCls =
      len <= 40 ? "text-sm" : len <= 60 ? "text-xs" : len <= 78 ? "text-[11px]" : "text-[10px]";
    // sm:-часть размера берём из пресета, чтобы не конфликтовала с phoneNameCls (телефон)
    const smNameCls =
      nameCls.split(" ").filter((c) => c.startsWith("sm:")).join(" ") || "sm:text-xs";

    return (
      <div
        style={{ perspective: "1000px" }}
        className={`relative rounded-lg overflow-hidden border border-gray-100 shadow-sm hover:shadow-md transition-shadow duration-150${inStock ? "" : " opacity-60"}`}
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
              // Тап по фото больше НЕ открывает Lightbox — клик уходит наверх и
              // переворачивает карточку. Полноэкранный просмотр — через угловую
              // кнопку-стрелки (планшет); на телефоне/ПК в углу — сердечко избранного.
              <div className="relative bg-white w-full aspect-square">
                {product.imageUrl && !imgError ? (
                  // unoptimized: браузер запрашивает прямой res.cloudinary.com/... URL
                  // (подход 1) — совпадает с matcher SW и prefetch, кэш работает корректно.
                  <Image
                    src={product.imageUrl}
                    alt={product.name}
                    fill
                    className="object-contain"
                    unoptimized
                    onError={() => setImgError(true)}
                  />
                ) : (
                  // Заглушка: нет фото ИЛИ фото не загрузилось (D-06 — офлайн без кэша)
                  <PhotoPlaceholder iconSize={placeholderIcon} />
                )}
                {badgeStyle && (
                  <span
                    className={`absolute ${badgePos} font-medium rounded ${badgeCls} ${badgeStyle}`}
                  >
                    {badgeLabel(product.badge)}
                  </span>
                )}
                {/* Угловая кнопка: стрелки (планшет) или сердечко (телефон/ПК) */}
                <CardCornerButton
                  productId={product.id}
                  onPhotoOpen={onPhotoOpen}
                  canOpenPhoto={!!product.imageUrl}
                />
              </div>
            )}

            {/* Название + цена + кнопка */}
            <div className={`flex flex-col ${bodyPad}`}>
              {!showPhotos && badgeStyle && (
                <span className={`self-start font-medium rounded ${badgeCls} ${badgeStyle}`}>
                  {badgeLabel(product.badge)}
                </span>
              )}
              {/* Название показывается на лицевой стороне всегда.
                  На телефоне — полностью, без сокращений (line-clamp-none); карточка
                  растёт по тексту. На планшете/ПК — в две строки (как раньше). */}
              <p
                className={`${phoneNameCls} ${smNameCls} font-medium text-gray-900 leading-tight overflow-hidden line-clamp-3 sm:line-clamp-2 h-[3.4rem] sm:h-auto`}
              >
                {product.name}
              </p>
              {/* Описание — на лицевой стороне только на телефоне (презентация 2×3
                  с описанием). На планшете/ПК описание остаётся на обороте. */}
              {showPhotos && product.description && (
                <p className="text-[11px] text-gray-500 leading-snug line-clamp-2 sm:hidden">
                  {product.description}
                </p>
              )}
              <div className="flex items-end justify-between gap-1">
                {showPrices ? (
                  <div className="min-w-0">
                    <p className={`${priceCls} font-bold ${priceCol} leading-none whitespace-nowrap`}>
                      {displayPrice.toFixed(2)} ₽
                    </p>
                    {packaging && (
                      <p className={`${pkgCls} text-gray-400 mt-0.5 truncate hidden sm:block`}>
                        {packaging}
                      </p>
                    )}
                  </div>
                ) : (
                  <span />
                )}
                <div onClick={(e) => e.stopPropagation()}>
                  {/* На телефоне — компактная «+», на планшете — по пресету */}
                  <div className="sm:hidden">
                    <AddToCartButton product={product} compact />
                  </div>
                  <div className="hidden sm:block">
                    <AddToCartButton product={product} compact={compactCart} />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* ── ОБОРОТНАЯ СТОРОНА (absolute, совпадает с высотой фронта) ──
              Полное название → «Осталось: …» → описание → цена и корзина. */}
          <div
            style={{ backfaceVisibility: "hidden", transform: "rotateY(180deg)" }}
            className="absolute inset-0 flex flex-col px-3 py-2 bg-amber-50 cursor-pointer overflow-hidden"
            onClick={() => setFlipped(false)}
          >
            {/* Название без сокращений — места на обороте достаточно */}
            <p className={`${nameCls} font-semibold text-gray-800 leading-snug`}>
              {product.name}
            </p>
            {/* Остаток — сразу после названия, полным текстом */}
            <p className="text-xs font-medium mt-1">
              {inStock ? (
                <span className="text-emerald-700">Осталось: {product.stock} шт</span>
              ) : (
                <span className="text-gray-400">Нет в наличии</span>
              )}
            </p>
            {/* Описание — только если заполнено */}
            {product.description && (
              <p className="text-xs text-gray-600 leading-snug mt-1 overflow-hidden">
                {product.description}
              </p>
            )}
            <div className="flex-1" />
            {/* Цена + корзина (на обороте цена видна всегда) */}
            <div className="flex items-end justify-between gap-1">
              <div className="min-w-0">
                <p className={`${priceCls} font-bold ${priceCol} leading-none whitespace-nowrap`}>
                  {displayPrice.toFixed(2)} ₽
                </p>
                {packaging && (
                  <p className="text-[10px] text-gray-400 mt-0.5 truncate">{packaging}</p>
                )}
              </div>
              <div onClick={(e) => e.stopPropagation()}>
                <div className="sm:hidden">
                  <AddToCartButton product={product} compact />
                </div>
                <div className="hidden sm:block">
                  <AddToCartButton product={product} compact={compactCart} />
                </div>
              </div>
            </div>
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
          className={`flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition-colors duration-100${inStock ? " bg-white" : " bg-gray-50"}`}
        >
          {badgeStyle && (
            <span className={`absolute top-1.5 right-1.5 text-[10px] font-medium px-1.5 py-0.5 rounded ${badgeStyle}`}>
              {badgeLabel(product.badge)}
            </span>
          )}

          {/* Миниатюра — только в режиме «С фото».
              Тап по миниатюре переворачивает карточку; полноэкранный просмотр —
              угловой кнопкой-стрелками (планшет), на телефоне/ПК — сердечко. */}
          {showPhotos && (
            <div
              onClick={() => setFlipped(true)}
              className="relative flex-shrink-0 w-14 h-14 rounded overflow-hidden border border-gray-100 bg-white cursor-pointer"
            >
              {product.imageUrl && !imgError ? (
                // unoptimized: прямой Cloudinary URL — тот же, что ловит SW-matcher.
                // onError: при офлайн + незакэшированном фото → иконка-заглушка (D-06).
                <Image
                  src={product.imageUrl}
                  alt={product.name}
                  width={56}
                  height={56}
                  className="w-full h-full object-contain"
                  unoptimized
                  onError={() => setImgError(true)}
                />
              ) : (
                // Заглушка: нет фото ИЛИ фото не загрузилось (D-06 — офлайн без кэша)
                <PhotoPlaceholder />
              )}
              <CardCornerButton
                productId={product.id}
                onPhotoOpen={onPhotoOpen}
                canOpenPhoto={!!product.imageUrl}
                size="sm"
              />
            </div>
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
            {showPrices && (
              <div className="text-right">
                <span className={`text-sm font-bold ${priceCol} whitespace-nowrap`}>
                  {displayPrice.toFixed(2)} ₽
                </span>
                {packaging && (
                  <p className="text-xs text-gray-400">{packaging}</p>
                )}
              </div>
            )}
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
          {/* Название без сокращений */}
          <p className="text-sm font-semibold text-gray-800 leading-snug">
            {product.name}
          </p>
          {/* Остаток — сразу после названия, полным текстом */}
          <p className="text-xs font-medium mt-1">
            {inStock ? (
              <span className="text-emerald-700">Осталось: {product.stock} шт</span>
            ) : (
              <span className="text-gray-400">Нет в наличии</span>
            )}
          </p>
          {/* Описание — только если заполнено */}
          {product.description && (
            <p className="text-xs text-gray-600 leading-relaxed mt-1 overflow-hidden">
              {product.description}
            </p>
          )}
          <div className="flex-1" />
          {/* Цена + корзина */}
          <div className="flex items-end justify-between gap-2">
            <div className="min-w-0">
              <p className={`text-sm font-bold ${priceCol} leading-none whitespace-nowrap`}>
                {displayPrice.toFixed(2)} ₽
              </p>
              {packaging && (
                <p className="text-[10px] text-gray-400 mt-0.5 truncate">{packaging}</p>
              )}
            </div>
            <div onClick={(e) => e.stopPropagation()}>
              <AddToCartButton product={product} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
