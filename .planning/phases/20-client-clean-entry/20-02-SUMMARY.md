---
phase: 20-client-clean-entry
plan: "02"
subsystem: shared-components
tags: [refactor, plural, reorder-modal, orders-page]
dependency_graph:
  requires: []
  provides: [components/ReorderSummaryModal.tsx, lib/plural.ts]
  affects: [app/catalog/[secret]/orders/page.tsx]
tech_stack:
  added: []
  patterns: [extract-shared-module, named-exports-utility]
key_files:
  created:
    - lib/plural.ts
    - components/ReorderSummaryModal.tsx
  modified:
    - app/catalog/[secret]/orders/page.tsx
decisions:
  - "pluralGoods используется внутри ReorderSummaryModal, в orders/page не нужен — не импортирован лишний"
  - "Тела функций склонения перенесены дословно без изменений логики (n%10/n%100)"
  - "Комментарий-заглушка оставлен в конце orders/page для ориентира о вынесенном коде"
metrics:
  duration: "~10 минут"
  completed_date: "2026-06-30"
  tasks_completed: 3
  files_changed: 3
---

# Этап 20 Plan 02: Рефакторинг — вынос ReorderSummaryModal и склонений

**Одной строкой:** Вынесены `ReorderSummaryModal` в `components/ReorderSummaryModal.tsx` и функции склонения `pluralGoods/pluralOrders/pluralItems` в `lib/plural.ts`; `orders/page.tsx` переключён на общие импорты без изменения поведения.

## Что сделано

### Задача 1: lib/plural.ts
Создан новый файл `/c/catalog/lib/plural.ts` с тремя именованными экспортами:
- `pluralOrders(n)` — заказ/заказа/заказов
- `pluralItems(n)` — позиция/позиции/позиций
- `pluralGoods(n)` — товар/товара/товаров

Тела функций перенесены дословно из `orders/page.tsx` (строки 479-501). Чистые функции без состояния и побочных эффектов. Коммит: `eb2f33b`.

### Задача 2: components/ReorderSummaryModal.tsx
Создан клиентский компонент `components/ReorderSummaryModal.tsx`:
- `"use client"` — клиентский компонент (JSX + onClick/state из пропса)
- `export default function ReorderSummaryModal({ result, secret, onClose })`
- Вёрстка перенесена дословно из `orders/page.tsx` (строки 307-475)
- Импортирует `ReorderResult` из `@/lib/reorder` и `pluralGoods` из `@/lib/plural`
- Сохранены: `paddingBottom: calc(env(safe-area-inset-bottom, 0px) + 5rem)`, все цвета иконок исходов (`text-green-500/text-blue-500/text-gray-400/text-red-400/text-amber-500`)
- Кнопка «Перейти в корзину →» рендерится только при `addedCount > 0`

Коммит: `567c2c9`.

### Задача 3: orders/page.tsx — переход на общие модули
Добавлены импорты:
- `import ReorderSummaryModal from '@/components/ReorderSummaryModal'`
- `import { pluralOrders, pluralItems } from '@/lib/plural'` (`pluralGoods` используется внутри модалки)

Удалены из файла:
- Локальная функция `ReorderSummaryModal` (строки 307-475) — 168 строк
- Три функции склонения `pluralOrders/pluralItems/pluralGoods` (строки 477-501) — 25 строк

Итого файл сократился на 195 строк при неизменном поведении.
`npm run build` — прошёл без ошибок типов и линта.

Коммит: `cad7714`.

## Коммиты

| Задача | Хэш | Сообщение |
|--------|-----|-----------|
| 1 | `eb2f33b` | refactor(этап-20): вынести утилиты склонения в lib/plural.ts |
| 2 | `567c2c9` | refactor(этап-20): вынести ReorderSummaryModal в общий компонент |
| 3 | `cad7714` | refactor(этап-20): orders/page переходит на общие модули |

## Отклонения от плана

Нет — план выполнен точно как написано.

## Known Stubs

Нет. Весь перенесённый код — рабочая функциональность без заглушек.

## Threat Flags

Нет новых поверхностей. Рефакторинг не добавил сетевых вызовов, новых путей к данным или изменений схемы. T-20-04 (Tampering) и T-20-05 (Information Disclosure) из плана — приняты без дополнительных действий (перенос дословный, React экранирует текст).

## Self-Check: PASSED

- [x] `lib/plural.ts` существует и экспортирует pluralOrders/pluralItems/pluralGoods
- [x] `components/ReorderSummaryModal.tsx` существует, клиентский, дефолтный экспорт
- [x] `orders/page.tsx` импортирует оба модуля, локальные копии удалены
- [x] `npm run build` — прошёл без ошибок
- [x] Все три коммита существуют в git log
