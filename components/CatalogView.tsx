"use client";

import { useState, useMemo } from "react";
import { Product } from "@/lib/types";
import ProductCard from "./ProductCard";
import CategoryFilter from "./CategoryFilter";
import SearchBar from "./SearchBar";

interface CatalogViewProps {
  products: Product[];
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

export default function CatalogView({ products }: CatalogViewProps) {
  const [activeGroup, setActiveGroup] = useState("");
  const [search, setSearch] = useState("");
  const [showPhotos, setShowPhotos] = useState(true);

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

  return (
    <div className="min-h-screen flex flex-col">
      {/* Фильтр по группам */}
      <CategoryFilter
        groups={groups}
        activeGroup={activeGroup}
        onSelect={setActiveGroup}
      />

      {/* Поиск */}
      <SearchBar value={search} onChange={setSearch} count={filtered.length} />

      {/* Переключатель режима отображения */}
      <div className="flex justify-end px-4 py-1.5 bg-white border-b border-gray-100">
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
      </div>

      {/* Список товаров */}
      <div className="flex-1">
        {filtered.length > 0 ? (
          filtered.map((product) => (
            <ProductCard key={product.id} product={product} showPhotos={showPhotos} />
          ))
        ) : (
          <div className="px-4 py-12 text-center text-gray-400">
            <p className="text-lg">Ничего не найдено</p>
            <p className="text-sm mt-1">Попробуйте изменить фильтр или поиск</p>
          </div>
        )}
      </div>
    </div>
  );
}
