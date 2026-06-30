---
phase: 20-client-clean-entry
plan: "03"
subsystem: catalog-client-ux
tags: [feature, search-history, reorder, localStorage, offline-safe]
dependency_graph:
  requires: [components/ReorderSummaryModal.tsx, lib/plural.ts, lib/reorder.ts, components/OrderHistoryProvider.tsx]
  provides: [lib/useSearchHistory.ts, components/SearchBar.tsx (history), components/CatalogView.tsx (repeat+history)]
  affects: [app/catalog/[secret]/page.tsx (CatalogView), components/SearchBar.tsx]
tech_stack:
  added: []
  patterns: [localStorage-hook-fifo, ssr-safe-role-gate, usePathname-secret, onPointerDown-blur-prevention]
key_files:
  created:
    - lib/useSearchHistory.ts
  modified:
    - components/SearchBar.tsx
    - components/CatalogView.tsx
decisions:
  - "secret извлекается из usePathname() внутри CatalogView — без проброса пропом из page.tsx (паттерн SettingsPanel)"
  - "Запись поискового запроса — debounce 800мс на непустое значение (не при blur — blur-логика в SearchBar уже занята выпадашкой)"
  - "В SearchBar используется onPointerDown вместо onClick для предотвращения потери фокуса до срабатывания тапа по пункту истории"
  - "Гейт строки повтора: ready && role === 'client' && orderEntries.length > 0 (T-20-10 mitigated)"
  - "useSearchHistory вызывается безусловно в CatalogView (правило хуков), данные уходят в SearchBar как пропсы"
metrics:
  duration: "~30 минут"
  completed_date: "2026-06-30"
  tasks_completed: 3
  files_changed: 3
---

# Этап 20 Plan 03: Строка повтора + история поиска

**Одной строкой:** Над каталогом у client появилась компактная строка «↻ Повторить последний заказ» (classifyReorder → addToCartWithQuantity → ReorderSummaryModal); в поиске при фокусе выпадает список недавних запросов из нового localStorage-хука useSearchHistory.

## Что сделано

### Задача 1: lib/useSearchHistory.ts

Создан новый хук истории поиска по точному образцу `useOrderHistory.ts` (1:1 структура):
- Ключ `catalog-search-history`, потолок 10 запросов
- SSR-гейт `typeof window === 'undefined' → []`
- `try/catch` на чтении и записи (приватный режим iOS, T-20-06)
- Мягкая деградация: битый JSON → `[]`, нестроковые записи фильтруются
- Дедуп регистронезависимо, свежие запросы сверху (`[q, ...without]`)
- Методы `addQuery` / `removeQuery` / `clearHistory` через `useCallback`
- load-on-mount + save-on-change + isLoaded-флаг

Коммит: `2d28385`.

### Задача 2: components/SearchBar.tsx

Расширен опциональными пропсами истории (`history?`, `onPickHistory?`, `onRemoveHistory?`, `onClearHistory?`):
- Вызов без пропсов истории (ветка loading в CatalogView) компилируется
- Локальный `focused` стейт; выпадашка появляется при `focused && history.length > 0 && !value.trim()`
- Выпадашка: `absolute top-full left-0 right-0 z-40`, `bg-white rounded-xl shadow-lg border border-gray-100`
- Заголовок «Недавние запросы» + «Очистить» (`text-red-500 font-medium`)
- Пункт: иконка-часы слева, текст запроса, крестик ✕ с `e.stopPropagation()`
- `onPointerDown` + `e.preventDefault()` для предотвращения blur до срабатывания тапа
- `aria-label` на кнопке очистки инпута, очистки истории и крестиках удаления
- Placeholder и крестик очистки инпута не изменены

Коммит: `3b78e13`.

### Задача 3: components/CatalogView.tsx

Добавлены импорты и хуки (все ВЫШЕ ранних return):
- `useRole()` → `{ role, ready }` — гейт строки повтора
- `useOrderHistoryContext()` → `orderEntries` — последний заказ для повтора
- `useCartContext()` → `addToCartWithQuantity` — добавление в корзину
- `classifyReorder`, `ReorderResult` — логика повтора из lib/reorder
- `ReorderSummaryModal` — общая модалка сводки (план 20-02)
- `useSearchHistory()` → `searchEntries`, `addQuery`, `removeQuery`, `clearHistory`
- `usePathname()` → извлечение secret через regex `/\/catalog\/([^/]+)/`

Строка повтора (HOME-02):
- Гейт: `ready && role === 'client' && orderEntries.length > 0`
- Между SearchBar и контентом, высота ~40px (`py-2 px-4 bg-white border-b border-gray-100`)
- Кнопка CTA: `bg-blue-600 text-white text-sm font-semibold rounded-xl active:bg-blue-700`
- Обработчик `handleRepeatLast` по образцу `handleRepeat` в orders/page.tsx

История поиска (SRCH-01):
- Запись по debounce 800мс на непустое значение через `useEffect`
- Пропсы `history/onPickHistory/onRemoveHistory/onClearHistory` пробрасываются в SearchBar

Модалка: `{reorderSummary && <ReorderSummaryModal ... />}` в конце JSX.

`npm run build` — зелёный без ошибок.

Коммит: `7a2c665`.

## Коммиты

| Задача | Хэш | Сообщение |
|--------|-----|-----------|
| 1 | `2d28385` | feat(этап-20): создать хук useSearchHistory — история поиска в localStorage |
| 2 | `3b78e13` | feat(этап-20): SearchBar — выпадашка недавних запросов при фокусе |
| 3 | `7a2c665` | feat(этап-20): CatalogView — строка повтора + проводка истории поиска |

## Отклонения от плана

Нет — план выполнен точно как написан.

**Авто-решения (без изменения плана):**
- Переменная с историей заказов названа `orderEntries` (не `entries`) во избежание конфликта с `searchEntries` от useSearchHistory — это единственное именование, не конфликтующее в одном scope.

## Отложенная приёмка (после деплоя)

Задача 4 плана — `checkpoint:human-verify` — не может быть выполнена локально. Приёмку проводить ПОСЛЕ `git push` → Vercel автодеплой:

**Что проверить (на проде, роль «Клиент»):**

1. **Строка повтора:** если есть история заказов — над каталогом видна ОДНА компактная строка «↻ Повторить последний заказ». Если истории нет — строки нет вовсе.
2. **Тап по строке:** корзина пополняется, появляется сводка «Добавлено N товаров» с列списком пропущенных/изменённых; кнопка «Перейти в корзину →». Нигде нет слов «статус/принято».
3. **Нечего добавить:** если ни одной позиции добавить нельзя — честное сообщение, кнопка перехода в корзину НЕТ.
4. **История поиска:** набрать 2-3 запроса → снова тапнуть в пустое поле → выпадает список; тап по запросу подставляет его; крестик ✕ удаляет; «Очистить» убирает весь список.
5. **Офлайн:** после первой загрузки включить авиарежим — строка повтора и история поиска работают.
6. **Роль «Торговый»:** строки повтора над каталогом быть НЕ должно.

**Сигнал приёмки:** напишите «принято» или опишите проблему.

## Known Stubs

Нет. Весь код — рабочая функциональность без заглушек.

## Threat Flags

Новых поверхностей нет. Все угрозы из threat_model плана 20-03 покрыты:
- T-20-06 (Tampering/search-history): `loadHistory()` фильтрует нестроки, try/catch, React экранирует текст
- T-20-07 (Tampering/order-history→повтор): classifyReorder против актуального каталога — битые/несуществующие позиции → unavailable
- T-20-08 (Information Disclosure): в localStorage только запросы/история заказов, не секреты
- T-20-09 (DoS/сеть): нет новых сетевых вызовов — всё читает localStorage/IndexedDB
- T-20-10 (DoS/гидратация): гейт `ready && role==='client'` — до ready строка не рисуется

## Self-Check: PASSED

- [x] `lib/useSearchHistory.ts` существует, экспортирует `useSearchHistory`, содержит ключ `catalog-search-history`, методы `addQuery`/`removeQuery`/`clearHistory`, SSR-гейт
- [x] `components/SearchBar.tsx` содержит опциональные пропсы `history?`, `onPickHistory`, `text-red-500`, placeholder `Поиск товара...`
- [x] `components/CatalogView.tsx` содержит `useSearchHistory`, `useOrderHistoryContext`, `classifyReorder`, `ReorderSummaryModal`, «Повторить последний заказ», гейт `role === 'client'`
- [x] `npm run build` — зелёный, без ошибок типов и линта
- [x] Все три коммита существуют в git log (2d28385, 3b78e13, 7a2c665)
