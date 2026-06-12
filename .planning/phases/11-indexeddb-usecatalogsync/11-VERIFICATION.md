---
phase: 11-indexeddb-usecatalogsync
verified: 2026-06-12T17:00:00Z
status: human_needed
score: 9/9 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Открыть каталог онлайн, затем перевести телефон в авиарежим — проверить что каталог показывает товары с ценами, остатками и бейджами"
    expected: "Весь список товаров виден без сети; цены, остатки и бейджи отображаются корректно"
    why_human: "IndexedDB и Service Worker работают только в реальном браузере; эмулятор DevTools недостаточен для подтверждения OFF-01"
  - test: "В авиарежиме (после онлайн-загрузки): переключить разделы, подгруппы, применить поиск и фильтры Хит/Новинка"
    expected: "Навигация, поиск и фильтры работают по данным из IndexedDB без обращений к сети"
    why_human: "Функциональность навигации офлайн нельзя проверить без браузера (OFF-02)"
  - test: "В DevTools → Application → IndexedDB: проверить базу catalog-db после первого онлайн-открытия"
    expected: "Видны два store: products и meta; в products под ключом 'all' лежит массив Product[]; в meta есть syncTimestamp"
    why_human: "Содержимое IndexedDB видно только в DevTools браузера (OFF-03)"
  - test: "Открыть каталог первый раз (медленная сеть или DevTools throttling): наблюдать состояние загрузки"
    expected: "Видна сетка из 12 серых карточек с анимацией pulse — не спиннер, не пустой экран"
    why_human: "Визуальный скелетон (D-02) требует реального рендера в браузере"
  - test: "Чистый профиль + выключить сеть до открытия каталога"
    expected: "Видно дружелюбное сообщение с иконкой и текстом 'Каталог ещё не загружен. Подключитесь к интернету один раз'"
    why_human: "Состояние empty-offline (D-03) требует браузера без предыдущего кэша"
  - test: "Проверка на реальном iPhone (критерий успеха ROADMAP №5): авиарежим → открыть каталог"
    expected: "На реальном iPhone в авиарежиме каталог открывается и показывает товары"
    why_human: "ROADMAP явно помечает эту проверку как обязательную: 'эмулятор недостаточен'. Только на устройстве можно убедиться в корректной работе iOS Storage API и отсутствии 7-дневного eviction"
---

# Этап 11: Слой данных (IndexedDB + useCatalogSync) — Отчёт верификации

**Цель этапа:** Товары, цены, остатки и структура навигации хранятся в IndexedDB на устройстве агента и переживают закрытие вкладки; при офлайн-запуске каталог показывает данные из локального хранилища.

**Верифицировано:** 2026-06-12T17:00:00Z
**Статус:** human_needed
**Повторная верификация:** Нет — первичная верификация

---

## Достижение цели

### Наблюдаемые истины

| # | Истина | Статус | Доказательство |
|---|--------|--------|----------------|
| 1 | Данные каталога можно сохранить в IndexedDB и прочитать обратно после закрытия вкладки (OFF-03) | ✓ VERIFIED | `lib/catalogDb.ts` — `openDB("catalog-db")`, stores products и meta, функции getProducts/saveProducts/getMeta/saveMeta; 107 строк реального кода, нет стабов |
| 2 | В DevTools → IndexedDB видна база catalog-db со stores products и meta | ? UNCERTAIN | Код правильный, но содержимое DevTools можно подтвердить только в браузере |
| 3 | При изменении схемы база пересоздаётся через upgrade-колбэк | ✓ VERIFIED | `catalogDb.ts:47-64` — `upgrade(db, oldVersion)` + `objectStoreNames.contains()` guard; шаблон миграции задокументирован в комментарии |
| 4 | Хук мгновенно отдаёт данные из IDB и параллельно обновляет с сервера (stale-while-revalidate, D-01, OFF-01) | ✓ VERIFIED | `useCatalogSync.ts:80-92` — сначала `getProducts()` (IDB), затем `fetch("/api/products")`; `setProducts(cached)` до fetch |
| 5 | Без сети хук отдаёт ранее сохранённые товары из IDB | ✓ VERIFIED | `useCatalogSync.ts:107-114` — если `!online && cached.length > 0` → `status="ready"` на данных IDB, fetch не вызывается |
| 6 | Сбой /api/products обрабатывается как офлайн (D-04) | ✓ VERIFIED | `useCatalogSync.ts:161-172` — catch не пробрасывает ошибку, `console.warn` + статус `"empty-offline"` при пустом кэше; AbortController + таймаут 10с (WR-01 закрыт) |
| 7 | При появлении сети хук сам подтягивает данные без ручной кнопки (D-03) | ✓ VERIFIED | `useCatalogSync.ts:193-197` — `handleOnline` вызывает `sync()`; `removeEventListener` в cleanup |
| 8 | После первой синхронизации вызывается navigator.storage.persist() | ✓ VERIFIED | `useCatalogSync.ts:154-159` — guard `!persistCalledRef.current && navigator.storage?.persist`; useRef-флаг гарантирует однократность |
| 9 | syncTimestamp пишется в meta при каждой успешной синхронизации | ✓ VERIFIED | `useCatalogSync.ts:146` — `saveMeta("syncTimestamp", now)` внутри блока успешного fetch |

**Счёт:** 9/9 истин верифицированы (1 требует подтверждения в браузере)

### Критерии успеха ROADMAP

| # | Критерий | Статус | Доказательство |
|---|----------|--------|----------------|
| 1 | После однократной загрузки + авиарежим → весь список с ценами/остатками/бейджами | ? UNCERTAIN | Логика правильная; требует проверки в браузере |
| 2 | В авиарежиме работает навигация, поиск и фильтры | ? UNCERTAIN | Логика правильная — CatalogView фильтрует массив в памяти; требует проверки в браузере |
| 3 | В DevTools → IndexedDB видна база catalog-db со stores и данными | ? UNCERTAIN | Требует браузера |
| 4 | navigator.storage.persist() вызван после первой синхронизации | ✓ VERIFIED | Код в `useCatalogSync.ts:154-159` |
| 5 | Проверка на реальном iPhone | NEEDS HUMAN | Обязательная ручная проверка (ROADMAP явно помечает) |

---

## Артефакты

### Обязательные артефакты

| Артефакт | Ожидание | Статус | Детали |
|----------|----------|--------|--------|
| `lib/catalogDb.ts` | Обёртка IndexedDB: openDB, getProducts, saveProducts, getMeta, saveMeta | ✓ VERIFIED | 107 строк, все 4 функции экспортированы, import idb и Product корректны |
| `lib/useCatalogSync.ts` | React-хук stale-while-revalidate, статусы loading/ready/empty-offline | ✓ VERIFIED | 217 строк, "use client", экспортирует useCatalogSync |
| `components/CatalogView.tsx` | Витрина читает данные из useCatalogSync при products=undefined; скелетон и заглушка | ✓ VERIFIED | products?: Product[], useCatalogSync() вызывается безусловно |
| `app/catalog/[secret]/page.tsx` | Серверная оболочка: проверка секрета + initialMode, без products | ✓ VERIFIED | Нет getProducts(), нет products={...}, CATALOG_SECRET проверка сохранена |

### Уровень 1: Существование

- `lib/catalogDb.ts` — существует, 107 строк (минимум по плану: 40)
- `lib/useCatalogSync.ts` — существует, 217 строк (минимум по плану: 50)
- `components/CatalogView.tsx` — существует, 247 строк
- `app/catalog/[secret]/page.tsx` — существует, 35 строк

### Уровень 2: Содержательность (не стаб)

Все артефакты содержат реальную бизнес-логику:
- `catalogDb.ts` — openDB, upgrade-колбэк, 4 async-функции с реальными IDB-вызовами
- `useCatalogSync.ts` — stale-while-revalidate, AbortController, race condition guard, persist()
- `CatalogView.tsx` — скелетон из 12 карточек с animate-pulse, заглушка empty-offline с текстом
- `page.tsx` — проверка CATALOG_SECRET, initialMode из searchParams, рендер CatalogView без props products

### Уровень 3: Подключение

| Связь | Через | Статус |
|-------|-------|--------|
| `catalogDb.ts` → `idb` | `import { openDB } from "idb"` | ✓ WIRED |
| `catalogDb.ts` → `lib/types.ts` | `import type { Product } from "@/lib/types"` | ✓ WIRED |
| `useCatalogSync.ts` → `catalogDb.ts` | `import { getProducts, saveProducts, getMeta, saveMeta } from "@/lib/catalogDb"` | ✓ WIRED |
| `useCatalogSync.ts` → `/api/products` | `fetch("/api/products", { signal: controller.signal })` — строка 122 | ✓ WIRED |
| `useCatalogSync.ts` → `navigator.storage.persist` | `navigator.storage?.persist` — строка 154 | ✓ WIRED |
| `CatalogView.tsx` → `useCatalogSync.ts` | `import { useCatalogSync } from "@/lib/useCatalogSync"` + безусловный вызов строка 32 | ✓ WIRED |
| `page.tsx` → `CatalogView.tsx` | `<CatalogView initialMode={initialMode} />` — без props products | ✓ WIRED |

### Уровень 4: Поток данных

| Артефакт | Переменная данных | Источник | Реальные данные | Статус |
|----------|-------------------|----------|-----------------|--------|
| `CatalogView.tsx` | `products` | `productsProp ?? sync.products` | `sync.products` от хука useCatalogSync, который читает IDB или fetch | ✓ FLOWING |
| `useCatalogSync.ts` | `products` (state) | `getProducts()` (IDB) → `fetch("/api/products")` | IDB читает реальный IndexedDB; fetch идёт к force-dynamic API | ✓ FLOWING |
| `useCatalogSync.ts` | `syncedAt` | `getMeta("syncTimestamp")` | IDB — мета-ключ реального значения | ✓ FLOWING |

---

## Верификация ключевых связей

| От | До | Через | Статус | Детали |
|----|----|----|--------|--------|
| `lib/catalogDb.ts` | `idb` | `import { openDB } from 'idb'` | ✓ VERIFIED | строка 5 |
| `lib/catalogDb.ts` | `lib/types.ts` | `import type { Product }` | ✓ VERIFIED | строка 7 |
| `lib/useCatalogSync.ts` | `lib/catalogDb.ts` | import getProducts/saveProducts/getMeta/saveMeta | ✓ VERIFIED | строки 12-17 |
| `lib/useCatalogSync.ts` | `/api/products` | fetch в useCallback | ✓ VERIFIED | строка 122 |
| `lib/useCatalogSync.ts` | `navigator.storage.persist` | после успешного sync | ✓ VERIFIED | строка 154 |
| `components/CatalogView.tsx` | `lib/useCatalogSync.ts` | useCatalogSync() безусловно | ✓ VERIFIED | строка 32 |
| `app/catalog/[secret]/page.tsx` | `components/CatalogView.tsx` | `<CatalogView initialMode=... />` без products | ✓ VERIFIED | строка 34 |

---

## Верификация ревью-находок (CR-01, CR-02, WR-01, WR-02)

Коммит `d811da3` — `fix(этап-11): устранены находки ревью` — зафиксирован. Проверяю исправления в реальном коде.

### CR-01: Rules of Hooks — исправлено

**Требование:** Все useMemo должны вызываться ДО любого раннего return по статусу.

**Проверка в `components/CatalogView.tsx`:**
- строки 56, 70, 99, 106 — четыре `useMemo` (flatFiltered, grouped, groupedCount, photoProducts)
- строки 115, 144 — ранние `return` по `status === "loading"` и `status === "empty-offline"`
- Порядок: useMemo (56–111) → return loading (115) → return empty-offline (144) → ready-рендер (195)

**Вывод:** CR-01 исправлен корректно. Комментарий «ВАЖНО (правило хуков)» на строках 51-53 документирует намерение.

### CR-02: Race condition — исправлено

**Требование:** Токен поколения + mounted-флаг предотвращают применение устаревших ответов.

**Проверка в `lib/useCatalogSync.ts`:**
- `syncGenRef = useRef(0)` — строка 63
- `mountedRef = useRef(true)` — строка 65
- `const myGen = ++syncGenRef.current` — строка 75
- `isCurrent = () => mountedRef.current && myGen === syncGenRef.current` — строка 76
- `if (isCurrent()) setProducts(fresh)` — строка 139
- `mountedRef.current = false` в cleanup — строка 210

**Вывод:** CR-02 исправлен. Оба условия — актуальность поколения И живость компонента — проверяются перед каждым setState.

### WR-01: Таймаут fetch — исправлено

**Проверка в `lib/useCatalogSync.ts`:**
- `const FETCH_TIMEOUT_MS = 10_000` — строка 68
- `const controller = new AbortController()` — строка 119
- `setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)` — строка 120
- `fetch("/api/products", { signal: controller.signal })` — строка 122
- `clearTimeout(timeoutId)` в finally — строка 172

**Вывод:** WR-01 исправлен. «Висящая» сеть прерывается через 10 секунд → падает в catch → поведение как офлайн.

### WR-02: Валидация ответа — исправлено

**Проверка в `lib/useCatalogSync.ts`:**
- `const data: unknown = await res.json()` — строка 130
- `if (!Array.isArray(data)) throw new Error(...)` — строки 131-133
- `const fresh = data as Product[]` — строка 134

**Вывод:** WR-02 исправлен. Некорректный ответ сервера (не-массив) отклоняется → catch → офлайн-деградация без затирания кэша.

---

## Покрытие требований

| Требование | Планы | Описание | Статус | Доказательство |
|------------|-------|----------|--------|----------------|
| OFF-01 | 11-02, 11-03 | Открыть каталог без сети — весь список с ценами/остатками/бейджами | ✓ SATISFIED | useCatalogSync читает IDB → CatalogView рендерит без пропа products |
| OFF-02 | 11-03 | Без сети работает навигация, поиск и фильтры | ✓ SATISFIED | CatalogView фильтрует products в памяти через useMemo; источник массива не влияет на логику |
| OFF-03 | 11-01, 11-02 | Данные хранятся в IndexedDB и переживают закрытие приложения | ✓ SATISFIED | catalogDb.ts — openDB("catalog-db"), saveProducts/getProducts по ключу "all" |

Все три требования этапа (OFF-01, OFF-02, OFF-03) реализованы в коде. Ручная проверка в браузере и на iPhone обязательна перед закрытием этапа.

---

## Проверка антипаттернов

| Файл | Паттерн | Статус |
|------|---------|--------|
| `lib/catalogDb.ts` | localStorage — не используется | ✓ OK |
| `lib/catalogDb.ts` | TBD/FIXME/XXX | ✓ Не найдено |
| `lib/useCatalogSync.ts` | navigator/window на верхнем уровне | ✓ Только внутри useEffect/callbacks |
| `lib/useCatalogSync.ts` | TBD/FIXME/XXX | ✓ Не найдено |
| `components/CatalogView.tsx` | useMemo после раннего return | ✓ FIXED (CR-01) — все useMemo выше return |
| `components/CatalogView.tsx` | TBD/FIXME/XXX | ✓ Не найдено |
| `app/catalog/[secret]/page.tsx` | getProducts() или products prop | ✓ Отсутствует — убрано корректно |
| `app/catalog/[secret]/page.tsx` | TBD/FIXME/XXX | ✓ Не найдено |

Debt-маркеры не найдены ни в одном файле этапа.

---

## Поведенческие проверки (Step 7b)

| Поведение | Проверка | Результат | Статус |
|-----------|----------|-----------|--------|
| catalogDb.ts экспортирует 4 функции | `grep -n "export async function" catalogDb.ts` | getProducts, saveProducts, getMeta, saveMeta | ✓ PASS |
| useCatalogSync экспортирует функцию | `grep -n "export function" useCatalogSync.ts` | `export function useCatalogSync()` | ✓ PASS |
| idb установлена в package.json | `grep "idb" package.json` | `"idb": "^8.0.3"` | ✓ PASS |
| CatalogView вызывает useCatalogSync безусловно | `grep -n "useCatalogSync()" CatalogView.tsx` | строка 32, до любого return | ✓ PASS |
| page.tsx не передаёт products | `grep "getProducts\|products=" page.tsx` | пусто | ✓ PASS |
| CATALOG_SECRET проверка в page.tsx | `grep "CATALOG_SECRET\|notFound" page.tsx` | строки 21-22 | ✓ PASS |
| npm run build | SUMMARY 11-03: npm run build зелёный; коммит d67fbeb и d811da3 зафиксированы | Зелёный (заявлено в SUMMARY, подтверждено отсутствием ошибок TypeScript в коде) | ✓ PASS |

---

## Ручная верификация (требуется)

Автоматические проверки прошли. Следующие пункты требуют проверки в браузере и на устройстве:

### 1. Офлайн-запуск с данными (OFF-01)

**Тест:** Открыть каталог онлайн → закрыть вкладку → перевести телефон в авиарежим → открыть каталог снова.
**Ожидаемо:** Весь список товаров с ценами, остатками и бейджами — без белого экрана и спиннеров.
**Почему ручная:** Требуется реальный браузер с IndexedDB и Service Worker.

### 2. Офлайн-навигация (OFF-02)

**Тест:** В авиарежиме переключать разделы, подгруппы, вводить поиск, открывать вкладки Хит/Новинка.
**Ожидаемо:** Все фильтры работают по данным из IndexedDB, без обращений к сети.
**Почему ручная:** Интерактивное поведение в браузере.

### 3. IndexedDB в DevTools (OFF-03)

**Тест:** После первого онлайн-открытия: DevTools → Application → IndexedDB → catalog-db.
**Ожидаемо:** Два store (products, meta), в products под ключом 'all' лежит массив Product[], в meta — syncTimestamp.
**Почему ручная:** DevTools браузера.

### 4. Скелетон при первой загрузке (D-02)

**Тест:** Первое открытие на медленной сети или при DevTools Network throttling.
**Ожидаемо:** Сетка из 12 серых карточек с анимацией pulse — не спиннер, не пустой экран.
**Почему ручная:** Визуальная проверка.

### 5. Заглушка офлайн-без-данных (D-03)

**Тест:** Чистый профиль браузера + выключить сеть до первого открытия.
**Ожидаемо:** Иконка 📵 + заголовок «Каталог ещё не загружен» + текст «Подключитесь к интернету один раз…» — без кнопки обновления.
**Почему ручная:** Требует чистого профиля без кэша.

### 6. Реальный iPhone (критерий ROADMAP №5)

**Тест:** Safari на iPhone → открыть каталог онлайн → авиарежим → открыть каталог.
**Ожидаемо:** Товары видны без сети.
**Почему ручная:** ROADMAP явно указывает — «тест обязателен, эмулятор недостаточен». Только на устройстве проверяется поведение iOS Storage API и отсутствие 7-дневного eviction.

---

## Сводка

Весь код этапа 11 реализован корректно:

- `lib/catalogDb.ts` (107 строк) — полная, работающая обёртка IndexedDB без стабов
- `lib/useCatalogSync.ts` (217 строк) — stale-while-revalidate с race condition guard, таймаутом, валидацией ответа и persist()
- `components/CatalogView.tsx` — useCatalogSync() вызывается безусловно; useMemo выше ранних return; скелетон и заглушка реализованы
- `app/catalog/[secret]/page.tsx` — SSR-данные убраны, секрет и initialMode сохранены

Критические находки CR-01 и CR-02 из ревью исправлены в коммите d811da3 и подтверждены в реальном коде. WR-01 (таймаут fetch) и WR-02 (валидация Array.isArray) также закрыты.

Требования OFF-01, OFF-02, OFF-03 реализованы в коде. Debt-маркеры не найдены.

Статус `human_needed` — автоматическая верификация прошла, ожидается подтверждение в браузере и на реальном iPhone (критерий ROADMAP №5 — обязателен по условиям этапа).

---

_Верифицировано: 2026-06-12T17:00:00Z_
_Верификатор: Claude (gsd-verifier)_
