"use client";

import { useState, useMemo, useEffect } from "react";
import { Product } from "@/lib/types";
import ProductCard from "./ProductCard";
import SearchBar from "./SearchBar";
import ScrollToTop from "./ScrollToTop";
import Lightbox from "./Lightbox";
import { useCatalogSettings, PRESENTATION_PRESETS } from "./CatalogSettings";
import { useNav, NavMode } from "./NavProvider";

interface CatalogViewProps {
  products: Product[];
  // Начальный режим из URL (?filter=hit|new) — для внешних ссылок
  initialMode?: NavMode;
}

export default function CatalogView({ products, initialMode }: CatalogViewProps) {
  // Настройки отображения (управляются шестерёнкой в шапке)
  const { viewMode, gridPreset, showPhotos, showPrices } = useCatalogSettings();
  // Состояние навигации (режим, раздел, подгруппа) — из общего контекста
  const { mode, section, subgroup, setMode } = useNav();

  const [search, setSearch] = useState("");
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  // Однократно применяем режим из URL (например, ссылка ?filter=hit)
  useEffect(() => {
    if (initialMode && initialMode !== "catalog") setMode(initialMode);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Плоский список — при активном поиске ИЛИ в режимах Хит/Новинка
  const isFlat = Boolean(search.trim()) || mode !== "catalog";

  // Плоско отфильтрованные товары: режим (бейдж) + поиск по названию
  const flatFiltered = useMemo(() => {
    if (!isFlat) return [];
    const q = search.trim().toLowerCase();
    return products.filter((p) => {
      if (p.stock <= 1) return false;
      if (mode === "hit" && p.badge !== "хит") return false;
      if (mode === "new" && p.badge !== "новинка") return false;
      if (q && !p.name.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [products, search, isFlat, mode]);

  // Группировка раздел → подгруппа → товары (режим «Каталог»).
  // Учитывает выбранные раздел и подгруппу (фильтр). «Новинки» — первым разделом.
  const grouped = useMemo(() => {
    let visible = products.filter((p) => p.stock > 1);
    if (section) visible = visible.filter((p) => (p.section || "Новинки") === section);
    if (subgroup)
      visible = visible.filter((p) => (p.subgroup || p.category || "—") === subgroup);

    const map = new Map<string, Map<string, Product[]>>();
    for (const p of visible) {
      const sec = p.section || "Новинки";
      const sub = p.subgroup || p.category || "—";
      if (!map.has(sec)) map.set(sec, new Map());
      const subMap = map.get(sec)!;
      if (!subMap.has(sub)) subMap.set(sub, []);
      subMap.get(sub)!.push(p);
    }

    // «Новинки» — первым разделом
    if (map.has("Новинки")) {
      const novinki = map.get("Новинки")!;
      map.delete("Новинки");
      const reordered = new Map<string, Map<string, Product[]>>();
      reordered.set("Новинки", novinki);
      map.forEach((v, k) => reordered.set(k, v));
      return reordered;
    }
    return map;
  }, [products, section, subgroup]);

  // Сколько товаров показано (для счётчика в строке поиска)
  const groupedCount = useMemo(() => {
    let n = 0;
    grouped.forEach((subMap) => subMap.forEach((items) => (n += items.length)));
    return n;
  }, [grouped]);

  // Источник фото для просмотрщика
  const photoProducts = useMemo(() => {
    if (isFlat) return flatFiltered.filter((p) => p.imageUrl);
    const list: Product[] = [];
    grouped.forEach((subMap) => subMap.forEach((items) => list.push(...items)));
    return list.filter((p) => p.imageUrl);
  }, [isFlat, flatFiltered, grouped]);

  const openLightbox = (product: Product) => {
    const idx = photoProducts.findIndex((p) => p.id === product.id);
    if (idx !== -1) setLightboxIndex(idx);
  };

  const preset = PRESENTATION_PRESETS[gridPreset];

  // Класс контейнера товаров — зависит от режима отображения
  const containerClass =
    viewMode === "list"
      ? "flex-1"
      : viewMode === "presentation"
      ? `flex-1 grid ${preset.cols} gap-1.5 p-1.5`
      : "flex-1 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-2 p-2"; // десктоп xl/2xl

  const visibleCount = isFlat ? flatFiltered.length : groupedCount;

  // Карточка товара (общий рендер для обеих веток)
  const renderCard = (product: Product) => (
    <ProductCard
      key={product.id}
      product={product}
      showPhotos={showPhotos}
      showPrices={showPrices}
      viewMode={viewMode}
      onPhotoOpen={() => openLightbox(product)}
      presentationSizes={viewMode === "presentation" ? preset.sizes : undefined}
    />
  );

  return (
    <div className="min-h-screen flex flex-col">
      <ScrollToTop viewMode={viewMode === "list" ? "list" : "grid"} />

      {/* Строка поиска */}
      <SearchBar value={search} onChange={setSearch} count={visibleCount} />

      {isFlat ? (
        // Плоский список: поиск или режимы Хит/Новинка
        <div className={containerClass}>
          {flatFiltered.length > 0 ? (
            flatFiltered.map(renderCard)
          ) : (
            <div className="px-4 py-12 text-center text-gray-400">
              <p className="text-lg">Ничего не найдено</p>
              <p className="text-sm mt-1">Попробуйте изменить фильтр или поиск</p>
            </div>
          )}
        </div>
      ) : groupedCount === 0 ? (
        <div className="px-4 py-12 text-center text-gray-400">
          <p className="text-lg">Здесь пока нет товаров</p>
        </div>
      ) : (
        // Групповой режим: заголовки раздел → подгруппа + карточки
        Array.from(grouped.entries()).map(([sec, subMap]) => (
          <div key={sec}>
            <h2 className="text-lg font-bold text-gray-800 px-4 pt-5 pb-2">{sec}</h2>
            {Array.from(subMap.entries()).map(([sub, items]) => (
              <div key={sub}>
                <h3 className="text-sm font-semibold text-gray-500 px-4 pt-3 pb-1.5 uppercase tracking-wide">
                  {sub}{" "}
                  <span className="font-normal text-gray-400">({items.length})</span>
                </h3>
                <div className={containerClass}>{items.map(renderCard)}</div>
              </div>
            ))}
          </div>
        ))
      )}

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
