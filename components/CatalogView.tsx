"use client";

import { useState, useMemo } from "react";
import { Product } from "@/lib/types";
import ProductCard from "./ProductCard";
import CategoryFilter from "./CategoryFilter";
import SearchBar from "./SearchBar";
import ScrollToTop from "./ScrollToTop";
import Lightbox from "./Lightbox";
import { useCatalogSettings, PRESENTATION_PRESETS } from "./CatalogSettings";

interface CatalogViewProps {
  products: Product[];
  initialCategory?: string;
}

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
  // Настройки отображения берём из общего контекста (управляются шестерёнкой в шапке).
  const { viewMode, gridPreset, showPhotos, showPrices } = useCatalogSettings();

  const [activeGroup, setActiveGroup] = useState(initialCategory);
  const [search, setSearch] = useState("");
  // Индекс открытого фото в просмотрщике-галерее (null — закрыт).
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

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

      {/* Список / Сетка / Презентация товаров */}
      <div className={containerClass}>
        {filtered.length > 0 ? (
          filtered.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              showPhotos={showPhotos}
              showPrices={showPrices}
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
