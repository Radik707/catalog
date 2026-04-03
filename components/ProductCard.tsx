"use client";

import { useState } from "react";
import Image from "next/image";
import { Product } from "@/lib/types";
import AddToCartButton from "./AddToCartButton";

interface ProductCardProps {
  product: Product;
  showPhotos?: boolean;
  viewMode?: "list" | "grid";
}

function getPackaging(group: string, name: string): string {
  const n = name.toLowerCase();

  // Приоритет 1: точные совпадения по конкретным товарам
  if (n.includes("конфеты фараделла с печеньем трио")) return "за упаковку";
  if (n.includes("шоко-кроко")) return "за упаковку";
  if (n.includes("сэнсой хлопья нори")) return "за коробку";
  if (n.includes("акконд крекер с солью 190г/20")) return "за шт";
  if (n.includes("акконд крекер с солью 255г/12")) return "за шт";
  if (n.includes("акконд крекер вес.") && !n.includes("аккондовский с солью со вкусом сметаны и лука")) return "за коробку";
  if (n.includes("акконд печ. вес.")) return "за коробку";
  if (n.includes("вафли вес.")) return "за коробку";
  if (n.startsWith("батончик")) return "за шт";
  if (n.startsWith("драже") && !n.includes("38г/12шт")) return "за шт";
  if (n.includes("нутелла")) return "за шт";
  if (n.includes("холс")) return "за блок";
  if (n.includes("ментос")) return "за блок";
  if (n.includes("орбит")) return "за блок";

  // Приоритет 2: ШТ большими буквами → за шт
  if (name.includes("ШТ")) return "за шт";

  // Приоритет 3: комбинированные правила
  if (name.includes("ТРИО") && n.includes("вес. конфеты")) return "за упаковку";

  // Приоритет 4: глобальные правила по ключевым словам
  if (n.includes("печ. фас. трио")) return "за блок";
  if (name.includes("УПК")) return "за упаковку";
  if (n.includes("фас кг")) return "за кг";
  if (n.includes("фас.")) return "за шт";

  // Приоритет 5: правила по категории
  switch (group) {
    case "Батончики и шоколад":
      return n.includes("шоколад") ? "за шт" : "за блок";
    case "Конфеты и печенье":
      if (n.includes("вес.")) return "за кг";
      if (n.includes("печ.") || n.includes("крекер")) return "за ящик";
      return "";
    case "Лапша и каши":
      return "за шт";
    case "Чай и кофе":
      return "за пачку";
    case "Снэки":
      return "за шт";
    case "Крупы и бакалея":
      return "за пачку";
    case "Детское":
      return "за упаковку";
    case "Напитки":
      if (n.includes("добрый сок")) return "за шт";
      if (n.includes("добрый")) return "за пак";
      if (n.includes("лотте")) return "за шт";
      return "за блок";
    case "Энергетики":
      return "за пак";
    case "Соусы и специи":
    case "Соусы и приправы":
    case "Коробочные конфеты":
    case "Прикассовое":
    case "Стоевъ и Сэнсой":
    case "Консервация":
      return "за шт";
    default:
      return "";
  }
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

  // ── РЕЖИМ СЕТКИ ──
  // Фронт-сторона в нормальном потоке — определяет высоту контейнера.
  // Оборот — absolute inset-0, подстраивается под высоту фронта.
  // Это позволяет карточке сжиматься когда фото скрыто.
  if (viewMode === "grid") {
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
            {/* Фото — только если showPhotos */}
            {showPhotos && (
              <div className="relative bg-white h-32">
                {product.imageUrl ? (
                  <Image
                    src={product.imageUrl}
                    alt={product.name}
                    fill
                    className="object-contain p-1"
                  />
                ) : (
                  <PhotoPlaceholder iconSize="w-10 h-10" />
                )}
                {badgeStyle && (
                  <span
                    className={`absolute top-1 left-1 text-[9px] font-medium px-1 py-0.5 rounded ${badgeStyle}`}
                  >
                    {product.badge}
                  </span>
                )}
              </div>
            )}

            {/* Название + цена + кнопка */}
            <div className="flex flex-col px-2 pt-1.5 pb-2 gap-1.5">
              {!showPhotos && badgeStyle && (
                <span className={`self-start text-[9px] font-medium px-1 py-0.5 rounded ${badgeStyle}`}>
                  {product.badge}
                </span>
              )}
              <p className="text-xs font-medium text-gray-900 leading-tight">
                {product.name}
              </p>
              <div className="flex items-end justify-between gap-1">
                <div>
                  <p className="text-sm font-bold text-gray-900 leading-none whitespace-nowrap">
                    {product.price.toFixed(2)} ₽
                  </p>
                  {packaging && (
                    <p className="text-[10px] text-gray-400 mt-0.5">{packaging}</p>
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

  // ── РЕЖИМ СПИСКА (текущее поведение) ──
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

          {/* Миниатюра — только в режиме «С фото», клик открывает флип */}
          {showPhotos && (
            <button
              onClick={() => setFlipped(true)}
              className="flex-shrink-0 w-14 h-14 rounded overflow-hidden border border-gray-100 bg-white focus:outline-none"
              aria-label="Показать описание товара"
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
