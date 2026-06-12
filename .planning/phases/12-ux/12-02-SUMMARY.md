---
phase: 12-ux
plan: "02"
subsystem: offline-ux
tags: [offline, pwa, ux, cart, telegram, order]
dependency_graph:
  requires: [12-01]
  provides: [offline-order-guard, offline-cart-verified]
  affects:
    - app/catalog/[secret]/cart/page.tsx
    - components/TelegramButton.tsx
tech_stack:
  added: []
  patterns: [useOnlineStatus-consumer, disabled-button-offline, localStorage-cart]
key_files:
  created: []
  modified:
    - app/catalog/[secret]/cart/page.tsx
    - components/TelegramButton.tsx
decisions:
  - "[12-02] Обе кнопки отправки заказа потребляют useOnlineStatus() из плана 12-01 — единый источник статуса сети"
  - "[12-02] Локальная кнопка: disabled + постоянная подпись D-05 «Корзина сохранена» под кнопкой в офлайне"
  - "[12-02] Плавающая кнопка: onClick=undefined в офлайне + opacity-50, условные title/aria-label — не открывает Telegram без сети"
  - "[12-02] CART-01: корзина работает офлайн через localStorage (loadCart/saveCart с SSR-guard) — изменений кода не потребовалось (D-06)"
  - "[12-02] Нейтральное приглушение без красного цвета (D-03) — офлайн это рабочая норма, не авария"
metrics:
  completed_date: "2026-06-12"
  tasks_completed: 2
  tasks_deferred: 1
  files_created: 0
  files_modified: 2
requirements: [CART-01, CART-02]
checkpoint_status: deferred
---

# Phase 12 Plan 02: Офлайн-защита отправки заказа — Summary

Обе кнопки «Отправить заказ» (локальная в корзине и плавающая Telegram-помощника) блокируются без сети с понятным пояснением; корзина в localStorage не теряется. Финальная приёмка на реальном устройстве (Task 3) отложена по решению владельца на конец вехи v1.3.

## Что сделано

### Task 1: Офлайн-блокировка локальной кнопки в корзине
**Коммит:** `f9b32fb`

**app/catalog/[secret]/cart/page.tsx**:
- Добавлен импорт `useOnlineStatus` из `@/lib/useOnlineStatus`
- В локальной функции `TelegramButton` — `const isOnline = useOnlineStatus()`
- Кнопке добавлен `disabled={!isOnline}` + disabled-классы `disabled:bg-gray-300 disabled:text-gray-500 disabled:cursor-not-allowed` (прежние классы сохранены)
- Под кнопкой при `!isOnline` — постоянная подпись D-05: «Нет сети — заказ отправится, когда появится интернет. Корзина сохранена.»
- `handleSend` и логика сборки текста заказа не тронуты; корзина (useCart/localStorage) не модифицирована

### Task 2: Офлайн-блокировка плавающей кнопки Telegram + проверка офлайн-корзины
**Коммит:** `c028e47`

**components/TelegramButton.tsx**:
- Добавлен импорт и вызов `useOnlineStatus()`
- `onClick={isOnline ? handleClick : undefined}` + `disabled={!isOnline}`
- В офлайне — `opacity-50 cursor-not-allowed` (без hover/pulse); в онлайне — `hover:scale-110 active:scale-95` и условный `animate-pulse`
- Условные `title` / `aria-label` для офлайн-состояния; кнопка офлайн не открывает Telegram
- Без красного оформления (D-03)

**CART-01 (проверка, не переписывание):** прочитан `lib/useCart.ts` — корзина целиком работает через `localStorage` (`loadCart()` / `saveCart()` с SSR-guard `typeof window === "undefined"`), без сетевых вызовов. Добавление/удаление/изменение количества работают офлайн. Изменений кода не требуется (D-06).

### Task 3: iPhone-приёмка офлайн-корзины и блокировки кнопок — ОТЛОЖЕНА
**Статус:** deferred (отложена по решению владельца)

Финальная ручная приёмка на реальном iPhone (критерий успеха ROADMAP №5) перенесена на самый конец вехи v1.3 — перед сдачей всей вехи. Чеклист сохранён в `12-HUMAN-UAT.md` и всплывёт в `/gsd:progress`. Это согласуется с практикой этапа 11 (iPhone-проверка тоже была отложена).

## Критерии успеха

| Критерий | Статус |
|----------|--------|
| Офлайн обе кнопки отправки заблокированы | ✅ `disabled={!isOnline}` на обеих |
| Локальная кнопка: постоянная подпись D-05 | ✅ текст точный |
| Корзина набирается офлайн и не теряется (CART-01) | ✅ подтверждено чтением useCart.ts |
| При возврате сети кнопки включаются автоматически | ✅ через события online/offline хука |
| npx tsc --noEmit без ошибок | ✅ |
| npm run build без ошибок | ✅ |
| iPhone-приёмка на реальном устройстве (№5) | ⏸ отложена на конец вехи v1.3 |

## Отклонения от плана

Task 3 (блокирующая пауза human-verify) не выполнена сейчас — отложена на конец вехи по явному решению владельца. Кодовая часть плана (Task 1, Task 2) выполнена точно как написана.

## Known Stubs

Нет. Офлайн-фото — отдельный этап 13 (вне scope этого плана).

## Threat Flags

Нет новых поверхностей. T-12-04 (navigator.onLine как единственный признак сети) принят: корзина сохраняется в localStorage, потери данных нет.

## Self-Check: PASSED (код), приёмка отложена

- `app/catalog/[secret]/cart/page.tsx` — импортирует и использует useOnlineStatus ✅
- `components/TelegramButton.tsx` — импортирует и использует useOnlineStatus ✅
- Подпись D-05 «Корзина сохранена» присутствует ✅
- Коммит `f9b32fb` — существует ✅
- Коммит `c028e47` — существует ✅
- iPhone-приёмка (Task 3) — ⏸ отложена на конец вехи v1.3
