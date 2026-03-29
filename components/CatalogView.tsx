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

      {/* Список товаров */}
      <div className="flex-1">
        {filtered.length > 0 ? (
          filtered.map((product) => (
            <ProductCard key={product.id} product={product} />
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
