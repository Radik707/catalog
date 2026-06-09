---
phase: 06-1
plan: 02
subsystem: ui
tags: [next.js, typescript, navigation, scroll-spy, anchor, tailwind]

# Dependency graph
requires:
  - phase: 06-1
    plan: 01
    provides: "Product.subgroup / Product.section из Google Sheet (колонки J/K)"
provides:
  - "SectionBar.tsx — прилипающая полоса разделов со scroll-spy и плавной перемоткой"
  - "CatalogView.tsx — группировка раздел→подгруппа в порядке данных, ветка плоского списка"
  - "page.tsx — передаёт isFiltered вместо initialCategory"
affects:
  - "Витрина каталога /catalog/[secret] — двухуровневая навигация активна"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "IntersectionObserver rootMargin -50%/0/-50%/0 — scroll-spy активного раздела"
    - "scrollIntoView behavior:smooth — плавная перемотка к якорю section-{name}"
    - "Map<string, Map<string, Product[]>> порядок вставки = порядок разделов"
    - "useCallback для мемоизации onSectionChange — стабильная ссылка в dep-массиве"
    - "Ветка isFlat: Boolean(search.trim()) || isFiltered — плоский список"

key-files:
  created:
    - components/SectionBar.tsx
  modified:
    - components/CatalogView.tsx
    - app/catalog/[secret]/page.tsx

key-decisions:
  - "Порядок разделов из данных через Map (порядок вставки), GROUP_ORDER удалён (D-04)"
  - "Товары с пустым section → «Новинки», гарантированно первый раздел (D-05)"
  - "isFlat = search || isFiltered — единая ветка для поиска и фильтра Хит/Новинка (D-06)"
  - "useCallback(handleSectionChange) — предотвращает пересоздание IntersectionObserver при каждом рендере"

# Metrics
duration: 20min
completed: 2026-06-09
---

# Phase 6, Plan 02: Двухуровневая навигация на витрине — Summary

**Прилипающая полоса разделов со scroll-spy + единая прокручиваемая страница раздел→подгруппа, плоский список при поиске/фильтрах; npm run build: 0 ошибок**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-06-09
- **Tasks:** 4 (3 кода + 1 checkpoint визуальной проверки — ожидает одобрения)
- **Files created:** 1 (SectionBar.tsx)
- **Files modified:** 2 (CatalogView.tsx, page.tsx)

## Accomplishments

- **SectionBar.tsx** — новый клиентский компонент. `sticky top-12` (под синей шапкой h-12), кнопки-таблетки в стиле CategoryFilter, IntersectionObserver scroll-spy с rootMargin -50%/0/-50%/0, плавная перемотка scrollIntoView({behavior:"smooth"}) по клику, обязательный `observer.disconnect()` в cleanup.

- **CatalogView.tsx** — полностью перестроен. Удалён `GROUP_ORDER` и параметр `initialCategory`. Группировка `Map<string, Map<string, Product[]>>` в порядке первого появления — порядок разделов приходит из данных (upload.py уже сортирует по structure_map.json). «Новинки» принудительно первым разделом (D-05). Ветка `isFlat` скрывает SectionBar и заголовки при поиске ИЛИ активном фильтре (D-06). Заголовки `<h2 id="section-{name}">` и `<h3>` с счётчиком `({items.length})`. ProductCard, Lightbox, CatalogSettings, SearchBar, ScrollToTop — неизменны.

- **page.tsx** — убрана передача `initialCategory`; добавлен флаг `isFiltered` (фильтр hit/new → плоский список); проверка CATALOG_SECRET и notFound() сохранены.

- **npm run build** прошёл без ошибок (exit 0).

## Task Commits

| Task | Описание | Коммит |
|------|----------|--------|
| 1 | Создать SectionBar | `783aa3f` |
| 2 | Перестроить CatalogView | `19e985a` |
| 3 | Очистить page.tsx + build | `482bd09` |

## Files Created/Modified

- `components/SectionBar.tsx` (создан, 76 строк) — прилипающая полоса разделов
- `components/CatalogView.tsx` (перестроен, 197 строк) — двухуровневая группировка
- `app/catalog/[secret]/page.tsx` (обновлён, 35 строк) — isFiltered, убран initialCategory

## Decisions Made

- **D-04 выполнен:** GROUP_ORDER удалён, порядок разделов = порядок вставки в Map = порядок данных из Sheet (upload.py сортирует по structure_map.json)
- **D-05 выполнен:** `p.section || "Новинки"` + принудительная расстановка «Новинки» первым через пересборку Map
- **D-06 выполнен:** `isFlat = Boolean(search.trim()) || isFiltered` — единая ветка плоского списка скрывает SectionBar и якорные заголовки

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Ошибка итерации Map без --downlevelIteration**
- **Found during:** Task 2, npx tsc --noEmit
- **Issue:** `for (const [k, v] of map)` давал TS2802 при target без явного es2015
- **Fix:** Заменено на `Array.from(map.entries()).forEach(...)` — совместимо со всеми target
- **Files modified:** components/CatalogView.tsx
- **Commit:** 19e985a (в рамках одного коммита с задачей)

## Known Stubs

Нет — все данные живые (Product.section/subgroup из Google Sheet).

## Threat Flags

Новой поверхности атаки нет (аналитика угроз из плана — T-06-03, T-06-04, T-06-05 обработаны):
- CATALOG_SECRET gate сохранён без изменений
- section/subgroup рендерятся как React-текст, не через dangerouslySetInnerHTML
- id-якоря формируются из доверенных данных Sheet

## Checkpoint Status

Task 4 (визуальная проверка) — ожидает одобрения владельца. Требует `npm run dev` и ручной проверки на телефоне/мобильной эмуляции.

## Self-Check: PASSED

- [x] `components/SectionBar.tsx` — существует, содержит `IntersectionObserver`, `top-12`, `section-`, `disconnect()`
- [x] `components/CatalogView.tsx` — импортирует SectionBar, не содержит GROUP_ORDER/initialCategory, группирует по section/subgroup
- [x] `app/catalog/[secret]/page.tsx` — не передаёт initialCategory, передаёт isFiltered, gate CATALOG_SECRET цел
- [x] `npm run build` — exit 0
- [x] Коммиты 783aa3f, 19e985a, 482bd09 — существуют в git log
