---
phase: 13-photo-sync
verified: 2026-06-13T13:43:29Z
status: human_needed
score: 9/9 авто-проверяемых критериев подтверждены
overrides_applied: 0
human_verification:
  - test: "iPhone-приёмка офлайн-фото (IMG-01, IMG-02, IMG-03)"
    expected: "Просмотреть 5–10 товаров онлайн → авиарежим → те же карточки показывают фото без сети; незнакомый товар — иконка-заглушка; ↻ обновляет каталог и докачивает только новые фото"
    why_human: "Проверяется только на реальном iPhone в Safari; нельзя проверить grep-ом или сборкой"
deferred:
  - truth: "Фото товара, открытого ранее при наличии сети, отображается в авиарежиме — в т.ч. в Lightbox с зумом (критерий 1 ROADMAP)"
    addressed_in: "конец вехи v1.3 (перед финальной сдачей, после этапа 14)"
    evidence: "Решение зафиксировано в 13-02-SUMMARY.md: 'iPhone-приёмка (Task 3) отложена на конец вехи v1.3 — по образцу этапов 11 и 12'"
  - truth: "Нажатие ↻ не перекачивает старые фото (критерий 2 ROADMAP)"
    addressed_in: "конец вехи v1.3"
    evidence: "Поведенческая проверка diff-алгоритма невозможна без реального устройства; код реализован и верифицирован статически"
  - truth: "На iPhone кэш фото не вызывает QuotaExceededError (критерий 4 ROADMAP)"
    addressed_in: "конец вехи v1.3"
    evidence: "Требует DevTools Safari Web Inspector на реальном iPhone"
  - truth: "Проверка на реальном iPhone: 5–10 товаров → авиарежим → фото видны (критерий 5 ROADMAP)"
    addressed_in: "конец вехи v1.3"
    evidence: "Отложено явным решением в 13-02-SUMMARY.md по образцу этапов 11–12"
---

# Этап 13: Синхронизация фото — Отчёт верификации

**Цель этапа:** Фото просмотренных товаров доступны офлайн (IMG-01/IMG-02/IMG-03); умная докачка только новых фото (SYNC-02); видимая кнопка «Обновить» (↻) в шапке (SYNC-01).

**Проверено:** 2026-06-13T13:43:29Z
**Статус:** human_needed (все авто-проверяемые критерии PASSED; iPhone-UAT отложена по решению владельца до конца вехи v1.3)
**Повторная верификация:** Нет — первичная.

---

## Выполненные шаги

- Step 0: Предыдущий VERIFICATION.md отсутствует — начальная верификация.
- Step 1–2: Цель и критерии успеха загружены из ROADMAP.md (5 критериев) и PLAN-frontmatter (11 must-have truths из двух планов).
- Step 3–5: Проверка каждой истины по 4 уровням (существует / содержательный / подключён / данные текут).
- Step 6: Покрытие требований IMG-01, IMG-02, IMG-03, SYNC-01, SYNC-02.
- Step 7: Сканирование anti-паттернов в 6 изменённых файлах.
- Step 7b: Поведенческие spot-check — `npx tsc --noEmit` + `npm run build`.
- Step 8: Идентификация Human-UAT пунктов.
- Step 9b: Фильтрация отложенных пунктов.

---

## Наблюдаемые истины (Must-Haves)

### Из плана 13-01

| # | Истина | Статус | Доказательство |
|---|--------|--------|----------------|
| 1 | Фото запрашивается по прямому URL res.cloudinary.com (не через /_next/image) | ✓ VERIFIED | ProductCard.tsx стр. 149, 300: атрибут `unoptimized` на обоих `<Image>` |
| 2 | SW кэширует только успешные (200) ответы Cloudinary | ✓ VERIFIED | sw.ts стр. 9, 70: `CacheableResponsePlugin({ statuses: [200] })` импортирован и применён в plugins CacheFirst |
| 3 | D-04: При нажатии Обновить докачиваются только новые фото (diff против prevImageUrls) | ✓ VERIFIED (код) | syncPhotos.ts стр. 32–35: `new Set(prevUrls)` + `filter(!prevSet.has(url))` + `fetch(url).catch` |
| 4 | D-04: Первая синхронизация (prevImageUrls пуст) НЕ качает все ~900 фото | ✓ VERIFIED | syncPhotos.ts стр. 30: `if (prevUrls.length > 0)` оборачивает весь блок fetch |
| 5 | D-06: Незакэшированное фото офлайн → иконка-заглушка, не битое изображение | ✓ VERIFIED (код) | ProductCard.tsx стр. 83: `useState(false)` imgError; стр. 150, 301: `onError={() => setImgError(true)}`; при imgError рендерится `<PhotoPlaceholder />` |
| 6 | Хук useCatalogSync экспонирует refetch() в контракте UseCatalogSyncResult | ✓ VERIFIED | useCatalogSync.ts стр. 46: `refetch: () => Promise<void>;`; стр. 229: `return { ..., refetch: sync }` |

### Из плана 13-02

| # | Истина | Статус | Доказательство |
|---|--------|--------|----------------|
| 7 | Кнопка ↻ видна в синей шапке рядом с шестерёнкой/корзиной всегда | ✓ VERIFIED | layout.tsx стр. 45: `<SyncButton />` в `<div className="flex items-center gap-1 shrink-0">` перед `<SettingsButton />` |
| 8 | Нажатие ↻ онлайн запускает refetch (fetch /api/products + prefetch новых фото) | ✓ VERIFIED | SyncButton.tsx стр. 15: `{ refetch, isOnline } = useCatalogSyncContext()`; стр. 30: `await refetch()` |
| 9 | Во время обновления иконка крутится; по завершении галочка | ✓ VERIFIED | SyncButton.tsx стр. 77: `animate-spin` при busy; стр. 58–73: done → SVG-галочка |
| 10 | Офлайн кнопка ↻ заблокирована (disabled) с понятным title | ✓ VERIFIED | SyncButton.tsx стр. 53: `disabled={!isOnline \|\| busy}`; стр. 55: `title={!isOnline ? "Нужен интернет для обновления" : ...}` |
| 11 | Кнопка и CatalogView делят один экземпляр useCatalogSync | ✓ VERIFIED | CatalogSyncProvider.tsx стр. 42: `const sync = useCatalogSync()` — один вызов; CatalogView.tsx стр. 33: `useCatalogSyncContext()` без своего вызова хука |

**Счёт авто-верифицируемых истин: 9/9 (истины 1–11 за вычетом 2 поведенческих iPhone-UAT)**

---

### Отложенные пункты (Step 9b)

Следующие критерии ROADMAP не верифицируемы программно — они явно отложены на конец вехи v1.3 согласно 13-02-SUMMARY.md (по образцу этапов 11 и 12):

| # | Критерий ROADMAP | Адресован в | Доказательство |
|---|-----------------|-------------|----------------|
| 1 | Фото, просмотренное ранее, видно в авиарежиме в т.ч. в Lightbox | конец вехи v1.3 | 13-02-SUMMARY.md § "Отложенная HUMAN-UAT" |
| 2 | ↻ не перекачивает старые фото (только новые в Cache Storage) | конец вехи v1.3 | Требует DevTools Safari / iPhone |
| 4 | QuotaExceededError не возникает на iPhone | конец вехи v1.3 | Требует реальный iPhone |
| 5 | Просмотр 5–10 товаров → авиарежим → фото видны | конец вехи v1.3 | 13-02-SUMMARY.md Task 3 |

Критерий 3 (maxEntries:450 соблюдается) — статически VERIFIED: sw.ts стр. 72 `maxEntries: 450`.

---

## Артефакты

| Артефакт | Ожидание | Статус | Детали |
|----------|----------|--------|--------|
| `lib/syncPhotos.ts` | diff + fire-and-forget prefetch, экспорт syncPhotos | ✓ VERIFIED | 48 строк, содержательная реализация; `syncPhotos` экспортирован |
| `components/ProductCard.tsx` | unoptimized на обоих Image + onError на PhotoPlaceholder | ✓ VERIFIED | unoptimized: 2 вхождения; onError: 2 вхождения; PhotoPlaceholder переиспользован |
| `app/sw.ts` | CacheFirst Cloudinary + CacheableResponsePlugin(200) + maxEntries:450/7д | ✓ VERIFIED | Все три условия выполнены |
| `lib/useCatalogSync.ts` | вызов syncPhotos после saveProducts + refetch в контракте | ✓ VERIFIED | Стр. 158: `await syncPhotos(fresh)`; стр. 46, 229: refetch |
| `components/CatalogSyncProvider.tsx` | createContext + Provider + useCatalogSyncContext + throw guard | ✓ VERIFIED | Один вызов useCatalogSync(); throw при отсутствии провайдера |
| `components/SyncButton.tsx` | busy/done state, disabled офлайн, animate-spin, галочка | ✓ VERIFIED | Все паттерны подтверждены grep-ом |
| `app/catalog/[secret]/layout.tsx` | `<SyncButton />` в шапке + `<CatalogSyncProvider>` обёртка | ✓ VERIFIED | Стр. 37, 45, 64 |

---

## Ключевые связи (Wiring)

| От | До | Через | Статус | Детали |
|----|-----|-------|--------|--------|
| ProductCard.tsx | res.cloudinary.com | `unoptimized` → браузер запрашивает raw URL | ✓ WIRED | Стр. 149, 300 |
| useCatalogSync.ts | lib/syncPhotos.ts | `await syncPhotos(fresh)` после `saveProducts` | ✓ WIRED | Стр. 158 |
| syncPhotos.ts | lib/catalogDb.ts | `getMeta/saveMeta("prevImageUrls")` | ✓ WIRED | Стр. 25, 47 |
| SyncButton.tsx | CatalogSyncProvider.tsx | `useCatalogSyncContext().refetch` + `isOnline` | ✓ WIRED | Стр. 15 |
| CatalogView.tsx | CatalogSyncProvider.tsx | `useCatalogSyncContext()` вместо прямого `useCatalogSync()` | ✓ WIRED | Стр. 33 |
| layout.tsx | SyncButton.tsx | `<SyncButton />` в правом блоке шапки | ✓ WIRED | Стр. 45 |

---

## Data-Flow Trace (Level 4)

| Артефакт | Переменная данных | Источник | Реальные данные | Статус |
|----------|------------------|----------|-----------------|--------|
| SyncButton.tsx | `refetch`, `isOnline` | `useCatalogSyncContext()` → `useCatalogSync()` → `sync` (useCallback) | useCatalogSync вызывает `/api/products` и `syncPhotos` | ✓ FLOWING |
| CatalogView.tsx | `sync.products`, `sync.status` | `useCatalogSyncContext()` → IDB + `/api/products` | `getProducts()` из IndexedDB + сервер | ✓ FLOWING |
| syncPhotos.ts | `prevUrls` | `getMeta<string[]>("prevImageUrls")` из IDB | IDB meta-хранилище, заполняется после каждой синхронизации | ✓ FLOWING |

---

## Поведенческие Spot-Checks

| Поведение | Команда | Результат | Статус |
|-----------|---------|-----------|--------|
| TypeScript типы корректны | `npx tsc --noEmit` | Нет вывода (0 ошибок) | ✓ PASS |
| Production-сборка успешна | `npm run build` | `✓ Compiled successfully`; serwist SW собран | ✓ PASS |

---

## Покрытие требований

| Требование | План | Описание | Статус | Доказательство |
|------------|------|----------|--------|----------------|
| IMG-01 | 13-01, 13-02 | Фото просмотренных товаров доступны офлайн | ✓ КОД ГОТОВ / ⏸ UAT отложена | unoptimized + CacheFirst + CacheableResponsePlugin |
| IMG-02 | 13-01, 13-02 | Lightbox с зумом работает офлайн | ✓ КОД ГОТОВ / ⏸ UAT отложена | Lightbox уже использовал raw img[src=getHiResUrl], SW ловит тот же домен |
| IMG-03 | 13-01 | Кэш не переполняет телефон (maxEntries:450/7д) | ✓ VERIFIED | sw.ts: ExpirationPlugin maxEntries:450 |
| SYNC-01 | 13-02 | Ручная кнопка «Обновить» в шапке | ✓ VERIFIED | SyncButton + layout + CatalogSyncProvider |
| SYNC-02 | 13-01 | Умная докачка: только новые фото (diff) | ✓ КОД VERIFIED | syncPhotos: Set-diff + if(prevUrls.length>0) |

---

## Anti-Паттерны

| Файл | Строка | Паттерн | Серьёзность | Вывод |
|------|--------|---------|-------------|-------|
| lib/syncPhotos.ts | 7 | `"use client"` в lib/ файле | ℹ️ Info | Директива добавлена т.к. файл импортирует client-only API (fetch, IDB); корректно для данного использования — не anti-pattern |
| Все файлы | — | TBD / FIXME / XXX / TODO / HACK | — | Не обнаружено |
| Все файлы | — | `return null` / `return []` / заглушки | — | Не обнаружено — все return содержательны |

Блокирующих anti-паттернов не найдено.

---

## Human Verification Required

### 1. iPhone-приёмка офлайн-фото (IMG-01, IMG-02, IMG-03)

**Тест:** Деплой: `git push` → дождаться Vercel. На реальном iPhone (Safari):
1. Открыть каталог по секретной ссылке онлайн, дождаться загрузки.
2. Прокрутить и открыть 5–10 карточек с фото; открыть 2–3 в Lightbox с зумом.
3. Включить авиарежим. Открыть те же карточки — фото видны. В Lightbox — видны.
4. Открыть товар, который НЕ просматривали онлайн → иконка-заглушка «нет фото», не битое изображение (D-06).
5. DevTools (опционально) → Cache Storage cloudinary-images ≤ 450 записей, ≤ ~50 МБ, без QuotaExceededError.
6. Снова онлайн → нажать ↻ → крутится → галочка; OfflineBar обновился; в Cache Storage — только новые URL (если есть), старые не перекачаны.

**Ожидаемый результат:** Все 6 пунктов пройдены без замечаний.

**Почему нужен человек:** Поведение SW, Cache Storage, iOS-квота и Safari-специфика не проверяемы статически — только на реальном устройстве.

**Когда проводить:** Перед финальной сдачей вехи v1.3 (после этапа 14).
**Сигнал возобновления:** «принято» (или описать расхождения).

---

## Итого

**Все 9 авто-проверяемых критериев подтверждены кодом и сборкой.**

Кодовый слой этапа 13 полностью реализован и не содержит заглушек:
- `lib/syncPhotos.ts` — содержательная реализация diff-алгоритма с Set(O1) и lazy-стратегией первой загрузки.
- `components/ProductCard.tsx` — оба `<Image>` имеют `unoptimized` и `onError` → `PhotoPlaceholder`.
- `app/sw.ts` — `CacheableResponsePlugin({ statuses: [200] })` добавлен; matcher и лимиты сохранены.
- `lib/useCatalogSync.ts` — `syncPhotos(fresh)` вызывается в правильном месте потока; `refetch: sync` в контракте.
- `components/CatalogSyncProvider.tsx` — единственный экземпляр `useCatalogSync()` с throw-guard.
- `components/SyncButton.tsx` — busy/done/disabled/animate-spin/галочка реализованы.
- `app/catalog/[secret]/layout.tsx` — `<CatalogSyncProvider>` оборачивает всё дерево; `<SyncButton />` в шапке.

**npx tsc --noEmit** — 0 ошибок.
**npm run build** — Compiled successfully (SW собран Serwist).

Единственная причина статуса `human_needed` — отложенная iPhone-UAT (явное решение владельца, зафиксировано в 13-02-SUMMARY.md и ROADMAP.md).

---

_Проверено: 2026-06-13T13:43:29Z_
_Верификатор: Claude (gsd-verifier)_
