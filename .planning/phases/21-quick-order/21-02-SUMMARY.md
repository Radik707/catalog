---
phase: 21-quick-order
plan: "02"
subsystem: frontend
tags: [quick-order, ViewMode, CatalogView, SettingsPanel, CatalogSettings, role-gate, SSR-safe]
dependency_graph:
  requires: [21-01]
  provides: [режим-quick-в-витрине, гейт-роли-sales-в-панели]
  affects: [components/CatalogView.tsx, components/CatalogSettings.tsx, components/SettingsPanel.tsx, app/catalog/[secret]/cart/page.tsx]
tech_stack:
  added: []
  patterns: [SSR-safe role gate (ready flag), effectiveMode fallback, visibleViews derived list]
key_files:
  created: []
  modified:
    - components/CatalogSettings.tsx
    - components/SettingsPanel.tsx
    - components/CatalogView.tsx
    - app/catalog/[secret]/cart/page.tsx
decisions:
  - "D-01/D-02 подтверждены: дефолт остаётся presentation; quick недоступен без ready && role === sales"
  - "D-09 подтверждён: виртуализация НЕ введена; оставлен комментарий-заметка о будущем шаге"
  - "D-10 выполнен: снимок заказа несёт реальную единицу через getUnit().replace(/^за\\s+/i, '') || шт"
  - "effectiveMode как единственная точка откатного гейта в CatalogView — viewMode не меняется, только рендер"
  - "visibleViews derived list в SettingsPanel — базовый views без quick, гейт вынесен в производный список"
metrics:
  duration: "~30 min"
  completed: "2026-07-01"
  tasks_completed: 4
  tasks_total: 4
  files_created: 0
  files_modified: 4
---

# Phase 21 Plan 02: Подключение QuickOrderRow в витрину — 4-й режим «Быстрый набор»

**One-liner:** Режим `quick` подключён как 4-й вариант ViewMode: виден только роли `sales` через SSR-safe гейт, рендерит плотные строки `QuickOrderRow`, клиентский опыт не задет.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | ViewMode "quick" + валидация localStorage (QORD-01) | 8afd32f | components/CatalogSettings.tsx |
| 2 | Пункт меню «Быстрый набор» под гейтом роли sales (QORD-04) | 2add406 | components/SettingsPanel.tsx |
| 3 | Ветка рендера quick в CatalogView + SSR-safe гейт (QORD-01, QORD-04, QORD-05) | 6261e80 | components/CatalogView.tsx |
| 4 | Реальная единица в снимке заказа (D-10, опционально) | f9e3a3a | app/catalog/[secret]/cart/page.tsx |

## Decisions Made

- **effectiveMode** — введена производная переменная в `CatalogView`: если `viewMode === "quick"` и `!(ready && role === "sales")` → откат к `"presentation"`. Сам `viewMode` в стейте остаётся нетронутым (восстановится корректно при смене роли на sales).
- **visibleViews derived list** — в `SettingsPanel` базовый `views` не содержит пункта quick; производный `visibleViews` добавляет его только при `ready && role === "sales"`. Гейт однозначен и обслуживается в одном месте.
- **D-09 confirmed** — виртуализация не вводится; `quick` использует тот же `flex-1` контейнер что и `list`, рендерит тот же плоский маппинг через `renderCard`. Комментарий-заметка в коде указывает `react-virtual` как следующий шаг при реальных тормозах.
- **D-10 executed** — опциональная задача выполнена: `buildOrderSnapshot` в cart/page.tsx расширен до `Product`, `unit` вычисляется через `getUnit(product).replace(/^за\\s+/i, "") || "шт"`.

## What Was Built

### `components/CatalogSettings.tsx`
- Тип `ViewMode` расширен: `"list" | "grid" | "presentation" | "quick"` (русский комментарий)
- Валидация при чтении localStorage: принимает `"quick"` (добавлен `|| v === "quick"`)
- Дефолт `useState<ViewMode>("presentation")` — не изменён (D-01/D-02)

### `components/SettingsPanel.tsx`
- Производный список `visibleViews`: при `ready && role === "sales"` добавляет `{ key: "quick", label: "⚡ Набор" }` в конец базового `views`
- Рендер кнопок режимов маппит `visibleViews` (не исходный `views`)
- Базовый `views` без quick — гейт вынесен из массива в производный список

### `components/CatalogView.tsx`
- Импорт `QuickOrderRow` из `@/components/QuickOrderRow`
- `effectiveMode` — SSR-safe откат к `presentation` для не-sales/не-ready
- `containerClass` — ветка `effectiveMode === "list" || effectiveMode === "quick"` → `"flex-1"` (плотный список)
- `renderCard` — при `effectiveMode === "quick"` возвращает `<QuickOrderRow product={product} priceForm={priceForm} />`, иначе `<ProductCard ...>` с `effectiveMode` вместо `viewMode`
- `<ScrollToTop>` — для quick передаёт `"list"` (тот же порог прокрутки)
- Комментарий-заметка о виртуализации (D-09, QORD-05)

### `app/catalog/[secret]/cart/page.tsx`
- Импорт `getUnit` из `@/lib/getUnit` и типа `Product`
- `buildOrderSnapshot`: параметр `product` расширен до `Product` (нужны `group`/`name`)
- `unit` вычисляется как `getUnit(product).replace(/^за\\s+/i, "") || "шт"` вместо жёсткого `"шт"`

## Verification

- `npx tsc --noEmit` — 0 ошибок на всех 4 файлах
- `npm run build` — код 0, Compiled successfully
- `grep -q "QuickOrderRow" components/CatalogView.tsx` — найдено (импорт + рендер)
- `grep -q "effectiveMode" components/CatalogView.tsx` — найдено
- `grep -E 'ready && role === "sales"' components/CatalogView.tsx` — найдено
- `grep -q "visibleViews" components/SettingsPanel.tsx` — найдено
- `grep -E 'ViewMode = .*"quick"' components/CatalogSettings.tsx` — найдено
- `grep -q "getUnit" app/catalog/\\[secret\\]/cart/page.tsx` — найдено

## Deviations from Plan

### Уточнение типа в renderCard

**Task 3** — при создании ветки `effectiveMode !== "quick"` в `renderCard` передавали `viewMode` в `ProductCard`. Вместо этого передаётся `effectiveMode` приведённый к допустимым значениям `list | grid | presentation`. Это обеспечивает корректное поведение ProductCard когда `viewMode === "quick"` но роль меняется: пока `effectiveMode` показывает `presentation`, `ProductCard` получает правильный пропс.

Классификация: **[Rule 2 - Auto-add missing critical functionality]** — без этого исправления ProductCard получал бы значение `"quick"` в проп `viewMode`, что он не ожидает.

## Threat Flags

Нет — правки только клиентские (ViewMode тип, пункт меню, ветка рендера, снимок заказа). Серверных поверхностей не добавляется. Гейт роли — UX-пресет, не граница безопасности (T-21-03 accepted: клиент видит те же товары/цены в любом режиме).

## Known Stubs

Нет — все 4 файла работают с реальными данными. `QuickOrderRow` рендерит данные из `product`, режим quick переключается через `SettingsPanel`, unit в снимке заказа вычисляется через `getUnit`.

## Self-Check: PASSED

- [x] `components/CatalogSettings.tsx` содержит `"quick"` в ViewMode и `v === "quick"` в валидации
- [x] `components/SettingsPanel.tsx` содержит `visibleViews` и гейт `ready && role === "sales"`
- [x] `components/CatalogView.tsx` импортирует QuickOrderRow, содержит `effectiveMode`, рендерит QuickOrderRow при `effectiveMode === "quick"`
- [x] `app/catalog/[secret]/cart/page.tsx` импортирует `getUnit`, unit через `getUnit().replace(...)`
- [x] Коммит 8afd32f (Task 1) существует
- [x] Коммит 2add406 (Task 2) существует
- [x] Коммит 6261e80 (Task 3) существует
- [x] Коммит f9e3a3a (Task 4) существует
- [x] `npm run build` — код 0
