# Phase 6: Двухуровневая навигация на витрине — Pattern Map

**Mapped:** 2026-06-09
**Files analyzed:** 5 (изменяемых) + 1 (новый компонент)
**Analogs found:** 6 / 6

---

## File Classification

| Новый / изменяемый файл | Роль | Data Flow | Ближайший аналог | Качество совпадения |
|---|---|---|---|---|
| `lib/types.ts` | model | — | `lib/types.ts` (текущий) | exact |
| `lib/sheets.ts` | service | request-response | `lib/sheets.ts` (текущий) | exact |
| `components/CategoryFilter.tsx` | component | event-driven | `components/CategoryFilter.tsx` (текущий) | exact |
| `components/CatalogView.tsx` | component | event-driven + transform | `components/CatalogView.tsx` (текущий) | exact |
| `components/SectionBar.tsx` (новый) | component | event-driven + scroll-spy | `components/ScrollToTop.tsx` | role-match |
| `app/catalog/[secret]/page.tsx` | route/page | request-response | `app/catalog/[secret]/page.tsx` (текущий) | exact |

---

## Pattern Assignments

### `lib/types.ts` (model)

**Аналог:** `lib/types.ts` (текущий, строки 1-12)

Добавить два опциональных поля к существующему интерфейсу `Product`. Порядок полей соответствует колонкам Sheet (A→K).

**Текущая структура** (строки 1-12):
```typescript
export interface Product {
  id: string;
  name: string;
  price: number;
  stock: number;
  category: string;
  group: string;
  supplier: string;
  badge?: string;
  imageUrl?: string;
  description?: string;
}
```

**Что добавить** — два поля после `description`, опциональные (`?`), как все поля после `supplier`:
```typescript
  subgroup?: string;  // колонка J — «Подгруппа»
  section?: string;   // колонка K — «Раздел»
```

---

### `lib/sheets.ts` (service, request-response)

**Аналог:** `lib/sheets.ts` (текущий, строки 1-41)

**Импорты и константы** (строки 1-3):
```typescript
import { Product } from "./types";

const SHEETS_ID = process.env.GOOGLE_SHEETS_ID;
const API_KEY = process.env.GOOGLE_API_KEY;
```

**Паттерн чтения диапазона** (строки 16-19):
```typescript
// ИЗМЕНИТЬ: "Товары!A2:I" → "Товары!A2:K"
const range = encodeURIComponent("Товары!A2:I");
const url = `https://sheets.googleapis.com/v4/spreadsheets/${SHEETS_ID}/values/${range}?key=${API_KEY}`;

const res = await fetch(url, { next: { revalidate: 300 } }); // кеш 5 минут (ISR)
```

**Паттерн маппинга строк** (строки 29-40):
```typescript
return rows.map((row, index) => ({
  id: String(index + 1),
  name: row[0] || "",
  price: parseFloat(row[1]) || 0,
  stock: parseInt(row[2]) || 0,
  category: row[3] || "",
  group: row[4] || "",
  supplier: row[5] || "",
  badge: row[6] || undefined,
  imageUrl: row[7] || undefined,
  description: row[8] || undefined,
  // ДОБАВИТЬ: новые поля J и K
}));
```

**Что добавить** в маппинг — по аналогии с `description` (undefined если пусто):
```typescript
  subgroup: row[9] || undefined,  // J — «Подгруппа»
  section:  row[10] || undefined, // K — «Раздел»
```

---

### `components/CategoryFilter.tsx` → переделать в `SectionBar` (component, event-driven + scroll-spy)

**Аналог:** `components/CategoryFilter.tsx` (текущий, строки 1-43)

Этот файл **полностью переписывается** — старая логика плоских кнопок-фильтров заменяется прилипающей полосой разделов со scroll-to-anchor и scroll-spy. Интерфейс пропсов меняется.

**Sticky-контейнер — скопировать как есть** (строки 14-16):
```tsx
<div className="sticky top-0 z-10 bg-white border-b border-gray-200 shadow-sm">
  <div className="flex gap-2 px-4 py-2.5 overflow-x-auto scrollbar-hide">
```

**Паттерн кнопки-таблетки — скопировать стили** (строки 17-39):
```tsx
className={`flex-shrink-0 px-3.5 py-1.5 rounded-full text-sm font-medium transition-colors whitespace-nowrap ${
  activeGroup === group
    ? "bg-blue-600 text-white"
    : "bg-gray-100 text-gray-600 active:bg-gray-200"
}`}
```

**Новый интерфейс пропсов** (вместо старого):
```typescript
interface SectionBarProps {
  sections: string[];       // список разделов в порядке появления
  activeSection: string;    // текущий активный раздел (из scroll-spy)
  onSelect: (section: string) => void; // клик = плавный скролл к якорю
}
```

**Scroll-to-anchor паттерн** — взять из `ScrollToTop.tsx` строки 47-48 (window.scrollTo с smooth):
```typescript
// Плавная прокрутка к якорному элементу
const el = document.getElementById(`section-${section}`);
el?.scrollIntoView({ behavior: "smooth", block: "start" });
```

**Scroll-spy паттерн** — взять из `ScrollToTop.tsx` структуру useEffect + window.addEventListener (строки 16-42):
```typescript
// IntersectionObserver для определения активного раздела при прокрутке
useEffect(() => {
  const observer = new IntersectionObserver(
    (entries) => { /* обновить activeSection */ },
    { rootMargin: "-50% 0px -50% 0px", threshold: 0 }
  );
  // Следить за всеми элементами с id="section-*"
  sections.forEach(s => {
    const el = document.getElementById(`section-${s}`);
    if (el) observer.observe(el);
  });
  return () => observer.disconnect();
}, [sections]);
```

---

### `components/CatalogView.tsx` (component, event-driven + transform)

**Аналог:** `components/CatalogView.tsx` (текущий, строки 1-137)

Это центральный файл этапа — структура сохраняется, внутренности заменяются.

**"use client" + импорты** (строки 1-10) — скопировать структуру:
```typescript
"use client";

import { useState, useMemo, useRef, useEffect } from "react";
import { Product } from "@/lib/types";
import ProductCard from "./ProductCard";
// CategoryFilter заменяется SectionBar (новый компонент):
import SectionBar from "./SectionBar";
import SearchBar from "./SearchBar";
import ScrollToTop from "./ScrollToTop";
import Lightbox from "./Lightbox";
import { useCatalogSettings, PRESENTATION_PRESETS } from "./CatalogSettings";
```

**Паттерн пропсов** (строки 12-15) — `initialCategory` больше не нужен, удалить:
```typescript
interface CatalogViewProps {
  products: Product[];
  // initialCategory убирается — теперь навигация через scroll-to-anchor, не фильтр
}
```

**`GROUP_ORDER` удалить** (строки 18-32) — заменить группировкой из данных.

**Паттерн useMemo для вычисления структуры** (строки 44-51) — взять структуру `useMemo` + `Array.from(new Set(...))`, но теперь для разделов и подгрупп:
```typescript
// Структура разделов → подгруппы → товары в порядке первого появления
const grouped = useMemo(() => {
  const visible = products.filter((p) => p.stock > 1);
  // Map: section → Map: subgroup → Product[]
  const map = new Map<string, Map<string, Product[]>>();
  for (const p of visible) {
    const sec = p.section || "Новинки";       // fallback по D-05
    const sub = p.subgroup || p.category || "—"; // fallback
    if (!map.has(sec)) map.set(sec, new Map());
    const subMap = map.get(sec)!;
    if (!subMap.has(sub)) subMap.set(sub, []);
    subMap.get(sub)!.push(p);
  }
  return map;
}, [products]);
```

**Паттерн фильтрации** (строки 54-67) — скопировать структуру фильтрации, адаптировать под ветку «плоский список» (D-06):
```typescript
// Плоский список при активном поиске или фильтре Хит/Новинка
const isFlat = Boolean(search.trim());  // фильтр по badge передаётся через props.products (уже отфильтрованы в page.tsx)

const flatFiltered = useMemo(() => {
  if (!isFlat) return [];
  return products.filter((p) => p.stock > 1 && p.name.toLowerCase().includes(search.trim().toLowerCase()));
}, [products, search, isFlat]);
```

**Паттерн containerClass** (строки 83-89) — скопировать без изменений:
```typescript
const containerClass =
  viewMode === "list"
    ? "flex-1"
    : viewMode === "presentation"
    ? `flex-1 grid ${preset.cols} gap-1.5 p-1.5`
    : "flex-1 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2 p-2";
```

**Паттерн Lightbox** (строки 69-79, 127-134) — скопировать без изменений.

**Паттерн JSX-ветвления** — вместо одного `filtered.map(...)` сделать ветку:
```tsx
{isFlat
  ? /* плоский список flatFiltered.map(product => <ProductCard .../>) */
  : /* grouped: Array.from(grouped.entries()).map([section, subMap] => (
       <>
         <h2 id={`section-${section}`}>…раздел…</h2>
         {Array.from(subMap.entries()).map([subgroup, items] => (
           <>
             <h3>…подгруппа + счётчик…</h3>
             <div className={containerClass}>
               {items.map(p => <ProductCard .../>)}
             </div>
           </>
         ))}
       </>
     )) */
}
```

---

### `components/SectionBar.tsx` (новый компонент, event-driven + scroll-spy)

**Аналоги:**
1. `components/CategoryFilter.tsx` — sticky-контейнер и стили кнопок-таблеток
2. `components/ScrollToTop.tsx` — паттерн `useEffect` + `window.addEventListener` для отслеживания позиции прокрутки

Это новый файл, создаётся с нуля. Паттерны — см. раздел `CategoryFilter.tsx` выше.

**Скелет файла** (все паттерны уже описаны выше):
```typescript
"use client";

import { useEffect, useState } from "react";

// Прилипающая полоса разделов с scroll-spy и плавной перемоткой по якорям
interface SectionBarProps {
  sections: string[];
  activeSection: string;
  onSectionChange: (section: string) => void;
}

export default function SectionBar({ sections, activeSection, onSectionChange }: SectionBarProps) {
  // IntersectionObserver — паттерн из ScrollToTop.tsx (useEffect + cleanup)
  // sticky div — паттерн из CategoryFilter.tsx (строки 14-16)
  // кнопки-таблетки — паттерн из CategoryFilter.tsx (строки 27-39)
}
```

---

### `app/catalog/[secret]/page.tsx` (route, request-response)

**Аналог:** `app/catalog/[secret]/page.tsx` (текущий, строки 1-28)

Минимальные изменения: убрать `initialCategory` из пропсов `CatalogView` (D-06 — группировка в данных, не в URL).

**Паттерн revalidate + getProducts + notFound** (строки 1-28) — скопировать полностью:
```typescript
import { notFound } from "next/navigation";
import { getProducts } from "@/lib/sheets";
import CatalogView from "@/components/CatalogView";

export const revalidate = 300;

export default async function CatalogPage({ params, searchParams }: {
  params: { secret: string };
  searchParams: { filter?: string };
}) {
  if (params.secret !== process.env.CATALOG_SECRET) {
    notFound();
  }

  const allProducts = await getProducts();

  let products = allProducts;
  if (searchParams.filter === "hit") {
    products = allProducts.filter((p) => p.badge === "хит");
  } else if (searchParams.filter === "new") {
    products = allProducts.filter((p) => p.badge === "новинка");
  }

  // ИЗМЕНИТЬ: убрать initialCategory={...} из пропсов
  return <CatalogView products={products} />;
}
```

---

## Shared Patterns

### "use client" — клиентские компоненты
**Источник:** `components/CatalogView.tsx` строка 1, `components/CategoryFilter.tsx` строка 1, `components/ScrollToTop.tsx` строка 1
**Применять к:** `SectionBar.tsx`, обновлённым `CatalogView.tsx`, `CategoryFilter.tsx`
```typescript
"use client";
```
Все интерактивные компоненты (состояние, события, DOM-API) требуют директивы. `page.tsx` — серверный компонент, директива не нужна.

---

### Sticky-полоса под шапкой
**Источник:** `components/CategoryFilter.tsx` строки 14-16
**Применять к:** `SectionBar.tsx`

Шапка `layout.tsx` имеет `sticky top-0 z-50` и высоту `h-12` (48px). Полоса разделов должна прилипать под ней:
```tsx
<div className="sticky top-12 z-10 bg-white border-b border-gray-200 shadow-sm">
  <div className="flex gap-2 px-4 py-2.5 overflow-x-auto scrollbar-hide">
```
Ключевой момент: `top-12` (не `top-0`) чтобы не перекрывать шапку.

---

### useMemo для вычислений из массива products
**Источник:** `components/CatalogView.tsx` строки 44-67
**Применять к:** обновлённому `CatalogView.tsx`

```typescript
const derived = useMemo(() => {
  // вычисление из products — группировка, фильтрация
  // зависимости: [products, search, ...]
}, [products, search]);
```
Все вычисления структуры разделов/подгрупп — через `useMemo`, без `useEffect`.

---

### useEffect + addEventListener для scroll-событий
**Источник:** `components/ScrollToTop.tsx` строки 16-41
**Применять к:** `SectionBar.tsx` (scroll-spy через IntersectionObserver)

```typescript
useEffect(() => {
  // подписка на событие
  window.addEventListener("scroll", handler, { passive: true });
  return () => {
    // обязательная очистка при unmount
    window.removeEventListener("scroll", handler);
  };
}, [dependencies]);
```
Паттерн: подписка в `useEffect`, очистка в `return`.

---

### Стили заголовков разделов/подгрупп
**Источник:** UI-конвенции проекта (синяя шапка `bg-blue-600`, серые границы `border-gray-200`)
**Применять к:** заголовкам разделов и подгрупп в `CatalogView.tsx`

Раздел — крупный жирный (консистентно с шапкой):
```tsx
<h2 className="text-lg font-bold text-gray-800 px-4 pt-5 pb-2">
  {section}
</h2>
```

Подгруппа — поменьше, со счётчиком:
```tsx
<h3 className="text-sm font-semibold text-gray-500 px-4 pt-3 pb-1.5 uppercase tracking-wide">
  {subgroup} <span className="font-normal text-gray-400">({count})</span>
</h3>
```

---

### Якорные id для scroll-to-anchor
**Применять к:** заголовкам разделов в `CatalogView.tsx`

Формат id: `section-${section}` — строго однозначный, используется и для IntersectionObserver в `SectionBar`, и для `scrollIntoView` по клику:
```tsx
<h2 id={`section-${section}`} ...>
```

---

## No Analog Found

Файлов без аналога нет. Все новые/изменяемые файлы имеют прямые аналоги в кодовой базе.

Единственный по-настоящему новый файл — `SectionBar.tsx` — собирается из двух существующих аналогов:
- sticky + стили кнопок → `CategoryFilter.tsx`
- scroll-отслеживание useEffect → `ScrollToTop.tsx`

---

## Metadata

**Область поиска аналогов:** `components/`, `lib/`, `app/catalog/[secret]/`
**Файлов просмотрено:** 11
**Дата маппинга:** 2026-06-09
