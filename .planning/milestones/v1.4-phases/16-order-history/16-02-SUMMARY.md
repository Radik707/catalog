---
phase: 16-order-history
plan: 02
subsystem: ui
tags: [typescript, localStorage, react-hooks, order-history, cart]

# Dependency graph
requires:
  - phase: 16-01
    provides: "useOrderHistory хук с CRUD + FIFO-потолком 20; типы OrderHistoryItem/OrderHistoryEntry"
provides:
  - "Страница /orders «Отправленные заказы» с мини-фото, датой, каналом, очисткой всё/по одной"
  - "Запись заказа в историю при нажатии кнопки Telegram и MAX в корзине (D-01, D-02)"
  - "Бирюзовая таблетка «История заказов» в шапке корзины + ссылка из пустой корзины (D-05)"
  - "Цены в истории через effectivePrice — совпадают с текстом заказа (D-08)"
  - "Корзина после отправки НЕ очищается (D-03)"
affects:
  - "16-SUMMARY (этап завершён полностью)"
  - "17 (сортировка + стикеры — строится поверх тех же страниц каталога)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "addEntry вызывается ПОСЛЕ window.open — снимок строится из items + effectivePrice в момент отправки"
    - "Бирюзовая таблетка-ссылка в шапке корзины: паттерн pill-badge для быстрого перехода к истории"
    - "pluralOrders(n) — локальная утилита склонения слова «заказ» по образцу pluralItems"
    - "Мягкая деградация рендера: проверка name/priceAtOrder перед рендером каждой позиции"

key-files:
  created:
    - app/catalog/[secret]/orders/page.tsx
  modified:
    - app/catalog/[secret]/cart/page.tsx

key-decisions:
  - "D-01: запись в момент нажатия кнопки отправки (ПОСЛЕ window.open), не при открытии мессенджера"
  - "D-02: канал определяется нажатой кнопкой — 'telegram' или 'max'"
  - "D-03: корзина после отправки НЕ очищается — пользователь сам управляет"
  - "D-05: ссылка на /orders видна и в пустой корзине (блок empty-state), и в шапке заполненной (бирюзовая таблетка)"
  - "D-08: priceAtOrder = effectivePrice(product, priceForm) — цифры истории совпадают с текстом заказа"
  - "Бирюзовая таблетка «История заказов» добавлена на приёмке (правка по итогам checkpoint) вместо текстовой ссылки — лучше заметна"

patterns-established:
  - "История заказов: снимок строить в момент нажатия кнопки, не хранить ссылки на объекты корзины"
  - "effectivePrice как единственный источник цены в снимке — исключает расхождение с текстом заказа"
  - "Страница /orders: заголовок строго «Отправленные заказы», без слов статуса (HIST-03 инвариант)"

requirements-completed: [HIST-01, HIST-03, HIST-04]

# Metrics
duration: ~30min
completed: 2026-06-27
---

# Phase 16 Plan 02: История заказов подключена Summary

**Страница /orders «Отправленные заказы» + запись в localStorage при отправке обоими каналами (Telegram/MAX) с ценами через effectivePrice, корзина не очищается, бирюзовая таблетка в шапке корзины**

## Performance

- **Duration:** ~30 мин (включая деплой и живую приёмку на проде)
- **Started:** 2026-06-27
- **Completed:** 2026-06-27
- **Tasks:** 3 (2 авто + 1 checkpoint:human-verify)
- **Files modified:** 2

## Accomplishments
- Создана страница `app/catalog/[secret]/orders/page.tsx` — список заказов с мини-фото, датой, каналом (Telegram/MAX), числом позиций, итогом; очистка всё/по одной через confirm (HIST-04, D-12)
- Встроена запись заказа в обе кнопки отправки `cart/page.tsx` — снимок items с ценами effectivePrice, channel: 'telegram' / 'max', корзина не очищается (D-01, D-02, D-03)
- Добавлены ссылки на /orders: из пустой корзины (обязательный D-05) и бирюзовая таблетка «История заказов» в шапке заполненной корзины (правка на checkpoint)
- Checkpoint:human-verify пройден — приёмка на проде (Vercel) пользователем, итог: «принято»

## Task Commits

Каждое задание закоммичено атомарно:

1. **Task 1: Страница «Отправленные заказы» (/orders)** — `502b9e7` (feat)
2. **Task 2: Встройка записи в обе кнопки отправки + ссылки на /orders** — `20c4df4` (feat)
3. **Post-checkpoint tweak: бирюзовая таблетка «История заказов» в шапке корзины** — `f6af7a3` (feat)

**Метаданные плана:** (см. финальный коммит docs)

## Files Created/Modified
- `app/catalog/[secret]/orders/page.tsx` — страница «Отправленные заказы»: рендер списка из useOrderHistory, мини-фото с onError/SVG-заглушкой, дата-время, канал, склонение через pluralOrders/pluralItems, confirm на очистку всего/удаление одной записи, ссылка «← Корзина»; мягкая деградация позиций без name/priceAtOrder
- `app/catalog/[secret]/cart/page.tsx` — добавлен импорт useOrderHistory; в TelegramButton.handleSend и MaxOrderButton.handleSend вызов addEntry после window.open с channel 'telegram'/'max' и снимком через effectivePrice; ссылки на /orders из пустой корзины и бирюзовая таблетка в шапке

## Decisions Made
- Бирюзовая таблетка «История заказов» — паттерн pill-badge, визуально контрастнее текстовой ссылки, лучше заметна рядом с синей шапкой корзины (решение на приёмке checkpoint)
- Снимок заказа строится в момент нажатия кнопки, не хранятся ссылки на объекты корзины — истекшие цены не меняются ретроспективно
- priceAtOrder = effectivePrice(product, priceForm) во всех позициях — ноль расхождения между историей и текстом заказа в мессенджере (D-08)
- Страница /orders без слов «статус/принято/в доставке» — подпись честная «Отправленные заказы» (HIST-03, D-06)

## Deviations from Plan

### Auto-fixed Issues

**1. [Правка на приёмке] Добавлена бирюзовая таблетка «История заказов» в шапку корзины**
- **Found during:** Checkpoint:human-verify (приёмка на проде)
- **Issue:** Исходная ссылка на /orders в шапке была недостаточно заметна
- **Fix:** Заменена на бирюзовую таблетку-badge с текстом «История заказов» — лучше выделяется в шапке
- **Files modified:** `app/catalog/[secret]/cart/page.tsx`
- **Committed in:** `f6af7a3`

---

**Total deviations:** 1 (UX-правка на приёмке по запросу checkpoint)
**Impact on plan:** Позитивный — улучшена заметность ссылки на историю. Поведение не изменено.

## Issues Encountered

Нет — все задания выполнены, TypeScript прошёл, приёмка на проде пройдена с первого раза.

## Threat Surface Scan

Нет новых угроз: страница /orders и правки cart/page.tsx — чисто клиентский код без сетевых вызовов, без новых API-эндпоинтов.

Угрозы из threat_model плана закрыты:
- T-16-04: мягкая деградация рендера на /orders — позиции без name/priceAtOrder показывают заглушку
- T-16-05: снимок содержит только данные из корзины (название/цена/кол-во), новой PII нет
- T-16-06: подпись «Отправленные заказы» исключает ложное толкование как «принято/доставлено»

## Known Stubs

Нет — все данные берутся из реального useOrderHistory хука (localStorage), данные не захардкожены.

## User Setup Required

Нет — никаких внешних сервисов и переменных окружения.

## Next Phase Readiness

- **Этап 16 полностью завершён:** HIST-01, HIST-02 (через хук 16-01), HIST-03, HIST-04 — все требования выполнены
- **Этап 17 (сортировка + стикеры акций)** можно начинать независимо — история заказов не блокирует его
- История заказов работает офлайн (localStorage + хук 16-01 с isLoaded-паттерном)
- Формат данных OrderHistoryEntry совместим с будущим переездом на Supabase (v2.0) — поля id/items/total/createdAt/channel покрывают серверную схему

## Self-Check: PASSED

- [x] `app/catalog/[secret]/orders/page.tsx` создан (коммит 502b9e7)
- [x] `app/catalog/[secret]/cart/page.tsx` изменён — встройка addEntry в обе кнопки (коммит 20c4df4)
- [x] Бирюзовая таблетка «История заказов» добавлена в шапку корзины (коммит f6af7a3)
- [x] Checkpoint:human-verify пройден на проде — ответ пользователя «принято»
- [x] HIST-01 выполнен: запись появляется после отправки (Telegram/MAX)
- [x] HIST-03 выполнен: подпись «Отправленные заказы», слов о статусе нет
- [x] HIST-04 выполнен: очистка всё/по одной + мягкая деградация

---
*Phase: 16-order-history*
*Completed: 2026-06-27*
