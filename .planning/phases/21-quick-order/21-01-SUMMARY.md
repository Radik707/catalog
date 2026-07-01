---
phase: 21-quick-order
plan: "01"
subsystem: frontend
tags: [quick-order, getUnit, QuickOrderRow, cart, packaging]
dependency_graph:
  requires: []
  provides: [lib/getUnit.ts, components/QuickOrderRow.tsx]
  affects: [components/CatalogView.tsx, components/CatalogSettings.tsx, components/SettingsPanel.tsx]
tech_stack:
  added: [getUnit helper, QuickOrderRow component]
  patterns: [SSR-safe role gate (ready flag), kap po stock cherez useCart/AddToCartButton, inline quantity via AddToCartButton]
key_files:
  created:
    - lib/getUnit.ts
    - components/QuickOrderRow.tsx
  modified: []
decisions:
  - "D-06: getUnit(product) — единственная точка чтения единицы товара; возвращает строку с предлогом как есть (обратная совместимость с ProductCard)"
  - "D-03: QuickOrderRow без флипа, галереи и CardCornerButton — только плотная строка"
  - "D-07/D-08: AddToCartButton переиспользован целиком — кап по stock не дублируется в строке"
metrics:
  duration: "~25 min"
  completed: "2026-07-01"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 0
---

# Phase 21 Plan 01: getUnit + QuickOrderRow — строительные блоки быстрого набора

**One-liner:** Хелпер `getUnit(product)` как шов под этап 21b и компонент `QuickOrderRow` — плотная flex-строка с мини-фото 56×56, названием, ценой с подписью единицы и `AddToCartButton` для инлайн-количества.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Хелпер getUnit — единая точка чтения единицы (D-06) | 6316118 | lib/getUnit.ts |
| 2 | Компонент QuickOrderRow — плотная строка быстрого набора | f47280e | components/QuickOrderRow.tsx |

## Decisions Made

- **D-06 подтверждён:** `getUnit(product)` возвращает строку с предлогом («за шт», «за блок» и т.д.) как есть из `getPackaging()` — без срезания «за ». Потребители срезают на месте если нужно (например `cart/page.tsx` для снимка заказа). Обратная совместимость с `ProductCard` сохранена.
- **AddToCartButton переиспользован целиком** (D-07/D-08): в `QuickOrderRow` нет собственной логики «+/−» и нет нового `Math.min` по `stock` — всё уже внутри `AddToCartButton` и `useCart`.
- **PhotoPlaceholder локальная:** `PhotoPlaceholder` из `ProductCard` не экспортируется — создан собственный мини-вариант в `QuickOrderRow.tsx` с той же SVG-иконкой. Выносить в общий файл не требовалось (план не трогает витрину).

## What Was Built

### `lib/getUnit.ts`
Тонкий хелпер-«шов» над `getPackaging(group, name)`:
- Принимает `Product`, возвращает `string` (подпись единицы с предлогом или `""`)
- Единственная точка под будущее расширение в этапе 21b (приоритет ручной правки из админ-панели)
- Весь фронт этапа 21 читает единицу только через этот хелпер

### `components/QuickOrderRow.tsx`
Клиентский компонент `"use client"` для режима «Быстрый набор»:
- Пропсы: `{ product: Product; priceForm: PriceForm }`
- Раскладка: `flex items-center gap-3` — миниатюра слева, название+остаток в центре, цена+кнопка справа
- Миниатюра `w-14 h-14` с `Image unoptimized` (SW-совместимый Cloudinary URL) и `onError` → `PhotoPlaceholder`
- Цена через `effectivePrice(product, priceForm)`, подпись единицы через `getUnit(product)` (рендерится только если непустая)
- Остаток: «N шт» при наличии / «Нет в наличии» — скромно, как в режиме «Список» (числовой остаток и фильтр — этап 22)
- Инлайн-количество: готовый `<AddToCartButton product={product} />` — сам показывает «+» и «− N +» с капом по stock

## Verification

- `npx tsc --noEmit` — 0 ошибок (оба новых файла)
- `npm run build` — код 0, `✓ Compiled successfully`
- `grep -E "Lightbox|onFlipChange|CardCornerButton" components/QuickOrderRow.tsx` — пусто (запрещённых импортов нет)
- Кап по stock не продублирован в `QuickOrderRow` — нет `Math.min` по `stock`, только `AddToCartButton`

## Deviations from Plan

Нет — план выполнен точно как написано.

## Threat Flags

Нет — новые файлы не добавляют серверных поверхностей, не меняют данные, не открывают новых trust-границ.

## Known Stubs

Нет — оба артефакта самодостаточны. `QuickOrderRow` рендерит реальные данные из `product`; подключение к витрине (CatalogView, CatalogSettings, SettingsPanel) — волна 2, план 02.

## Self-Check: PASSED

- [x] `lib/getUnit.ts` существует
- [x] `components/QuickOrderRow.tsx` существует
- [x] Коммит 6316118 существует (getUnit)
- [x] Коммит f47280e существует (QuickOrderRow)
- [x] `npm run build` — код 0
