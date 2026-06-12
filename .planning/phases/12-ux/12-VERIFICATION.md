---
phase: 12-ux
verified: 2026-06-12T12:00:00Z
status: human_needed
score: 9/10 must-haves verified
overrides_applied: 0
human_verification:
  - test: "iPhone-приёмка офлайн-корзины и блокировки кнопок (Task 3 плана 12-02)"
    expected: |
      1. Под синей шапкой появляется серая полоска «Офлайн • данные за ЧЧ:ММ»
      2. Товары добавляются/удаляются из корзины без сети
      3. Кнопка «Отправить заказ» серая/неактивная, под ней подпись «Нет сети — заказ отправится, когда появится интернет. Корзина сохранена.»
      4. Плавающая кнопка Telegram приглушена, не открывает Telegram
      5. После закрытия/открытия вкладки корзина сохранилась
      6. При отключении авиарежима кнопка автоматически становится активной (синей) без перезагрузки
    why_human: "Критерий успеха ROADMAP №5 явно требует проверки на реальном iPhone (Safari, PWA). Эмулятор не достаточен согласно плану. Отложено по решению владельца на конец вехи v1.3 (аналогично этапу 11)."
---

# Этап 12: Офлайн-UX (индикаторы и корзина) — Отчёт верификации

**Цель этапа:** Агент всегда понимает, онлайн он или офлайн и насколько свежи данные; корзина работает без сети, но попытка отправить заказ офлайн не теряет данные молча.
**Проверено:** 2026-06-12
**Статус:** human_needed
**Повторная верификация:** Нет — первичная проверка

---

## Цель достигнута?

### Наблюдаемые истины

| # | Истина | Статус | Доказательство |
|---|--------|--------|----------------|
| 1 | Онлайн + данные свежее 24 ч → полоска скрыта (чистая шапка) | ✓ VERIFIED | `OfflineBar.tsx:63` — `if (isOnline && !isStale) return null` |
| 2 | Офлайн → серая нейтральная полоска «Офлайн • данные за 08:30» | ✓ VERIFIED | `OfflineBar.tsx:72-74` — `bg-gray-100 text-gray-600`; `OfflineBar.tsx:78-79` — `Офлайн • ${formatSyncTime(syncedAt)}` |
| 3 | Данные старше 24 ч → жёлтая полоска-предупреждение | ✓ VERIFIED | `OfflineBar.tsx:58-59` — `isStale = syncedAt !== null && Date.now() - syncedAt > STALE_THRESHOLD_MS`; `OfflineBar.tsx:70-74` — `bg-yellow-50 text-yellow-800` |
| 4 | Полоска показывает время последней синхронизации в человекочитаемом формате | ✓ VERIFIED | `formatSyncTime.ts:65-89` — три ветки: null/сегодня/вчера/раньше; `OfflineBar.tsx:44` — `getMeta<number>("syncTimestamp")` |
| 5 | Офлайн обе кнопки отправки заказа заблокированы (disabled) | ✓ VERIFIED | `cart/page.tsx:169` — `disabled={!isOnline}`; `TelegramButton.tsx:52` — `disabled={!isOnline}` |
| 6 | Под локальной кнопкой офлайн видна подпись «Нет сети — заказ отправится, когда появится интернет. Корзина сохранена.» | ✓ VERIFIED | `cart/page.tsx:175-179` — точный текст D-05 рендерится при `!isOnline` |
| 7 | При появлении сети кнопки включаются автоматически (без перезагрузки) | ✓ VERIFIED | `useOnlineStatus.ts:28-32` — слушатели `window.addEventListener("online"/"offline")` обновляют `isOnline` реактивно |
| 8 | Корзина добавляется/удаляется офлайн — данные не теряются (CART-01) | ✓ VERIFIED | `useCart.ts:15-33` — `loadCart()`/`saveCart()` используют только `localStorage` с SSR-guard `typeof window === "undefined"`; ни одного сетевого вызова |
| 9 | Заказ в корзине сохраняется при попытке отправки офлайн — данные не теряются молча (CART-02) | ✓ VERIFIED | `cart/page.tsx:147-161` — `handleSend` не вызывается при `disabled={!isOnline}`; корзина `useCartContext` не очищается при блокировке |
| 10 | iPhone-приёмка: авиарежим → добавить товар → корзина сохранилась → кнопка заблокирована | ? HUMAN_NEEDED | Требует реального устройства (iPhone/Safari/PWA). Отложена владельцем на конец вехи v1.3 |

**Счёт: 9/10 истин подтверждены автоматически**

---

## Артефакты

| Артефакт | Ожидалось | Статус | Детали |
|----------|-----------|--------|--------|
| `lib/useOnlineStatus.ts` | Хук статуса сети, SSR-safe, min 20 строк | ✓ VERIFIED | 42 строки; `"use client"`; `useState(true)`; `typeof navigator !== "undefined"` guard; cleanup online/offline; независим от useCatalogSync и IDB |
| `lib/formatSyncTime.ts` | Утилита форматирования метки, без "use client", min 20 строк | ✓ VERIFIED | 89 строк; нет `"use client"`; нет внешних библиотек; три формата; `MONTHS_GENITIVE` массив; `formatTime` с `padStart` |
| `components/OfflineBar.tsx` | Клиентская полоска, три состояния, min 30 строк | ✓ VERIFIED | 91 строка; `"use client"`; три состояния D-01; `setInterval(60_000)` — тик WR-01; повторное чтение IDB в интервале — WR-02; `try/catch` вокруг `getMeta` |
| `app/catalog/[secret]/layout.tsx` | Вставка `<OfflineBar />` под `</header>` | ✓ VERIFIED | Строка 9: `import OfflineBar`; строка 41: `<OfflineBar />`; нет `"use client"` в начале файла — layout серверный |
| `app/catalog/[secret]/cart/page.tsx` | Локальная кнопка с офлайн-блокировкой + подпись | ✓ VERIFIED | Строка 4: `import { useOnlineStatus }`; строка 144: `const isOnline = useOnlineStatus()`; строка 169: `disabled={!isOnline}`; строки 175-179: подпись D-05 |
| `components/TelegramButton.tsx` | Плавающая кнопка с офлайн-блокировкой | ✓ VERIFIED | Строка 4: `import { useOnlineStatus }`; строка 12: `const isOnline = useOnlineStatus()`; строка 51: `onClick={isOnline ? handleClick : undefined}`; строка 52: `disabled={!isOnline}`; `opacity-50 cursor-not-allowed` в офлайне |

---

## Ключевые связи (wiring)

| От | К | Через | Статус | Детали |
|----|----|-------|--------|--------|
| `components/OfflineBar.tsx` | `lib/useOnlineStatus.ts` | `import useOnlineStatus` | ✓ WIRED | строка 13 OfflineBar.tsx |
| `components/OfflineBar.tsx` | `lib/catalogDb.ts` | `getMeta('syncTimestamp')` | ✓ WIRED | строка 14 (import), строки 44/50 (вызов в load()) |
| `components/OfflineBar.tsx` | `lib/formatSyncTime.ts` | `import formatSyncTime` | ✓ WIRED | строка 15 (import), строки 79/80 (вызов в label) |
| `app/catalog/[secret]/layout.tsx` | `components/OfflineBar.tsx` | `<OfflineBar />` в JSX | ✓ WIRED | строка 9 (import), строка 41 (JSX) |
| `app/catalog/[secret]/cart/page.tsx` | `lib/useOnlineStatus.ts` | `import useOnlineStatus` | ✓ WIRED | строка 4 (import), строка 144 (вызов) |
| `components/TelegramButton.tsx` | `lib/useOnlineStatus.ts` | `import useOnlineStatus` | ✓ WIRED | строка 4 (import), строка 12 (вызов) |

---

## Трассировка данных (Level 4)

| Артефакт | Переменная данных | Источник | Реальные данные | Статус |
|----------|------------------|----------|-----------------|--------|
| `OfflineBar.tsx` | `syncedAt` | `getMeta<number>("syncTimestamp")` из `lib/catalogDb.ts` (IndexedDB) | Да — читает реальный `syncTimestamp`, записанный `useCatalogSync` | ✓ FLOWING |
| `OfflineBar.tsx` | `isOnline` | `useOnlineStatus()` → `navigator.onLine` + события | Да — браузерный API, обновляется в реальном времени | ✓ FLOWING |
| `cart/page.tsx` (TelegramButton) | `isOnline` | `useOnlineStatus()` → `navigator.onLine` + события | Да | ✓ FLOWING |
| `TelegramButton.tsx` | `isOnline` | `useOnlineStatus()` → `navigator.onLine` + события | Да | ✓ FLOWING |

---

## Исправления ревью (WR-01/WR-02/WR-03)

| Находка | Коммит | Подтверждение в коде |
|---------|--------|----------------------|
| WR-01: OfflineBar не пересчитывал `isStale` со временем | `7179722` | `OfflineBar.tsx:27,49-53` — `const [, setTick] = useState(0)`; `setInterval(() => { void load(); setTick((t) => t + 1) }, 60_000)` |
| WR-02: Метка `syncedAt` не обновлялась после фоновой синхронизации | `7179722` | `OfflineBar.tsx:46-54` — `load()` вызывается и при монтировании, и в интервале 60 сек |
| WR-03: Двойное открытие Telegram (tg:// + window.open) | `c034000` | `TelegramButton.tsx:36-44` — `cancelFallback`: слушает `visibilitychange`, очищает таймер если `document.hidden === true` |

Все три WR-исправления верифицированы в коде. WR-04 и Info-замечания (IN-01..IN-05) перенесены в BACKLOG по решению владельца — не блокируют этап.

---

## Поведенческие spot-checks

| Поведение | Файл | Строка | Результат |
|-----------|------|--------|-----------|
| `OfflineBar` скрыта при `isOnline && !isStale` | `OfflineBar.tsx` | 63 | ✓ `return null` |
| `OfflineBar` серая при `!isOnline && !isStale` | `OfflineBar.tsx` | 72-74 | ✓ `bg-gray-100 text-gray-600` |
| `OfflineBar` жёлтая при `isStale` | `OfflineBar.tsx` | 70-74 | ✓ `bg-yellow-50 text-yellow-800` |
| Красный цвет отсутствует (D-03) | `OfflineBar.tsx` | 1-91 | ✓ нет `bg-red-` / `text-red-` |
| `sticky`, не `fixed` | `OfflineBar.tsx` | 84 | ✓ `sticky top-12 z-40` |
| `max-w-screen-2xl mx-auto` | `OfflineBar.tsx` | 86 | ✓ |
| `formatSyncTime(null)` → «данные не загружены» | `formatSyncTime.ts` | 67-69 | ✓ |
| ведущие нули в `formatTime` | `formatSyncTime.ts` | 29-31 | ✓ `.padStart(2, "0")` |
| `MONTHS_GENITIVE` массив, родительный падеж | `formatSyncTime.ts` | 10-23 | ✓ |
| `useOnlineStatus` SSR-safe | `useOnlineStatus.ts` | 18,23-24 | ✓ `useState(true)` + `typeof navigator !== "undefined"` |
| Cleanup online/offline слушателей | `useOnlineStatus.ts` | 35-38 | ✓ |
| Локальная кнопка: `disabled={!isOnline}` | `cart/page.tsx` | 169 | ✓ |
| Подпись D-05 точный текст | `cart/page.tsx` | 175-179 | ✓ |
| Плавающая кнопка: `onClick=undefined` в офлайне | `TelegramButton.tsx` | 51 | ✓ `onClick={isOnline ? handleClick : undefined}` |
| `opacity-50 cursor-not-allowed` в офлайне (FAB) | `TelegramButton.tsx` | 56 | ✓ |
| Условные `title` и `aria-label` | `TelegramButton.tsx` | 58-59 | ✓ |
| Корзина — только localStorage, без сети | `useCart.ts` | 15-33 | ✓ `localStorage.getItem/setItem` с SSR-guard |

---

## Покрытие требований

| Требование | Источник плана | Описание | Статус | Доказательство |
|------------|---------------|----------|--------|----------------|
| SYNC-03 | 12-01-PLAN.md | Видно состояние сети (онлайн/офлайн) и метка «данные за ЧЧ:ММ» | ✓ ВЫПОЛНЕНО | `OfflineBar.tsx` с тремя состояниями, `formatSyncTime`, вставлен в layout |
| CART-01 | 12-02-PLAN.md | Набор корзины работает без сети — товары добавляются и удаляются офлайн | ✓ ВЫПОЛНЕНО | `useCart.ts` использует только localStorage; подтверждено чтением кода + решение D-06 |
| CART-02 | 12-02-PLAN.md | Отправка заказа требует сети — офлайн кнопка заблокирована с пояснением; заказ не теряется | ✓ ВЫПОЛНЕНО | `disabled={!isOnline}` на обеих кнопках; подпись D-05; корзина не очищается |

Все три требования этапа 12 закрыты в коде. Статус «Pending» для CART-01/CART-02 в REQUIREMENTS.md трассировочной таблице не обновлён — но это документационный артефакт, не дефект кода.

---

## Антипаттерны

Сканирование файлов этапа (`lib/useOnlineStatus.ts`, `lib/formatSyncTime.ts`, `components/OfflineBar.tsx`, `app/catalog/[secret]/layout.tsx`, `app/catalog/[secret]/cart/page.tsx`, `components/TelegramButton.tsx`):

| Файл | Строка | Паттерн | Серьёзность | Влияние |
|------|--------|---------|-------------|---------|
| Нет | — | — | — | — |

Маркеры TBD/FIXME/XXX: не найдены. Заглушки `return null` / `return []` / `return {}`: не найдены в путях рендера. Все `return null` — намеренные (полоска скрыта при онлайне, TelegramButton скрыт при `!BOT_USERNAME`).

---

## Ручная верификация

### 1. iPhone-приёмка офлайн-режима

**Тест:** На реальном iPhone (Safari, каталог по секретной ссылке, желательно как PWA):
1. Убедись, что каталог загрузился при наличии сети (данные в IndexedDB).
2. Включи Авиарежим.
3. Открой каталог — под шапкой должна появиться серая полоска «Офлайн • данные за ЧЧ:ММ».
4. Добавь 2-3 товара в корзину, измени количество, удали один — должно работать без сети.
5. Открой корзину — товары на месте; кнопка «Отправить заказ в Telegram» серая/неактивная; под ней подпись «Нет сети — заказ отправится, когда появится интернет. Корзина сохранена.»
6. Плавающая кнопка Telegram (если NEXT_PUBLIC_BOT_USERNAME задан) — приглушена и не открывает Telegram.
7. Закрой и снова открой вкладку в авиарежиме — корзина сохранилась.
8. Выключи авиарежим — кнопка «Отправить заказ» через секунду снова активная (синяя) без перезагрузки.

**Ожидается:** всё перечисленное работает без сбоев.

**Почему нужен человек:** Критерий успеха ROADMAP №5 явно требует проверки на реальном iPhone — эмулятор недостаточен. Отложено по решению владельца аналогично этапу 11 (iPhone-тест вынесен в конец вехи v1.3).

---

## Итог по пробелам

Автоматически верифицированных пробелов нет. Единственный открытый пункт — ручная iPhone-приёмка (критерий ROADMAP №5), отложенная по решению владельца.

---

_Проверено: 2026-06-12_
_Верификатор: Claude (gsd-verifier)_
