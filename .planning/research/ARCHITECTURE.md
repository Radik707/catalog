# Architecture Research: PWA / Offline Layer

**Domain:** Offline PWA поверх существующего Next.js 14 App Router + Vercel + Google Sheets
**Researched:** 2026-06-12
**Confidence:** HIGH (интеграция Serwist с Next.js, стратегии кэширования, iOS-ограничения)

---

## Ключевое решение: как разрешить конфликт force-dynamic vs offline

Существующий `/api/products` имеет `export const dynamic = 'force-dynamic'` — Vercel не кэширует HTML-страницу. Это **не проблема**: service worker перехватывает HTTP-запрос **до** сервера. SW получает ответ JSON → кладёт в Cache Storage → при следующем вызове без сети — отдаёт из кэша. Serwist `NetworkFirst` делает это автоматически.

Однако одного SW-кэша недостаточно для надёжного офлайна, особенно на iOS (7-дневная eviction SW). Поэтому добавляем второй слой: клиент после успешного fetch сохраняет `Product[]` в IndexedDB. При запуске без сети: читаем из IndexedDB, не ждём SW. Это даёт двойную страховку.

**Итог: force-dynamic остаётся как есть. Ничего на сервере не меняется.**

---

## System Overview

```
╔══════════════════════════════════════════════════════════════════╗
║  СЕРВЕР (без изменений в v1.3)                                   ║
║  Vercel serverless                                               ║
║  GET /api/products  ──► lib/sheets.ts ──► Google Sheets API      ║
║  (force-dynamic, всегда свежий JSON)                             ║
╚══════════════════════╦═══════════════════════════════════════════╝
                       │ HTTPS JSON ~200 KB
                       ▼
╔══════════════════════════════════════════════════════════════════╗
║  SERVICE WORKER  (app/sw.ts, скомпилированный в public/sw.js)    ║
║                                                                  ║
║  ┌─────────────────────────────────────────────────────────┐    ║
║  │  precache: Next.js assets (JS, CSS, HTML-шелл)           │    ║
║  ├─────────────────────────────────────────────────────────┤    ║
║  │  NetworkFirst  /api/products  → "api-cache"              │    ║
║  │  (5s timeout → fallback на кэш)                          │    ║
║  ├─────────────────────────────────────────────────────────┤    ║
║  │  CacheFirst  res.cloudinary.com/**  → "image-cache"      │    ║
║  │  (maxEntries: 450, TTL: 7 дней)                          │    ║
║  └─────────────────────────────────────────────────────────┘    ║
╚══════════════════════╦═══════════════════════════════════════════╝
                       │ перехват fetch
                       ▼
╔══════════════════════════════════════════════════════════════════╗
║  КЛИЕНТ (браузер / PWA-standalone)                               ║
║                                                                  ║
║  ┌─────────────────────────────────────────────────────────┐    ║
║  │  useCatalogSync hook                                     │    ║
║  │  ┌────────────────────────────────────────────────────┐ │    ║
║  │  │  онлайн: fetch("/api/products")                     │ │    ║
║  │  │    └──► SW перехватывает ──► network + кэш          │ │    ║
║  │  │    └──► idb.saveProducts(data)  ──►  IndexedDB      │ │    ║
║  │  │    └──► idb.saveSyncTimestamp()                      │ │    ║
║  │  │                                                      │ │    ║
║  │  │  офлайн: idb.getProducts()  ◄──  IndexedDB          │ │    ║
║  │  └────────────────────────────────────────────────────┘ │    ║
║  └─────────────────────────────────────────────────────────┘    ║
║                                                                  ║
║  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   ║
║  │ CatalogView  │  │ CartProvider │  │  OfflineBar          │   ║
║  │ (от IndexedDB│  │ (localStorage│  │ (navigator.onLine +  │   ║
║  │  или fetch)  │  │  — без изм.) │  │  syncTimestamp)      │   ║
║  └──────────────┘  └──────────────┘  └──────────────────────┘   ║
║                                                                  ║
║  ┌──────────────────────────────────────────────────────────┐   ║
║  │  IndexedDB  (через idb)                                   │   ║
║  │  store: "products"  → Product[]                          │   ║
║  │  store: "meta"      → syncTimestamp, prevImageUrls[]     │   ║
║  └──────────────────────────────────────────────────────────┘   ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## Component Responsibilities

| Компонент | Ответственность | Файл |
|-----------|-----------------|------|
| `withSerwist` в next.config | Webpack-плагин: компилирует `app/sw.ts` → `public/sw.js`, инжектирует precache manifest | `next.config.mjs` (модифицировать) |
| `app/sw.ts` | Сам service worker: precache JS/CSS, NetworkFirst для `/api/products`, CacheFirst для Cloudinary | `app/sw.ts` (новый) |
| `app/manifest.ts` | Web App Manifest: имя, иконки, `start_url` с секретом, `display: standalone` | `app/manifest.ts` (новый) |
| `lib/catalogDb.ts` | Тонкая обёртка `idb`: open DB, getProducts, saveProducts, getSyncMeta, saveSyncMeta | `lib/catalogDb.ts` (новый) |
| `hooks/useCatalogSync.ts` | React hook: fetch → сохранить в IDB, читать из IDB, отдать `{products, syncedAt, isOnline}` | `lib/useCatalogSync.ts` (новый) |
| `components/OfflineBar.tsx` | Полоска «Офлайн • Данные за ЧЧ:ММ» / «Подключились — обновить?» | `components/OfflineBar.tsx` (новый) |
| `components/SyncButton.tsx` | Кнопка «Обновить каталог» + прогресс синхронизации фото | `components/SyncButton.tsx` (новый) |
| `components/InstallPrompt.tsx` | Баннер установки: Android `beforeinstallprompt` + iOS инструкция | `components/InstallPrompt.tsx` (новый) |
| `app/catalog/[secret]/page.tsx` | **Изменить**: не передавать `products` пропом с сервера; клиент читает из `useCatalogSync` | `app/catalog/[secret]/page.tsx` (модифицировать) |
| `components/CatalogView.tsx` | Принять `products` проп как и раньше; источник — теперь `useCatalogSync` вместо сервера | `components/CatalogView.tsx` (минимальные правки) |
| `app/catalog/[secret]/cart/page.tsx` | Добавить проверку `navigator.onLine` → деактивировать кнопку «Отправить» офлайн | `app/catalog/[secret]/cart/page.tsx` (модифицировать) |
| `app/layout.tsx` | Добавить PWA метаданные (`applicationName`, `appleWebApp`), подключить `InstallPrompt` | `app/layout.tsx` (модифицировать) |
| `public/icon-192.png`, `public/icon-512.png` | Иконки PWA (maskable) | `public/` (новые файлы, не код) |

---

## Рекомендуемая структура новых файлов

```
C:\catalog\
├── app\
│   ├── sw.ts                    # Service Worker (компилируется → public/sw.js)
│   ├── manifest.ts              # Web App Manifest (встроенный Next.js API)
│   └── catalog\[secret]\
│       └── page.tsx             # ИЗМЕНИТЬ: убрать SSR-пробрасывание products
├── components\
│   ├── OfflineBar.tsx           # Полоска офлайн-статуса + метка свежести
│   ├── SyncButton.tsx           # Кнопка ручного обновления + прогресс
│   └── InstallPrompt.tsx        # Баннер установки (Android + iOS)
├── lib\
│   ├── catalogDb.ts             # IndexedDB обёртка (через idb)
│   └── useCatalogSync.ts        # Hook: fetch → IDB → Product[] + статус
├── public\
│   ├── icon-192.png             # PWA иконка 192×192
│   └── icon-512.png             # PWA иконка 512×512 (maskable)
└── next.config.mjs              # ИЗМЕНИТЬ: обернуть withSerwist
```

---

## Architectural Patterns

### Pattern 1: Двухслойное хранение данных каталога

**Что:** SW Cache Storage (автоматический NetworkFirst) + IndexedDB (явное сохранение в `useCatalogSync`).

**Когда использовать:** Когда надёжность важнее простоты. SW-кэш на iOS может быть сброшен через 7 дней бездействия. IndexedDB — более персистентный слой.

**Соотношение слоёв:**
- SW Cache Storage = кэш HTTP-ответа, используется при обычных fetch-запросах
- IndexedDB = структурированный кэш данных, используется при старте приложения

**Пример (lib/useCatalogSync.ts):**
```typescript
// Упрощённая логика hook-а
export function useCatalogSync() {
  const [products, setProducts] = useState<Product[]>([]);
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  useEffect(() => {
    // 1. Сначала читаем из IndexedDB — мгновенный старт
    getProductsFromIDB().then(cached => {
      if (cached.length > 0) setProducts(cached);
    });

    // 2. Если онлайн — тянем свежее с сервера
    if (navigator.onLine) {
      fetch("/api/products")
        .then(r => r.json())
        .then((fresh: Product[]) => {
          setProducts(fresh);
          saveProductsToIDB(fresh);   // обновляем IndexedDB
          saveSyncTimestamp();
        })
        .catch(() => { /* используем данные из IDB */ });
    }
  }, []);

  return { products, isOnline, syncedAt: getSyncTimestamp() };
}
```

### Pattern 2: Перевод страницы каталога с SSR-данных на клиентский источник

**Что:** Сейчас `page.tsx` — Server Component, передаёт `products` пропом в `CatalogView`. После изменения `CatalogView` сам читает данные из `useCatalogSync`. Страница перестаёт быть source of truth для данных.

**Почему необходимо:** Серверный компонент работает только при сети. При офлайн-запуске PWA Serwist отдаст закэшированный HTML-шелл страницы, но SSR-данных в нём не будет (они не statically serialized в HTML при force-dynamic). Клиент должен читать данные сам.

**Изменения в page.tsx:**
```typescript
// БЫЛО (server component с данными):
// const products = await getProducts();
// return <CatalogView products={products} />;

// СТАЛО (server component — только оболочка):
// return <CatalogView />;
// CatalogView сам вызывает useCatalogSync() внутри
```

**Важно:** Проверка UUID-секрета (`params.secret !== CATALOG_SECRET → notFound()`) **остаётся на сервере** в `page.tsx`. Это нельзя убирать — безопасность.

### Pattern 3: CacheFirst для Cloudinary с умным diff

**Что:** SW перехватывает все запросы к `res.cloudinary.com` — стратегия CacheFirst. Фото попадают в кэш по мере просмотра. При синхронизации (кнопка «Обновить») — клиент сравнивает текущий список `imageUrl` с ранее сохранённым и prefetch-ит только новые.

**Почему diff безопасен:** Cloudinary URL-ы content-addressed по имени файла. Один и тот же URL (`akkond/500.jpg`) всегда означает одно и то же фото. Новые товары = новые URL. Старые URL не нужно перезакачивать.

**Пример логики diff в SyncButton.tsx:**
```typescript
async function syncPhotos(newProducts: Product[]) {
  const newUrls = newProducts.map(p => p.imageUrl).filter(Boolean);
  const prevUrls = await getPrevImageUrls(); // из IndexedDB meta
  const toFetch = newUrls.filter(url => !prevUrls.includes(url));

  // Prefetch только новые фото (SW перехватит и закэширует)
  for (const url of toFetch) {
    fetch(url, { mode: "no-cors" }).catch(() => {}); // огонь-и-забыл
  }

  await savePrevImageUrls(newUrls); // обновляем список для следующего diff
}
```

### Pattern 4: Регистрация SW без блокировки гидрации

**Что:** `@serwist/next` с `register: true` (дефолт) автоматически инжектирует код регистрации в entrypoint. Ничего дополнительного не нужно. Если нужен контроль (отложенная регистрация) — `register: false` + `window.serwist.register()` в `useEffect`.

**Рекомендация для этого проекта:** использовать `register: true` (автоматически). Ручная регистрация не даёт практических преимуществ при данной сложности.

---

## Data Flow

### Поток 1: Утренняя синхронизация (агент онлайн)

```
Агент открывает PWA
    │
    ▼
app/sw.ts зарегистрирован в браузере
    │
    ▼
CatalogView монтируется → useCatalogSync() вызывается
    │
    ├─► 1. getProductsFromIDB()  → мгновенный рендер из кэша (если есть)
    │
    └─► 2. fetch("/api/products")
              │
              ▼
          SW перехватывает → NetworkFirst
              │
              ├─► network → Google Sheets → Product[] JSON
              │         └─► SW кладёт в "api-cache"
              │         └─► клиент получает ответ
              │
              └─► saveProductsToIDB(products)
                  saveSyncTimestamp()
                  syncPhotos(products) → prefetch новых фото
                  (SW кэширует через CacheFirst)
```

### Поток 2: Работа без сети (агент офлайн)

```
Агент открывает PWA (нет сети)
    │
    ▼
SW отдаёт закэшированный HTML-шелл страницы (precache)
    │
    ▼
CatalogView монтируется → useCatalogSync()
    │
    ├─► navigator.onLine === false
    │
    └─► getProductsFromIDB() → Product[] из IndexedDB
              │
              ▼
          setProducts(cached)
          OfflineBar показывает "Офлайн • Данные за 08:30"
              │
              ▼
          Каталог, поиск, навигация — работают полностью
          Корзина (localStorage) — работает без изменений
          Кнопка «Отправить заказ» — задизейблена + подсказка
```

### Поток 3: Просмотр фото (онлайн и офлайн)

```
ProductCard / Lightbox запрашивает <img src="https://res.cloudinary.com/...">
    │
    ▼
SW перехватывает (CacheFirst)
    │
    ├─► Фото ЕСТЬ в "image-cache" → немедленно из кэша
    │
    └─► Фото НЕТ в кэше
              ├─► онлайн: fetch → кэшировать → показать
              └─► офлайн: возвращает placeholder (SW fallback)
```

### Поток 4: Обновление по требованию

```
Агент нажимает «Обновить каталог» (SyncButton)
    │
    ▼
fetch("/api/products")
    │
    ├─► SW NetworkFirst → сервер → свежий JSON
    │
    └─► Клиент:
          1. saveProductsToIDB(fresh)
          2. diff imageUrls: new vs prev
          3. prefetch(onlyNewUrls)  ← SW кэширует фото
          4. savePrevImageUrls(current)
          5. saveSyncTimestamp(now)
          6. setProducts(fresh)     ← UI обновляется без reload
```

---

## Integration Points

### Существующие компоненты: что изменяется, что нет

| Файл | Изменение | Объём |
|------|-----------|-------|
| `next.config.mjs` | Обернуть `withSerwist({swSrc, swDest, disable:dev})` | 6 строк |
| `app/layout.tsx` | Добавить PWA метаданные + `<InstallPrompt />` | 10 строк |
| `app/catalog/[secret]/page.tsx` | Убрать `getProducts()` + проп `products`; `<CatalogView>` без пропа | 5 строк удалить |
| `components/CatalogView.tsx` | Принять `products?: Product[]`, если не передан — вызвать `useCatalogSync()` | 15 строк |
| `app/catalog/[secret]/cart/page.tsx` | Проверка `navigator.onLine` → деактивация кнопки отправки | 5 строк |
| `tsconfig.json` | Добавить `"@serwist/next/typings"` в `compilerOptions.types` | 1 строка |
| `.gitignore` | Добавить `public/sw.js`, `public/swe-worker*.js` | 2 строки |

### Границы между слоями PWA

| Граница | Коммуникация | Комментарий |
|---------|-------------|-------------|
| SW ↔ Клиент (данные) | SW Cache Storage, перехват fetch | Прозрачный для React-кода |
| Клиент ↔ IndexedDB | `lib/catalogDb.ts` через `idb` | Единственный файл с IndexedDB API |
| Клиент → SW (команды) | `postMessage` (только для прогресса, если нужно) | В MVP не обязательно |
| SW lifecycle → Клиент | `updatefound` event → postMessage | Для баннера «Есть обновление» (P2) |

### Внешние сервисы: режим офлайн

| Сервис | Онлайн | Офлайн |
|--------|--------|--------|
| Vercel `/api/products` | Запрос → свежий JSON | SW отдаёт из "api-cache" |
| Cloudinary фото | Запрос → фото + SW кэширует | SW отдаёт из "image-cache" или placeholder |
| Google Sheets | Не затрагивается (только через Python) | — |
| Telegram deep-link | Работает | Блокируется проверкой `isOnline` |

---

## Anti-Patterns

### Anti-Pattern 1: Precache всех 900 фото при установке SW

**Что делают:** Добавляют все Cloudinary URL в `precache` список в `sw.ts`.

**Почему плохо:** iOS Cache Storage в браузере ограничен ~50 MB. 900 WebP ~80 KB = ~72 MB → SW установится с ошибкой квоты. Даже на Android: precache 900 URL при первом запуске = 5+ минут ожидания при первой установке, агент думает что приложение зависло.

**Правильно:** CacheFirst runtime caching — фото кэшируются по мере просмотра. При явной синхронизации — prefetch только новых URL через diff.

### Anti-Pattern 2: Оставить page.tsx как Server Component с SSR-данными

**Что делают:** Сохраняют `const products = await getProducts()` в `page.tsx` и передают в `CatalogView`.

**Почему плохо:** При офлайн-запуске SW отдаёт HTML-шелл страницы. В этом HTML нет serialized `products` (force-dynamic, не статичный). `CatalogView` получает пустой массив. Каталог пуст.

**Правильно:** `CatalogView` читает данные из `useCatalogSync()` → IndexedDB самостоятельно. `page.tsx` остаётся сервером только для проверки UUID-секрета.

### Anti-Pattern 3: Использовать SW `skipWaiting` без подтверждения пользователя

**Что делают:** `self.skipWaiting()` в activate-событии SW для «мгновенного» обновления.

**Почему плохо:** Агент работает с каталогом и корзиной. Новый SW активируется → страница перезагружается → корзина в localStorage сохраняется, но момент потери контекста раздражает. Ещё хуже — если обновление SW приходит в середине показа клиенту.

**Правильно:** Не использовать `skipWaiting` автоматически. Слушать `updatefound` + показать баннер «Доступно обновление — перезапустить?» (P2 фича). Агент сам решает когда обновиться.

### Anti-Pattern 4: Хранить данные каталога в localStorage

**Что делают:** `JSON.stringify(products)` → `localStorage.setItem(...)`.

**Почему плохо:** localStorage синхронный (блокирует main thread при ~200 KB JSON), ограничен 5–10 MB, нет TTL, нет транзакций. При 900 товарах с полями — размер вырастет. Ещё хуже: нельзя хранить Blob/фото.

**Правильно:** IndexedDB через `idb` — асинхронный, лимит сотни МБ, поддерживает структурированные объекты.

### Anti-Pattern 5: Кэшировать UUID-секрет каталога в Service Worker

**Что делают:** Добавляют маршрут `/catalog/[secret]` в precache manifest.

**Почему плохо:** `CATALOG_SECRET` — переменная окружения Vercel. При сборке она попадает в сгенерированный precache URL. Если секрет утечёт через SW manifest в `public/sw.js` — это security issue. Кроме того, при смене секрета старый SW будет пытаться precache старый URL.

**Правильно:** В `app/manifest.ts` использовать `start_url: "/catalog/YOUR_SECRET"` только если вы согласны что секрет виден в manifest (он всегда виден — это нормально для UUID-защиты). Для SW precache — кэшировать корневой HTML-шелл, не конкретный UUID-путь.

---

## Suggested Build Order

Порядок учитывает зависимости: каждый шаг опирается на предыдущий.

```
Этап 1: Foundation (SW + manifest) ← обязателен для всего остального
│   - next.config.mjs: withSerwist
│   - app/sw.ts: precache + NetworkFirst /api + CacheFirst Cloudinary
│   - app/manifest.ts: имя, иконки, start_url
│   - public/icon-192.png, public/icon-512.png
│   - app/layout.tsx: PWA metadata
│   Проверка: Chrome DevTools → Application → Service Workers
│
▼
Этап 2: Data layer (IndexedDB + useCatalogSync)
│   - lib/catalogDb.ts: openDB, getProducts, saveProducts, getMeta, saveMeta
│   - lib/useCatalogSync.ts: fetch → IDB → Product[] + syncedAt + isOnline
│   Проверка: DevTools → Application → IndexedDB — данные сохраняются
│
▼
Этап 3: UI переключение (CatalogView читает из hook, не из SSR)
│   - app/catalog/[secret]/page.tsx: убрать getProducts(), убрать проп
│   - components/CatalogView.tsx: читать из useCatalogSync()
│   Проверка: DevTools → Network → Offline → каталог отображает данные
│
▼
Этап 4: Офлайн UX (сигналы + корзина)
│   - components/OfflineBar.tsx: полоска со статусом и меткой времени
│   - app/catalog/[secret]/cart/page.tsx: блокировка кнопки офлайн
│   Проверка: Network Offline → видна полоска, кнопка задизейблена
│
▼
Этап 5: Sync button (умная синхронизация фото)
│   - components/SyncButton.tsx: кнопка + diff imageUrls + prefetch новых
│   Проверка: обновить каталог онлайн → только новые фото в "image-cache"
│
▼
Этап 6: Install prompt
    - components/InstallPrompt.tsx: Android beforeinstallprompt + iOS инструкция
    Проверка: Android Chrome → баннер установки, iOS Safari → инструкция
```

---

## Scaling Considerations

Данный проект — один агент, ~900 товаров, ~850 фото. Масштабирование не актуально для v1.3. Но стоит знать:

| Сценарий | Что изменится |
|----------|--------------|
| Несколько агентов (v2.0) | Каждый агент имеет свой IndexedDB в своём браузере. Никакого общего состояния нет. Масштабируется само. |
| Рост каталога до 5000 товаров | IndexedDB потянет. Cache Storage фото — нужно уменьшить `maxEntries` или сделать умный eviction по разделам. |
| Смена `CATALOG_SECRET` | SW precache нужно инвалидировать — новая сборка это делает автоматически (новый SW hash). |

---

## Sources

- Serwist официальная документация: https://serwist.pages.dev/docs/next/getting-started — HIGH confidence
- Serwist: register option: https://serwist.pages.dev/docs/next/configuring/register — HIGH confidence
- Next.js PWA guide: https://nextjs.org/docs/app/guides/progressive-web-apps — HIGH confidence
- Next.js Offline-First discussion (App Router + dynamic routes): https://github.com/vercel/next.js/discussions/82498 — MEDIUM confidence
- wellally.tech: Offline-first PWA with IndexedDB pattern: https://www.wellally.tech/blog/build-offline-first-pwa-nextjs-indexeddb — MEDIUM confidence
- WebKit Storage Policy (iOS квоты): https://webkit.org/blog/14403/updates-to-storage-policy/ — HIGH confidence
- Cloudinary PWA caching (Workbox): https://tpiros.dev/blog/a-cloudinary-plugin-for-workbox/ — MEDIUM confidence

---

*Architecture research for: PWA/Offline Layer, Next.js 14 App Router + Vercel + Google Sheets*
*Researched: 2026-06-12*
