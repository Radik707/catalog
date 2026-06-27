---
phase: 11-indexeddb-usecatalogsync
reviewed: 2026-06-12T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - lib/catalogDb.ts
  - lib/useCatalogSync.ts
  - components/CatalogView.tsx
  - app/catalog/[secret]/page.tsx
findings:
  critical: 2
  warning: 4
  info: 3
  total: 9
status: issues_found
---

# Этап 11: Отчёт код-ревью

**Проверено:** 2026-06-12
**Глубина:** standard
**Файлов проверено:** 4
**Статус:** issues_found (найдены проблемы)

## Сводка

Проверён слой IndexedDB (`catalogDb.ts`), клиентский хук stale-while-revalidate
(`useCatalogSync.ts`), витрина на его основе (`CatalogView.tsx`) и серверная страница
каталога (`page.tsx`).

Слой IndexedDB и логика синхронизации в целом аккуратны: обработка ошибок fetch
действительно деградирует в офлайн без throw, навигатор читается только внутри
колбэков (SSR безопасен), persist() защищён guard'ом, слушатели online/offline
снимаются в cleanup. Но есть **критическое нарушение Rules of Hooks** в `CatalogView`,
из-за которого React будет падать при смене статуса загрузки, и **race condition**
при гонке двух одновременных вызовов `sync()`. Их нужно исправить до выката.

## Critical Issues

### CR-01: Нарушение Rules of Hooks — ранний return до useMemo вызовет краш React

**Файл:** `components/CatalogView.tsx:50, 79, 104, 118, 147, 154`
**Issue:**
В компоненте есть условные ранние `return` при `status === "loading"` (строка 50)
и `status === "empty-offline"` (строка 79). А ниже, ПОСЛЕ этих return, вызываются
хуки `useMemo`: `flatFiltered` (104), `grouped` (118), `groupedCount` (147),
`photoProducts` (154).

При первом рендере (`status === "loading"`) React выполнит `useState` ×2,
`useCatalogSettings`, `useNav`, `useCatalogSync`, `useEffect` — и выйдет по return
на строке 50, НЕ вызвав четыре `useMemo`. Когда хук поменяет статус на `"ready"`,
рендер пройдёт дальше и вызовет эти `useMemo`. React увидит, что число хуков
изменилось между рендерами, и выбросит ошибку:
`"Rendered more hooks than during the previous render"` — белый экран вместо каталога.

Это именно тот путь, по которому идёт каждый первый офлайн-запуск
(`loading` → `ready` или `loading` → `empty-offline`), то есть баг проявится
у каждого пользователя при первом открытии.

**Fix:** Перенести ВСЕ вызовы хуков выше любых ранних return. Вычислять
`flatFiltered`, `grouped`, `groupedCount`, `photoProducts` безусловно, а ветвление
по `status` делать только в JSX (или вынести скелетон/заглушку в отдельные
компоненты). Пример каркаса:

```tsx
export default function CatalogView({ products: productsProp, initialMode }: CatalogViewProps) {
  const { viewMode, gridPreset, showPhotos, showPrices } = useCatalogSettings();
  const { mode, section, subgroup, setMode } = useNav();
  const [search, setSearch] = useState("");
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const sync = useCatalogSync();

  const products = productsProp ?? sync.products;
  const status = productsProp !== undefined ? "ready" : sync.status;

  useEffect(() => { /* initialMode */ }, []);

  const isFlat = Boolean(search.trim()) || mode !== "catalog";
  const flatFiltered = useMemo(() => { /* ... */ }, [products, search, isFlat, mode]);
  const grouped = useMemo(() => { /* ... */ }, [products, section, subgroup]);
  const groupedCount = useMemo(() => { /* ... */ }, [grouped]);
  const photoProducts = useMemo(() => { /* ... */ }, [isFlat, flatFiltered, grouped]);

  // Ранние return — ТОЛЬКО после всех хуков:
  if (status === "loading") return <SkeletonGrid />;
  if (status === "empty-offline") return <EmptyOffline />;

  // обычный рендер...
}
```

### CR-02: Race condition при гонке sync() — старый ответ может перезаписать свежий

**Файл:** `lib/useCatalogSync.ts:61-145, 157, 163`
**Issue:**
`sync()` запускается в трёх местах: при монтировании (157) и на каждое событие
`online` (163). Эти вызовы не сериализуются и не отменяются. Возможен сценарий:
сеть мигает (online → offline → online за секунду) → запускаются два параллельных
`fetch("/api/products")`. Ответы могут прийти в произвольном порядке, и более
старый ответ применится последним через `setProducts(fresh)` / `saveProducts(fresh)`,
перезаписав более свежие данные и в стейте, и в IndexedDB. Для каталога с ценами
и остатками это означает показ устаревших данных, которые при этом ещё и осядут
в офлайн-кэше до следующей удачной синхронизации.

Кроме того, нет дефенса от записи в стейт после размонтирования компонента
(`setProducts` после await при уже размонтированном `CatalogView` → React-warning
и потенциальная утечка).

**Fix:** Ввести «токен поколения» через ref и применять результат только если он
актуален. Также прервать предыдущий запрос через `AbortController`:

```ts
const runIdRef = useRef(0);
const mountedRef = useRef(true);

const sync = useCallback(async () => {
  const myRun = ++runIdRef.current;
  // ... fetch ...
  const fresh: Product[] = await res.json();
  if (myRun !== runIdRef.current || !mountedRef.current) return; // устарело — игнор
  setProducts(fresh);
  await saveProducts(fresh);
  // ...
}, []);

useEffect(() => {
  mountedRef.current = true;
  return () => { mountedRef.current = false; };
}, []);
```

(При желании добавить `AbortController` на сам `fetch`, чтобы не висели лишние запросы.)

## Warnings

### WR-01: Нет таймаута на fetch — «висящая» сеть не деградирует в офлайн

**Файл:** `lib/useCatalogSync.ts:103`
**Issue:**
Комментарий на строке 101 обещает, что таймаут трактуется как офлайн (D-04), но
`fetch("/api/products")` вызывается без `AbortController`/таймаута. При «висящей»
сети (captive portal, очень медленный канал) `navigator.onLine === true`, fetch
не падает и не завершается — промис висит, `status` остаётся `"loading"`, и
пользователь видит вечный скелетон вместо кэша/заглушки. Поведение расходится
с заявленным D-04.

**Fix:** Обернуть fetch в таймаут через `AbortController`:

```ts
const ctrl = new AbortController();
const t = setTimeout(() => ctrl.abort(), 8000);
try {
  const res = await fetch("/api/products", { signal: ctrl.signal });
  // ...
} finally {
  clearTimeout(t);
}
```

При abort сработает существующий `catch` (строка 134) и отработает офлайн-ветка.

### WR-02: Нет валидации формата ответа сервера — «успешный» мусор перетрёт кэш

**Файл:** `lib/useCatalogSync.ts:104-117`
**Issue:**
После `res.ok` ответ безусловно парсится `res.json()` и приводится к `Product[]`
без проверки. Если эндпоинт за прокси/CDN отдаст 200 с HTML-страницей ошибки или
пустым телом, либо вернёт `{}`/`null`, то:
`await res.json()` может бросить (это поймает catch — приемлемо), либо вернуть
не-массив, который через `setProducts(fresh)` уйдёт в UI, а через `saveProducts(fresh)`
перезапишет валидный офлайн-кэш мусором. На следующем офлайн-запуске
`cached.length` сломается (`undefined.length` → throw в getProducts? нет, но
`cached` будет не массивом, и `.length` даст undefined → ветки пойдут не так).

**Fix:** Проверить, что распарсенное — непустой массив, иначе трактовать как сбой:

```ts
const fresh = await res.json();
if (!Array.isArray(fresh)) throw new Error("Некорректный формат ответа /api/products");
// дополнительно можно отбросить пустой массив, если сервер не должен отдавать []
setProducts(fresh as Product[]);
await saveProducts(fresh as Product[]);
```

### WR-03: isOnline инициализируется true → SSR-разметка может разойтись с клиентом

**Файл:** `lib/useCatalogSync.ts:51, 152-154`
**Issue:**
`isOnline` стартует с `true` и корректируется в `useEffect` уже после монтирования.
Это осознанный SSR-safe приём, но `isOnline` — часть публичного контракта хука
(`UseCatalogSyncResult`). Если любой потребитель отрендерит UI по `isOnline` в
первом проходе (бейдж «офлайн», индикатор), будет mismatch гидрации/мерцание:
сервер и первый клиентский рендер дадут `true`, затем переключение на реальное
значение. Сейчас `CatalogView` `isOnline` не использует, поэтому это латентный
риск, а не активный баг — но контракт провоцирует ошибку у будущих потребителей.

**Fix:** Либо документировать в типе, что `isOnline` валиден только после
маунта, либо отдавать `isOnline: boolean | null` (null = «ещё не определено») и
заставлять потребителя обрабатывать неопределённость явно.

### WR-04: id товара = индекс строки → нестабильный ключ при подмене данных

**Файл:** `lib/useCatalogSync.ts:114` (+ источник `lib/sheets.ts:35`), `components/CatalogView.tsx:162, 179`
**Issue:**
`id` товара формируется как `String(index + 1)` по позиции строки в Google Sheet
(см. `lib/sheets.ts`). При бесшовной подмене `setProducts(fresh)` товар с `id="42"`
до и после синка может быть РАЗНЫМ товаром (если строки сместились — удалили/добавили
позицию). Последствия в `CatalogView`: `key={product.id}` (строка 180) у React
переиспользует DOM/состояние карточки под другим товаром (например, открытый flip
или выбранное в лайтбоксе), а `openLightbox` ищет по `p.id` (162) — после синка
индекс может указать на другой товар. Это не краш, но визуально «прыгающие»
карточки и неверная картинка в просмотрщике в момент обновления.

**Fix:** Использовать стабильный бизнес-ключ как id (например, артикул/штрихкод,
если есть в листе), либо хешировать `name`+`supplier`. Это изменение в `lib/sheets.ts`,
вне строго данного диапазона, но дефект проявляется именно через слой синхронизации
этапа 11, поэтому фиксирую.

## Info

### IN-01: useEffect с пустым deps и отключённым линтером скрывает initialMode-зависимость

**Файл:** `components/CatalogView.tsx:43-46`
**Issue:**
`useEffect(() => { if (initialMode ...) setMode(initialMode) }, [])` с
`eslint-disable-next-line react-hooks/exhaustive-deps`. Если `initialMode` сменится
после монтирования (смена `?filter=` без перемонтирования компонента, что при
клиентской навигации Next.js возможно), режим не обновится. Сейчас вероятно ОК
(страница серверная, перемонтируется), но disable-комментарий маскирует
потенциальный баг навигации.

**Fix:** Оставить как есть, если перемонтирование гарантировано, но добавить
комментарий, ПОЧЕМУ deps пустые (однократная инициализация), чтобы не пугать
будущего читателя.

### IN-02: Заявленное версионирование схемы IndexedDB не покрывает разрушающие миграции

**Файл:** `lib/catalogDb.ts:38-65`
**Issue:**
Комментарий обещает безопасную миграцию «без потери каталога», но upgrade-колбэк
только создаёт отсутствующие stores. При реальном breaking-change формата `Product`
(переименование/удаление поля) старые записи в `products` останутся в прежнем
формате, и `getProducts()` отдаст устаревшую структуру в типобезопасный `Product[]`
без фактической миграции. Сейчас `DB_VERSION = 1`, поэтому проблемы нет, но
комментарий создаёт ложное чувство защищённости (угроза T-11-02 не закрыта, лишь
задел).

**Fix:** Уточнить комментарий: текущий колбэк создаёт stores, но НЕ мигрирует данные;
при росте версии обязательна явная ветка `if (oldVersion < N)` с трансформацией или
очисткой `products`.

### IN-03: getMeta<T> приводит тип без проверки во время выполнения

**Файл:** `lib/catalogDb.ts:95-98`
**Issue:**
`getMeta<number>("syncTimestamp")` приводит произвольное значение из IDB к `T`
через `as`, без runtime-проверки. Если в базе под этим ключом окажется не число
(повреждение, ручное изменение в DevTools, смена формата), `syncedAt` получит
не-number и форматирование времени «последней синхронизации» сломается.
Низкий риск для внутренней утилиты.

**Fix:** Для критичных ключей валидировать тип на стороне вызова
(`typeof ts === "number"`), как уже частично делается на строке 81 (`ts !== undefined`).

---

_Проверено: 2026-06-12_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
