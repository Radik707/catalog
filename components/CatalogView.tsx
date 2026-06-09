"use client";

import { useState, useMemo, useCallback } from "react";
import { Product } from "@/lib/types";
import ProductCard from "./ProductCard";
import SectionBar from "./SectionBar";
import SearchBar from "./SearchBar";
import ScrollToTop from "./ScrollToTop";
import Lightbox from "./Lightbox";
import { useCatalogSettings, PRESENTATION_PRESETS } from "./CatalogSettings";

// GROUP_ORDER удалён — порядок разделов берётся из данных (D-04)
// initialCategory удалён — навигация через scroll-to-anchor, не через URL-фильтр

interface CatalogViewProps {
  products: Product[];
  // Флаг активного фильтра Хит/Новинка — переключает в плоский список (D-06)
  isFiltered?: boolean;
}

export default function CatalogView({ products, isFiltered = false }: CatalogViewProps) {
  // Настройки отображения (управляются шестерёнкой в шапке)
  const { viewMode, gridPreset, showPhotos, showPrices } = useCatalogSettings();

  const [search, setSearch] = useState("");
  // Активный раздел для подсветки в SectionBar
  const [activeSection, setActiveSection] = useState("");
  // Индекс открытого фото в просмотрщике-галерее (null — закрыт)
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  // Мемоизируем колбэк смены раздела — передаём в SectionBar стабильной ссылкой,
  // чтобы не пересоздавать IntersectionObserver при каждом рендере
  const handleSectionChange = useCallback((section: string) => {
    setActiveSection(section);
  }, []);

  // Группировка раздел → подгруппа → товары в порядке первого появления (D-04).
  // Товары с section=undefined попадают в «Новинки» (D-05).
  // «Новинки» принудительно ставятся первым разделом.
  const grouped = useMemo(() => {
    const visible = products.filter((p) => p.stock > 1);
    const map = new Map<string, Map<string, Product[]>>();

    for (const p of visible) {
      // Если раздел не заполнен — товар уходит в «Новинки» (D-05)
      const sec = p.section || "Новинки";
      // Если подгруппа не заполнена — используем категорию или прочерк
      const sub = p.subgroup || p.category || "—";

      if (!map.has(sec)) map.set(sec, new Map());
      const subMap = map.get(sec)!;
      if (!subMap.has(sub)) subMap.set(sub, []);
      subMap.get(sub)!.push(p);
    }

    // Гарантируем «Новинки» первым разделом (D-05): если есть — переставляем в начало
    const entries = Array.from(map.entries());
    if (map.has("Новинки") && entries[0]?.[0] !== "Новинки") {
      const novinki = map.get("Новинки")!;
      map.delete("Новинки");
      // Пересобираем Map с «Новинки» в начале
      const reordered = new Map<string, Map<string, Product[]>>();
      reordered.set("Новинки", novinki);
      Array.from(map.entries()).forEach(([k, v]) => reordered.set(k, v));
      return reordered;
    }

    return map;
  }, [products]);

  // Список разделов в порядке первого появления (для SectionBar)
  const sections = useMemo(() => Array.from(grouped.keys()), [grouped]);

  // Инициализация activeSection при первой загрузке данных
  // (чтобы первая кнопка в полосе была подсвечена)
  const initialSection = sections[0] ?? "";

  // Плоский список — при активном поиске ИЛИ фильтре Хит/Новинка (D-06)
  const isFlat = Boolean(search.trim()) || isFiltered;

  // Плоско отфильтрованные товары (для ветки isFlat)
  const flatFiltered = useMemo(() => {
    if (!isFlat) return [];
    const q = search.trim().toLowerCase();
    return products.filter(
      (p) => p.stock > 1 && (q === "" || p.name.toLowerCase().includes(q))
    );
  }, [products, search, isFlat]);

  // Все видимые товары в порядке данных — источник для Lightbox
  const allVisible = useMemo(
    () => products.filter((p) => p.stock > 1),
    [products]
  );

  // Источник фото для просмотрщика: в плоском режиме — flatFiltered, иначе — все видимые
  const photoProducts = useMemo(
    () => (isFlat ? flatFiltered : allVisible).filter((p) => p.imageUrl),
    [isFlat, flatFiltered, allVisible]
  );

  // Открыть просмотрщик на конкретном товаре
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
      : "flex-1 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2 p-2";

  // Счётчик для SearchBar: в плоском режиме — отфильтрованные, иначе — все видимые
  const visibleCount = isFlat ? flatFiltered.length : allVisible.length;

  return (
    <div className="min-h-screen flex flex-col">
      <ScrollToTop viewMode={viewMode === "list" ? "list" : "grid"} />

      {/* Полоса разделов — только в групповом режиме (D-06: скрыта при поиске/фильтре) */}
      {!isFlat && sections.length > 0 && (
        <SectionBar
          sections={sections}
          activeSection={activeSection || initialSection}
          onSectionChange={handleSectionChange}
        />
      )}

      {/* Строка поиска */}
      <SearchBar value={search} onChange={setSearch} count={visibleCount} />

      {/* Контент: плоский список или группировка раздел→подгруппа */}
      {isFlat ? (
        // Плоский список при поиске или активном фильтре Хит/Новинка
        <div className={containerClass}>
          {flatFiltered.length > 0 ? (
            flatFiltered.map((product) => (
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
      ) : (
        // Групповой режим: заголовки раздел → подгруппа + карточки товаров
        <>
          {Array.from(grouped.entries()).map(([section, subMap]) => (
            <div key={section}>
              {/* Якорный заголовок раздела — id используется SectionBar и scroll-spy */}
              <h2
                id={`section-${section}`}
                className="text-lg font-bold text-gray-800 px-4 pt-5 pb-2"
              >
                {section}
              </h2>

              {Array.from(subMap.entries()).map(([subgroup, items]) => (
                <div key={subgroup}>
                  {/* Заголовок подгруппы со счётчиком товаров */}
                  <h3 className="text-sm font-semibold text-gray-500 px-4 pt-3 pb-1.5 uppercase tracking-wide">
                    {subgroup}{" "}
                    <span className="font-normal text-gray-400">({items.length})</span>
                  </h3>

                  {/* Сетка / список карточек товаров */}
                  <div className={containerClass}>
                    {items.map((product) => (
                      <ProductCard
                        key={product.id}
                        product={product}
                        showPhotos={showPhotos}
                        showPrices={showPrices}
                        viewMode={viewMode}
                        onPhotoOpen={() => openLightbox(product)}
                        presentationSizes={
                          viewMode === "presentation" ? preset.sizes : undefined
                        }
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ))}
        </>
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
