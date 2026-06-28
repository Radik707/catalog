---
phase: 16-order-history
verified: 2026-06-27T18:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
re_verification: null
gaps: []
human_verification: []
resolution: |
  Все пункты human_verification закрыты:
  1. REQUIREMENTS.md обновлён — HIST-03 теперь [x] / Complete (строки 24, 70).
  2. Живая приёмка на проде (checkpoint:human-verify плана 16-02) подтверждена
     владельцем («принято»): заголовок «Отправленные заказы», запись в обе кнопки,
     корзина не очищается, очистка/удаление работают.
  Дополнительно: код-ревью нашло блокер CR-01 (гонка двух экземпляров useOrderHistory →
  потеря записи истории). Исправлено коммитом 78ba906 — введён единый OrderHistoryProvider
  (по образцу CartProvider), все потребители переведены на useOrderHistoryContext; сборка проходит.
---

# Phase 16: Локальная история заказов — Отчёт верификации

**Цель этапа:** Локальная история заказов — клиент видит список отправленных заказов (мини-фото, сумма, дата, канал), запись при отправке в Telegram/MAX, честная подпись «Отправленные заказы» без статусов, очистка всё/по одной, работа офлайн.
**Верифицировано:** 2026-06-27T18:00:00Z
**Статус:** HUMAN_NEEDED (документация REQUIREMENTS.md не синхронизирована с кодом)
**Ре-верификация:** Нет — первичная верификация

---

## Цель достигнута

### Observable Truths

| # | Истина | Статус | Доказательство |
|---|--------|--------|----------------|
| 1 | Хук useOrderHistory загружает историю из localStorage при монтировании и сохраняет при изменении (по образцу useCart) | ✓ VERIFIED | `lib/useOrderHistory.ts` строки 59–69: двойной useEffect (load-on-mount + save-on-change с isLoaded-guard), паттерн идентичен useCart |
| 2 | Добавление 21-й записи тихо вытесняет самую старую (FIFO, потолок 20) | ✓ VERIFIED | `useOrderHistory.ts` строки 72–80: `next.slice(next.length - MAX_HISTORY_ENTRIES)` при `next.length > 20` |
| 3 | Битая/неполная запись при чтении пропускается, валидные остаются (мягкая деградация) | ✓ VERIFIED | `useOrderHistory.ts` строки 14–23: `isValidEntry` + `Array.isArray(arr) ? arr.filter(isValidEntry) : []` + try/catch вокруг JSON.parse |
| 4 | Тип OrderHistoryEntry содержит items, total, createdAt, channel и уникальный id | ✓ VERIFIED | `lib/types.ts` строки 31–37: все 5 полей присутствуют; `channel: 'telegram' \| 'max'` |
| 5 | При нажатии «Отправить заказ в Telegram» в историю добавляется запись с channel: 'telegram' | ✓ VERIFIED | `cart/page.tsx` строки 255–268: `addEntry(entry)` с `channel: 'telegram'` ПОСЛЕ `window.open` |
| 6 | При нажатии «Отправить заказ в MAX» в историю добавляется запись с channel: 'max' | ✓ VERIFIED | `cart/page.tsx` строки 330–341: `addEntry(historyEntry)` с `channel: 'max'` перед try/catch — одна запись вне зависимости от успеха fetch |
| 7 | Корзина после отправки НЕ очищается (clearCart не вызывается при отправке) | ✓ VERIFIED | `cart/page.tsx` строки 256, 329: комментарии «clearCart НЕ вызывается»; `clearCart()` вызывается только в ручной кнопке «Очистить корзину» (строка 98, confirm-диалог) |
| 8 | Страница /orders показывает «Отправленные заказы», список записей с мини-фото, суммой, датой, каналом | ✓ VERIFIED | `orders/page.tsx` строка 69: заголовок «Отправленные заказы»; строки 116–171: рендер дата+канал+позиции с мини-фото и onError/SVG-заглушкой |
| 9 | Пользователь может очистить всю историю и удалить отдельную запись (с confirm) | ✓ VERIFIED | `orders/page.tsx` строки 74, 91: два confirm — `'Удалить всю историю заказов?'` и `'Удалить эту запись?'` |
| 10 | Из пустой и заполненной корзины есть видимая ссылка на /orders | ✓ VERIFIED | `cart/page.tsx` строка 63: ссылка в пустой корзине `Мои отправленные заказы →`; строка 90: бирюзовая таблетка «История заказов» в шапке заполненной корзины |
| 11 | Нигде на странице /orders нет слов «статус»/«принято»/«в доставке» | ✓ VERIFIED | Grep: слово «статус» встречается ТОЛЬКО в комментарии строки 5 (`// Не содержит слов...`), не в рендере. В JSX запрещённые слова отсутствуют |
| 12 | История работает офлайн (только localStorage, без сетевых вызовов в хуке) | ✓ VERIFIED | Grep: fetch/axios/API отсутствуют в `useOrderHistory.ts`; SSR-guard `typeof window === 'undefined'` на строке 29 |

**Счёт: 12/12 истин подтверждены**

---

### Артефакты

| Артефакт | Ожидалось | Уровень 1: Существует | Уровень 2: Содержателен | Уровень 3: Подключён | Итог |
|----------|-----------|----------------------|------------------------|---------------------|------|
| `lib/types.ts` | Типы OrderHistoryItem и OrderHistoryEntry | ✓ | ✓ 38 строк, оба интерфейса с полными полями | ✓ Импортируется в useOrderHistory.ts и orders/page.tsx | ✓ VERIFIED |
| `lib/useOrderHistory.ts` | Хук-store с CRUD + FIFO 20 + мягкая деградация | ✓ | ✓ 99 строк, все функции реализованы | ✓ Импортируется в cart/page.tsx и orders/page.tsx | ✓ VERIFIED |
| `app/catalog/[secret]/orders/page.tsx` | Страница «Отправленные заказы» | ✓ | ✓ 256 строк, список + очистка + мини-фото + пустое состояние | ✓ Использует useOrderHistory, removeEntry, clearHistory | ✓ VERIFIED |
| `app/catalog/[secret]/cart/page.tsx` | Запись заказа в историю + ссылки на /orders | ✓ | ✓ 389 строк, useOrderHistory импортирован | ✓ addEntry вызван в обеих кнопках (строки 267, 340) | ✓ VERIFIED |

---

### Ключевые связи (Key Links)

| От | К | Через | Статус | Детали |
|----|---|-------|--------|--------|
| `lib/useOrderHistory.ts` | `localStorage['catalog-order-history']` | loadHistory/saveHistory с try/catch | ✓ WIRED | `HISTORY_KEY = 'catalog-order-history'` строка 7; setItem/getItem строки 31, 45 |
| `lib/useOrderHistory.ts` | `lib/types.ts` | импорт OrderHistoryEntry | ✓ WIRED | строка 4: `import { OrderHistoryEntry } from './types'` |
| `app/catalog/[secret]/cart/page.tsx` | `useOrderHistory.addEntry` | вызов в handleSend обеих кнопок | ✓ WIRED | строки 267 (Telegram) и 340 (MAX) |
| `app/catalog/[secret]/orders/page.tsx` | `useOrderHistory` | чтение entries + removeEntry + clearHistory | ✓ WIRED | строки 7 и 11 |
| `app/catalog/[secret]/cart/page.tsx` | `/catalog/[secret]/orders` | ссылки в пустой корзине и шапке | ✓ WIRED | строки 63 и 90 — два вхождения `/orders` |

---

### Трассировка данных (Level 4)

| Артефакт | Переменная данных | Источник | Реальные данные | Статус |
|----------|------------------|---------|-----------------|--------|
| `orders/page.tsx` | `entries` | `useOrderHistory()` → localStorage | addEntry вызывается в cart/page.tsx при реальном нажатии кнопки отправки; данные из корзины через effectivePrice | ✓ FLOWING |
| `cart/page.tsx` (snapshot) | `items` + `priceForm` | `useCartContext()` + `useCatalogSettings()` | Реальные товары корзины, effectivePrice — не захардкожены | ✓ FLOWING |

---

### Поведенческие проверки (Spot-Checks)

| Поведение | Команда | Результат | Статус |
|-----------|---------|-----------|--------|
| useOrderHistory экспортирует функцию | `grep -c "export function useOrderHistory" lib/useOrderHistory.ts` | 1 | ✓ PASS |
| FIFO-потолок 20 | `grep -c "MAX_HISTORY_ENTRIES = 20" lib/useOrderHistory.ts` | 1 | ✓ PASS |
| Ключ localStorage | `grep -c "catalog-order-history" lib/useOrderHistory.ts` | 2 | ✓ PASS |
| SSR-guard | `grep -c "typeof window === 'undefined'" lib/useOrderHistory.ts` | 2 | ✓ PASS |
| Array.isArray мягкая деградация | присутствует в loadHistory | строка 34 | ✓ PASS |
| addEntry в Telegram-кнопке | строка 267 cart/page.tsx | `addEntry(entry)` | ✓ PASS |
| addEntry в MAX-кнопке | строка 340 cart/page.tsx | `addEntry(historyEntry)` | ✓ PASS |
| channel: 'telegram' | строка 265 cart/page.tsx | `channel: 'telegram'` | ✓ PASS |
| channel: 'max' | строка 338 cart/page.tsx | `channel: 'max'` | ✓ PASS |
| effectivePrice в снимке | строка 213 cart/page.tsx | `priceAtOrder: effectivePrice(product, priceForm)` | ✓ PASS |
| Заголовок «Отправленные заказы» | строка 69 orders/page.tsx | точный текст | ✓ PASS |
| Запрещённые слова в JSX | grep по «статус\|принято\|в доставке» в orders/page.tsx | только в комментарии строки 5, не в JSX | ✓ PASS |
| ссылок на /orders не менее 2 | grep "/orders" в cart/page.tsx | строки 63 и 90 | ✓ PASS |
| clearCart не в handleSend | context строки 256 и 329 | только комментарии «НЕ вызывается» | ✓ PASS |
| confirm на очистку | grep "confirm" в orders/page.tsx | 2 вхождения (строки 74 и 91) | ✓ PASS |

---

### Проверка коммитов

| Коммит | Задача | Статус |
|--------|--------|--------|
| `fd17e83` | Типы OrderHistoryItem и OrderHistoryEntry | ✓ EXIST в git log |
| `c657165` | Создать хук useOrderHistory | ✓ EXIST в git log |
| `502b9e7` | Страница «Отправленные заказы» | ✓ EXIST в git log |
| `20c4df4` | Встройка записи в обе кнопки + ссылки | ✓ EXIST в git log |
| `f6af7a3` | Бирюзовая таблетка «История заказов» | ✓ EXIST в git log |

---

### Покрытие требований

| Требование | Планы | Описание | Статус в коде | Статус в REQUIREMENTS.md | Примечание |
|------------|-------|----------|---------------|--------------------------|------------|
| HIST-01 | 16-01, 16-02 | Заказ сохраняется в локальную историю после отправки | ✓ SATISFIED | [x] Complete | addEntry в обеих кнопках |
| HIST-02 | 16-01 | История переживает закрытие вкладки, работает офлайн | ✓ SATISFIED | [x] Complete | только localStorage, без fetch |
| HIST-03 | 16-02 | Подпись «Отправленные заказы», без статусов | ✓ SATISFIED в коде | [ ] **Pending** | РАСХОЖДЕНИЕ: код реализует, документ не обновлён |
| HIST-04 | 16-01, 16-02 | Очистка + мягкая деградация битых записей | ✓ SATISFIED | [x] Complete | isValidEntry + confirm-диалоги |

---

### Антипаттерны

| Файл | Паттерн | Вердикт |
|------|---------|---------|
| Все 4 файла | TBD / FIXME / XXX | Не найдены |
| `orders/page.tsx` | return null / заглушки | Не найдены — рендер содержателен |
| `useOrderHistory.ts` | Сетевые вызовы (fetch/axios) | Не найдены — только localStorage |
| `cart/page.tsx` | clearCart в handleSend | Не найден — clearCart только в ручной кнопке «Очистить корзину» |

---

### Нужна проверка человеком

#### 1. Обновить REQUIREMENTS.md: статус HIST-03

**Тест:** Открыть `.planning/REQUIREMENTS.md`, исправить строку 24 с `[ ]` на `[x]`, строку 70 с `Pending` на `Complete`
**Ожидаемо:** HIST-03 помечен выполненным, таблица прослеживаемости актуальна
**Почему человек:** Это правка документа, а не кода; верификатор не вносит изменения

#### 2. Финальная визуальная проверка страницы /orders на проде

**Тест:** Открыть `https://catalog-khaki.vercel.app/catalog/<secret>/orders` (после уже выполненного деплоя, checkpoint:human-verify пройден с ответом «принято»)
**Ожидаемо:** Заголовок «Отправленные заказы», мини-фото позиций, кнопки «Удалить» и «Очистить» с confirm, ссылка «← Корзина»
**Почему человек:** Визуальный рендер; checkpoint уже был пройден, этот пункт формальный

---

### Итог по пробелам

Технических пробелов нет. Единственная нерешённая позиция — документальное расхождение: REQUIREMENTS.md содержит `[ ]` и `Pending` для HIST-03, тогда как код полностью реализует это требование. Цель этапа достигнута в коде. Статус `human_needed` — для закрытия расхождения в документации.

---

*Верифицировано: 2026-06-27T18:00:00Z*
*Верификатор: Claude (gsd-verifier)*
