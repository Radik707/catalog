"use client";

import { useState, useMemo, useEffect } from "react";
import { Product } from "@/lib/types";
import ProductCard, { PresentationSizes } from "./ProductCard";
import CategoryFilter from "./CategoryFilter";
import SearchBar from "./SearchBar";
import ScrollToTop from "./ScrollToTop";
import Lightbox from "./Lightbox";

interface CatalogViewProps {
  products: Product[];
  initialCategory?: string;
}

type ViewMode = "list" | "grid" | "presentation";
type GridPreset = "2x3" | "3x4" | "4x6";

// Пресеты плотности сетки для режима презентации.
// cols — колонки (адаптивно), sizes — размеры фото/текста (масштабируются
// вместе: чем плотнее сетка, тем мельче фото, шрифт и цена).
const PRESENTATION_PRESETS: Record<
  GridPreset,
  { label: string; cols: string; sizes: PresentationSizes }
> = {
  "2x3": {
    label: "2×3",
    cols: "grid-cols-2",
    sizes: {
      photoH: "h-64 sm:h-80",
      bodyPad: "px-3 pt-2 pb-3 gap-1.5",
      nameCls: "text-base sm:text-lg",
      priceCls: "text-xl sm:text-2xl",
      pkgCls: "text-sm",
    },
  },
  "3x4": {
    label: "3×4",
    cols: "grid-cols-2 sm:grid-cols-3",
    sizes: {
      photoH: "h-44 sm:h-52",
      bodyPad: "px-2.5 pt-1.5 pb-2.5 gap-1",
      nameCls: "text-sm sm:text-base",
      priceCls: "text-lg sm:text-xl",
      pkgCls: "text-xs",
    },
  },
  "4x6": {
    label: "4×6",
    cols: "grid-cols-3 sm:grid-cols-4",
    sizes: {
      photoH: "h-28 sm:h-32",
      bodyPad: "px-2 pt-1 pb-2 gap-0.5",
      nameCls: "text-[11px] sm:text-xs",
      priceCls: "text-sm sm:text-base",
      pkgCls: "text-[10px]",
    },
  },
};

// Порядок групп для отображения
const GROUP_ORDER = [
  "Напитки",
  "Батончики и шоколад",
  "Чай и кофе",
  "Конфеты и печенье",
  "Снэки",
  "Детское",
  "Лапша и каши",
  "Крупы и бакалея",
  "Энергетики",
  "Соусы и приправы",
  "Консервация",
  "Подарки и торты",
];

export default function CatalogView({ products, initialCategory = "" }: CatalogViewProps) {
  const [activeGroup, setActiveGroup] = useState(initialCategory);
  const [search, setSearch] = useState("");
  const [showPhotos, setShowPhotos] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [gridPreset, setGridPreset] = useState<GridPreset>("3x4");
  // Индекс открытого фото в просмотрщике-галерее (null — закрыт).
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  useEffect(() => {
    const savedView = localStorage.getItem("viewMode");
    if (savedView === "list" || savedView === "grid" || savedView === "presentation") {
      setViewMode(savedView);
    }
    const savedPreset = localStorage.getItem("gridPreset");
    if (savedPreset === "2x3" || savedPreset === "3x4" || savedPreset === "4x6") {
      setGridPreset(savedPreset);
    }
  }, []);

  const handleViewMode = (mode: ViewMode) => {
    setViewMode(mode);
    localStorage.setItem("viewMode", mode);
  };

  const handleGridPreset = (preset: GridPreset) => {
    setGridPreset(preset);
    localStorage.setItem("gridPreset", preset);
  };

  // Собираем уникальные группы из данных, сортируем по заданному порядку
  const groups = useMemo(() => {
    const unique = Array.from(new Set(products.map((p) => p.group)));
    return unique.sort((a, b) => {
      const ia = GROUP_ORDER.indexOf(a);
      const ib = GROUP_ORDER.indexOf(b);
      return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
    });
  }, [products]);

  // Фильтрация: по группе + по поиску (товары с stock <= 1 скрыты)
  const filtered = useMemo(() => {
    let result = products.filter((p) => p.stock > 1);

    if (activeGroup) {
      result = result.filter((p) => p.group === activeGroup);
    }

    if (search.trim()) {
      const q = search.trim().toLowerCase();
      result = result.filter((p) => p.name.toLowerCase().includes(q));
    }

    return result;
  }, [products, activeGroup, search]);

  // Товары с фото в текущем порядке — по ним листает просмотрщик-галерея.
  const photoProducts = useMemo(
    () => filtered.filter((p) => p.imageUrl),
    [filtered]
  );

  // Открыть просмотрщик на конкретном товаре.
  const openLightbox = (product: Product) => {
    const idx = photoProducts.findIndex((p) => p.id === product.id);
    if (idx !== -1) setLightboxIndex(idx);
  };

  const preset = PRESENTATION_PRESETS[gridPreset];

  // Класс контейнера товаров под выбранный режим
  const containerClass =
    viewMode === "list"
      ? "flex-1"
      : viewMode === "presentation"
      ? `flex-1 grid ${preset.cols} gap-4 p-4`
      : "flex-1 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 p-3";

  return (
    <div className="min-h-screen flex flex-col">
      <ScrollToTop viewMode={viewMode === "list" ? "list" : "grid"} />
      {/* Фильтр по группам */}
      <CategoryFilter
        groups={groups}
        activeGroup={activeGroup}
        onSelect={setActiveGroup}
      />

      {/* Поиск */}
      <SearchBar value={search} onChange={setSearch} count={filtered.length} />

      {/* Переключатели режима отображения */}
      <div className="flex flex-wrap justify-end items-center gap-2 px-4 py-1.5 bg-white border-b border-gray-100">
        {/* Выбор плотности сетки — только в режиме презентации */}
        {viewMode === "presentation" && (
          <div className="flex rounded-lg overflow-hidden border border-gray-200 text-xs mr-auto">
            {(Object.keys(PRESENTATION_PRESETS) as GridPreset[]).map((key) => (
              <button
                key={key}
                onClick={() => handleGridPreset(key)}
                className={`px-3 py-1 transition-colors ${
                  gridPreset === key ? "bg-blue-500 text-white" : "bg-white text-gray-500"
                }`}
              >
                {PRESENTATION_PRESETS[key].label}
              </button>
            ))}
          </div>
        )}

        <div className="flex rounded-lg overflow-hidden border border-gray-200 text-xs">
          <button
            onClick={() => setShowPhotos(true)}
            className={`px-3 py-1 transition-colors ${
              showPhotos ? "bg-blue-500 text-white" : "bg-white text-gray-500"
            }`}
          >
            С фото
          </button>
          <button
            onClick={() => setShowPhotos(false)}
            className={`px-3 py-1 transition-colors ${
              !showPhotos ? "bg-blue-500 text-white" : "bg-white text-gray-500"
            }`}
          >
            Без фото
          </button>
        </div>
        <div className="flex rounded-lg overflow-hidden border border-gray-200 text-xs">
          <button
            onClick={() => handleViewMode("list")}
            className={`px-3 py-1 transition-colors ${
              viewMode === "list" ? "bg-blue-500 text-white" : "bg-white text-gray-500"
            }`}
          >
            ☰ Список
          </button>
          <button
            onClick={() => handleViewMode("grid")}
            className={`px-3 py-1 transition-colors ${
              viewMode === "grid" ? "bg-blue-500 text-white" : "bg-white text-gray-500"
            }`}
          >
            ⊞ Сетка
          </button>
          <button
            onClick={() => handleViewMode("presentation")}
            className={`px-3 py-1 transition-colors ${
              viewMode === "presentation" ? "bg-blue-500 text-white" : "bg-white text-gray-500"
            }`}
          >
            ◳ Презентация
          </button>
        </div>
      </div>

      {/* Список / Сетка / Презентация товаров */}
      <div className={containerClass}>
        {filtered.length > 0 ? (
          filtered.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              showPhotos={showPhotos}
              viewMode={viewMode}
              onPhotoOpen={() => openLightbox(product)}
              presentationSizes={viewMode === "presentation" ? preset.sizes : undefined}
            />
          ))
        ) : (
          <div className="px-4 py-12 text-center text-gray-400">
            <p className="text-lg">Ничего не найдено</p>
            <p className="text-sm mt-1">Попробуйте изменить фильтр или поиск</p>
          </div>
        )}
      </div>

      {/* Полноэкранный просмотрщик-галерея фото */}
      {lightboxIndex !== null && photoProducts.length > 0 && (
        <Lightbox
          products={photoProducts}
          index={lightboxIndex}
          onIndexChange={setLightboxIndex}
          onClose={() => setLightboxIndex(null)}
        />
      )}
    </div>
  );
}
