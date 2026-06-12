# Research Summary: Оффлайн-режим (PWA) — веха v1.3

**Проект:** Каталог «Вкусный Дом»
**Домен:** PWA / Offline-first поверх Next.js 14 App Router + Vercel + Google Sheets
**Исследовано:** 2026-06-12
**Уверенность:** HIGH

---

## Executive Summary

Добавление PWA-слоя к существующему каталогу — это brownfield-задача с чёткими паттернами и одним главным полем для ошибок: iOS Safari. Правильный инструмент — **`@serwist/next` v9.x** (официальный наследник next-pwa, активно поддерживается по май 2026). Вся серверная часть остаётся без изменений: `force-dynamic` на `/api/products` не является проблемой — service worker перехватывает HTTP-запрос на клиенте, стратегия `NetworkFirst` отдаёт свежий JSON при сети и кэшированный при её отсутствии. Единственное существенное изменение на уровне архитектуры: страница каталога перестаёт получать товары через SSR-проп, а `CatalogView` читает их из клиентского хука `useCatalogSync` → IndexedDB.

Главный риск всей вехи — iOS и её лимит Cache Storage в **~50 МБ на origin в браузере**. 900 фото × ~60 КБ = ~54 МБ, что вплотную к лимиту или за ним. Стратегия обязательна: `CacheFirst` on-demand с жёстким `maxEntries: 450` (фото кэшируются по мере просмотра), при синхронизации — **умный diff по URL**: Cloudinary URL стабильны по имени файла, поэтому качаем только те, которых не было в предыдущей версии каталога. Это делает ежедневное утреннее обновление быстрым и экономным по трафику.

Второй по важности риск — корректный жизненный цикл SW: `skipWaiting: false` по умолчанию, обновление только по явному согласию пользователя. Форсированный `skipWaiting` при активной вкладке каталога приведёт к `ChunkLoadError` и белому экрану у агентов в самый неподходящий момент — во время показа клиенту. Тестирование обязательно на реальном iPhone, не в симуляторе: квоты хранилища, установка через Share → Add to Home Screen, standalone-режим — всё это ведёт себя иначе.

---

## Key Findings

### Рекомендуемый стек

Минимальный набор новых зависимостей: три пакета.

**Установка:**
```bash
npm install @serwist/next idb
npm install -D serwist
```

**Основные технологии:**

| Технология | Версия | Назначение | Почему |
|-----------|--------|-----------|--------|
| `@serwist/next` | ^9.0.0 | Webpack-плагин + withSerwist | Единственный актуальный вариант; next-pwa и @ducanh2912/next-pwa устарели |
| `serwist` (dev) | ^9.0.0 | Движок SW: стратегии, ExpirationPlugin | Форк Workbox с активной разработкой |
| `idb` | ^8.0.0 | IndexedDB обёртка (~5 КБ) | Двойная страховка при iOS 7-day eviction; асинхронный, не блокирует поток |
| `app/manifest.ts` | Next.js built-in | Web App Manifest | Content-Type автоматически, не нужна внешняя либа |

**Не использовать:** `next-pwa` (shadowwalker), `@ducanh2912/next-pwa` — оба устарели, App Router не поддерживается.

**Открытый вопрос:** замерить реальный средний размер WebP-фото (выборка из `scripts/photo_urls.json`) перед реализацией кнопки «Загрузить все фото». Если средний >80 КБ — снизить `maxEntries` до 300–350.

---

### Ожидаемые фичи

**Обязательно (table stakes) — MVP v1.3:**

| Фича | Приоритет | Сложность |
|------|-----------|-----------|
| Весь каталог (~900 товаров + структура) доступен офлайн через IndexedDB | P1 | HIGH |
| Фото доступны офлайн для просмотренных товаров (CacheFirst on-demand, maxEntries: 450) | P1 | HIGH |
| Manifest + иконки + `display: standalone` — установка на домашний экран | P1 | MEDIUM |
| iOS install prompt (bottom-sheet «Поделиться → Добавить») — нет `beforeinstallprompt` на iOS | P1 | LOW |
| Кнопка «Обновить каталог» — явный ручной триггер синхронизации | P1 | LOW |
| Умный diff фото: качать только новые URL при обновлении | P1 | HIGH |
| Офлайн-индикатор в шапке + метка «Данные за ЧЧ:ММ» | P1 | LOW |
| Корзина офлайн работает, кнопка «Отправить заказ» заблокирована с пояснением | P1 | LOW |
| `navigator.storage.persist()` после первой синхронизации | P1 | LOW |

**Желательно (differentiators) — v1.3.x:**

| Фича | Приоритет |
|------|-----------|
| Прогресс синхронизации («Загрузка фото: 23/47 новых») | P2 |
| Баннер «Доступно обновление SW» (управляемый postMessage) | P2 |
| Кнопка «Очистить кэш фото» | P2 |
| Показ объёма хранилища через `navigator.storage.estimate()` | P2 |

**Отложить на v2+:**
- Фоновая синхронизация (Background Sync) — iOS до 16.4+ не поддерживает
- Push-уведомления об обновлении каталога
- Персональный кэш по агентам (многопользовательность — v2.0)

**Anti-features (никогда не делать):**
- Precache всех 900 фото при установке SW — `QuotaExceededError` на iOS
- `skipWaiting: true` глобально — `ChunkLoadError` при деплое
- Background Sync для отправки заказа — ненадёжно на iOS

---

### Архитектурный подход

Ключевое архитектурное изменение: `CatalogView` переводится с SSR-данных (`await getProducts()` в page.tsx) на клиентский хук `useCatalogSync`. При офлайн-запуске Serwist отдаёт закэшированный HTML-шелл, а данные хук читает из IndexedDB напрямую. Проверка UUID-секрета остаётся на сервере. Серверная часть, Google Sheets API, пайплайн прайсов — не меняются.

**Новые компоненты:**

| Файл | Ответственность |
|------|----------------|
| `app/sw.ts` | Service worker: precache JS/CSS, NetworkFirst `/api/products` (5s timeout), CacheFirst Cloudinary (maxEntries: 450, TTL 7 дней) |
| `lib/catalogDb.ts` | Единственная точка IndexedDB: stores `products` и `meta` (syncTimestamp, prevImageUrls) |
| `hooks/useCatalogSync.ts` | Онлайн → fetch + IDB; офлайн → IDB; возвращает `{products, syncedAt, isOnline}` |
| `components/OfflineBar.tsx` | Полоска «Офлайн • Данные за 08:30» / жёлтый цвет если >24 ч |
| `components/SyncButton.tsx` | Кнопка обновления + diff imageUrls + prefetch только новых URL |
| `components/InstallPrompt.tsx` | Android `beforeinstallprompt` + iOS UA-детекция + bottom-sheet инструкция |
| `app/manifest.ts` | Web App Manifest (Next.js built-in), `start_url` с CATALOG_SECRET |

**Изменяемые файлы (минимально):**
- `next.config.mjs` — `withSerwist` + headers для `sw.js` (`max-age=0, must-revalidate`) + `Service-Worker-Allowed: /`
- `app/catalog/[secret]/page.tsx` — убрать `getProducts()` и проп (~5 строк)
- `components/CatalogView.tsx` — читать из `useCatalogSync()` если нет пропа (~15 строк)
- `app/catalog/[secret]/cart/page.tsx` — блокировка кнопки при `!isOnline`
- `.gitignore` — добавить `public/sw.js`, `public/swe-worker*.js`

---

### Критические ловушки

1. **Взрыв квоты iOS при precache фото** — никогда не делать `caches.addAll(allPhotoUrls)`. Только `CacheFirst` runtime + `maxEntries: 450`. Тест обязателен на реальном iPhone. Признак: синхронизация занимает 3+ мин, часть фото — плейсхолдеры без ошибок.

2. **7-дневная iOS eviction** — вызвать `navigator.storage.persist()` после первой синхронизации. Двойной слой (SW Cache + IndexedDB) страхует. Агентов предупредить: «Открывайте приложение минимум раз в неделю».

3. **`skipWaiting: true` → ChunkLoadError** — оставить `skipWaiting: false` (Serwist default). Обновление SW — только по `postMessage SKIP_WAITING` после согласия в баннере.

4. **Vercel кэширует `sw.js` с `immutable`** — добавить заголовок `Cache-Control: max-age=0, must-revalidate` для `/sw.js` в `next.config.mjs`. Без этого агенты застрянут на старом SW после деплоя.

5. **SW в dev-режиме ломает разработку** — обязательно `disable: process.env.NODE_ENV === 'development'`. PWA-специфику тестировать только через `npm run build && npm run start`.

6. **SSR-данные в офлайн пусты** — при offline-запуске HTML-шелл не содержит serialized products (force-dynamic). Если оставить `await getProducts()` в page.tsx — офлайн-каталог будет пустым.

7. **Молчащий сбой «Отправить заказ» офлайн** — `window.open("tg://...")` непредсказуем в iOS standalone. Блокировать кнопку при `!navigator.onLine`.

---

## Implications for Roadmap

### Этап 1: Фундамент (SW + Manifest)

**Обоснование:** Service worker — основа всего. Здесь закладываются критические конфигурации, которые нельзя добавить потом без переработки: `disable:dev`, заголовки Vercel, `skipWaiting:false`, `maxEntries`.

**Доставляет:** `@serwist/next` подключён, `app/sw.ts` с NetworkFirst+CacheFirst, `app/manifest.ts`, иконки, заголовки Vercel, SW в `.gitignore`.

**Избегает:** Pitfall 1 (квота фото), Pitfall 3 (skipWaiting), Pitfall 5 (SW в dev), Pitfall 6 (Vercel immutable).

**Проверка:** DevTools → Service Workers: `activated`. Network `/sw.js`: `max-age=0`.

---

### Этап 2: Слой данных (IndexedDB + useCatalogSync)

**Обоснование:** IndexedDB — второй уровень страховки при iOS 7-day eviction. Меняет источник данных CatalogView — ключевое архитектурное изменение.

**Доставляет:** `lib/catalogDb.ts`, `hooks/useCatalogSync.ts`, изменения в `page.tsx` и `CatalogView.tsx`, `navigator.storage.persist()`.

**Избегает:** Pitfall 2 (7-day eviction), Pitfall 4 (CacheFirst для API), Anti-Pattern 2 (SSR-данные в офлайн).

**Проверка:** DevTools → IndexedDB → данные есть. Network: Offline → каталог показывает товары.

---

### Этап 3: Офлайн UX (индикаторы + корзина)

**Обоснование:** Без видимых сигналов агент паникует «сайт сломался». Простые компоненты с большой пользовательской ценностью.

**Доставляет:** `components/OfflineBar.tsx` с меткой свежести, блокировка кнопки заказа в корзине, empty-state при пустом кэше.

**Избегает:** UX Pitfall «нет индикатора», Pitfall 7 (молчащий сбой заказа).

**Проверка:** Авиарежим → шапка «Офлайн», кнопка корзины неактивна.

---

### Этап 4: Синхронизация фото (SyncButton + умный diff)

**Обоснование:** Без diff агент ежедневно качает ~51 МБ. Cloudinary URL стабильны по имени файла → diff по URL безопасен и даёт драматический выигрыш (обычно 5–50 новых фото в день).

**Доставляет:** `components/SyncButton.tsx`, логика diff `newUrls.filter(url => !prevUrls.includes(url))`, сохранение `prevImageUrls` в IndexedDB meta.

**Избегает:** Performance trap «sync 850 фото при каждом обновлении».

**Проверка:** Добавить новый товар → «Обновить» → в Cache Storage только новый URL.

---

### Этап 5: Install Prompt (Android + iOS)

**Обоснование:** Без подсказки iOS-агенты не знают о возможности установки. Идёт последним: промпт логично показывать когда каталог уже работает офлайн.

**Доставляет:** `components/InstallPrompt.tsx` (Android `beforeinstallprompt` + iOS bottom-sheet), PWA-метаданные в `layout.tsx`, однократный показ через localStorage-флаг.

**Избегает:** UX Pitfall «iOS-агент не знает как установить», «промпт при каждом визите».

**Проверка:** Android → баннер после просмотра каталога. iOS Safari → bottom-sheet с инструкцией. Standalone-режим без адресной строки.

---

### Research Flags

**Нужна проверка при планировании:**
- **Этап 2** — интеграция `useCatalogSync` с существующим `CatalogView`: проверить контракт пропов и поведение двухуровневой навигации при смене источника данных. Карта кода `.planning/codebase/` обязательна.
- **Этап 4** — замерить реальный средний размер WebP-фото из `photo_urls.json` перед финализацией `maxEntries` и решения о кнопке «Загрузить все фото».

**Стандартные паттерны (research-phase не нужен):**
- **Этап 1** — Serwist документация полная, официальный Next.js guide
- **Этап 3** — `navigator.onLine`, offline/online события — браузерный стандарт
- **Этап 5** — `beforeinstallprompt` и iOS UA-детекция — задокументированные паттерны

---

## Confidence Assessment

| Область | Уверенность | Примечания |
|---------|-------------|------------|
| Стек | HIGH | Serwist официально документирован; совместимость с Next.js 14 проверена |
| Фичи | HIGH | iOS-лимиты — официальный WebKit blog; B2B field sales паттерны сходятся |
| Архитектура | HIGH | Двухслойное хранение задокументировано; интеграция описана детально |
| Ловушки | HIGH (iOS) / MEDIUM (UX) | iOS — официальные источники; UX — отраслевой консенсус |

**Общая уверенность: HIGH**

### Пробелы для прояснения

- **Реальный размер WebP-фото** — замерить выборку из `photo_urls.json`. Если средний >80 КБ → снизить `maxEntries` до 300, отказаться от кнопки «Загрузить все».
- **Контракт данных CatalogView** — проверить все места передачи пропа `products` вглубь дерева; возможно, нужен React Context вместо проп-дриллинга.
- **iOS persist() на практике** — Safari принимает запрос по эвристикам (установка на home screen, частота посещений). Нет гарантий. Агентов нужно предупреждать явно в онбординге.

---

## Источники

### Первичные (HIGH confidence)
- `@serwist/next` docs: https://serwist.pages.dev/docs/next/getting-started
- Next.js PWA guide: https://nextjs.org/docs/app/guides/progressive-web-apps
- WebKit Storage Policy: https://webkit.org/blog/14403/updates-to-storage-policy/
- web.dev SW Update Lifecycle: https://web.dev/learn/pwa/update/
- MDN Offline and background operation: https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Offline_and_background_operation
- Vercel Cache-Control headers: https://vercel.com/docs/caching/cache-control-headers

### Вторичные (MEDIUM confidence)
- magicbell.com: iOS PWA Limitations 2026 — 50 МБ лимит, 7-day eviction
- magicbell.com: Offline-First PWA Caching Strategies — diff фото, инкрементальное обновление
- wellally.tech: Offline-first PWA with IndexedDB — двухслойное хранение, Next.js App Router
- Cloudinary documentation: URL versioning — стабильность URL, безопасность diff
- love2dev.com: Cache Storage Limits — квоты по платформам

---
*Research completed: 2026-06-12*
*Ready for roadmap: yes*
