# Pitfalls Research: Offline PWA поверх Next.js/Vercel каталога

**Domain:** Добавление offline/PWA-слоя к существующему B2B-каталогу (Next.js 14 + Vercel + ~900 фото на Cloudinary + force-dynamic API + iOS + Android)
**Researched:** 2026-06-12
**Confidence:** HIGH (iOS storage — официальный WebKit blog; SW lifecycle — web.dev официально; Vercel headers — официальная документация Vercel); MEDIUM (cart/order offline UX — отраслевые паттерны)

---

## Вводный контекст

Все ловушки ниже специфичны для **этого** проекта: Next.js 14 App Router на Vercel free tier, данные через `force-dynamic` `/api/products` из Google Sheets, ~853 фото на Cloudinary (WebP, ~30–80 КБ каждое), корзина в `localStorage`, заказ через Telegram `window.open()` deep-link. Телефоны агентов — смешанные Android + iPhone. Сегодня service worker отсутствует полностью.

---

## Critical Pitfalls

### Pitfall 1: Precache всех ~900 фото при старте SW — взрыв квоты на iOS

**What goes wrong:**
Разработчик подключает `@serwist/next`, добавляет `runtimeCaching` для `res.cloudinary.com` с агрессивной стратегией и при первой установке SW или при нажатии «Обновить» начинает качать все известные URL фото. 850 фото × ~60 КБ (средний WebP) = **~51 МБ**. На iOS Safari Cache Storage в браузерном режиме ограничена **~50 МБ на origin** (Safari imposes a 50MiB limit). SW завершается с `QuotaExceededError` в середине закачки. Часть фото попадает в кэш, часть нет. Приложение выглядит работающим, но ~200 случайных товаров показывают placeholder вместо фото в офлайн — молча, без ошибки в UI.

**Why it happens:**
Логика «офлайн = всё на телефоне» кажется правильной. Разработчик добавляет `prefetchImages()` или `installEvent.waitUntil(caches.open(...).then(c => c.addAll(allPhotoUrls)))` и уходит. На рабочем столе в Chrome всё работает (там квота 60–80% диска). На реальном iPhone не тестировалось.

**How to avoid:**
Стратегия **CacheFirst on-demand** с жёстким лимитом: фото попадают в кэш только когда браузер действительно запрашивает их (при прокрутке каталога). В `app/sw.ts`:
```typescript
registerRuntimeCaching({
  matcher: /^https:\/\/res\.cloudinary\.com\/.*/i,
  handler: new CacheFirst({
    cacheName: "image-cache",
    plugins: [
      new ExpirationPlugin({ maxEntries: 450, maxAgeSeconds: 7 * 24 * 60 * 60 }),
    ],
  }),
});
```
`maxEntries: 450` — жёсткий потолок. При переполнении Workbox/Serwist автоматически удаляет LRU-записи. Предзагрузка только нового раздела — не всего каталога.

**Warning signs:**
- Safari DevTools → Storage показывает Cache Storage > 40 МБ
- При прокрутке каталога часть фото пуста без ошибки в консоли
- `QuotaExceededError` в Service Worker логах (`chrome://serviceworker-internals` или Safari Web Inspector)
- Первая синхронизация занимает 3+ минут на хорошем 4G

**Phase to address:**
Фаза 1 (базовый SW + manifest). Лимит `maxEntries` закладывается с самого начала — не добавляется потом.

---

### Pitfall 2: 7-дневная экспирация iOS уничтожает весь кэш агента

**What goes wrong:**
Агент установил PWA, сделал первую синхронизацию, неделю был в отпуске (или праздники). Возвращается, открывает каталог офлайн — пустой список, нет фото. Safari очистил всё хранилище SW (Cache Storage + IndexedDB), потому что происхождение (origin) не взаимодействовало 7+ дней. Это **best-effort mode** по умолчанию для всех источников.

**Why it happens:**
Safari с iOS 13.4 применяет cap на script-writable storage для сайтов, не посещавшихся 7 дней. По умолчанию хранилище в режиме `best-effort` (не `persistent`). Разработчики не вызывают `navigator.storage.persist()` и не документируют это агентам.

**How to avoid:**
1. Вызвать `navigator.storage.persist()` сразу после первой успешной синхронизации:
```typescript
if (navigator.storage && navigator.storage.persist) {
  const granted = await navigator.storage.persist();
  // на iOS 17+ Safari грантует на основе эвристик (добавлено на home screen, частое посещение)
  // не полагаться на результат, но вызвать обязательно
}
```
2. Показывать метку «Данные за ЧЧ:ММ ДД.ММ» в шапке — агент видит устаревание ещё до поля.
3. Документировать в инструкции для агентов: «Открывайте приложение хотя бы раз в неделю для сохранения данных».
4. При старте приложения: если `IndexedDB` пуст и сеть есть — автоматически запустить синхронизацию.
5. Offline-fallback страница должна явно писать «Нет сохранённых данных. Подключитесь к сети и обновите каталог», а не показывать пустой список.

**Warning signs:**
- Агент жалуется «вышел из отпуска — каталог пустой»
- `navigator.storage.estimate()` возвращает `usage: 0` при заходе после паузы
- В Safari DevTools IndexedDB store пустой

**Phase to address:**
Фаза 1 (базовый SW) — вызов `persist()`. Фаза 2 (синхронизация данных) — логика проверки наличия данных при старте.

---

### Pitfall 3: Устаревший SW — пользователи застряли на старой версии

**What goes wrong:**
В прод отгружается новая версия кода: исправлена ошибка в карточке товара, изменён интерфейс. Но агенты продолжают видеть старый интерфейс — SW кэшировал предыдущий `/_next/static/...` и обслуживает его. Новый SW скачан браузером, но находится в состоянии `waiting` — он не активируется, пока хоть одна вкладка/окно с приложением открыта. Агент всегда держит каталог открытым («свернул, не закрыл»). Дни идут, агент работает на старой версии.

**Why it happens:**
Стандартное поведение SW lifecycle: новый SW ждёт пока все клиенты не закроются. Разработчик добавляет `skipWaiting: true` в Serwist-конфиг «чтобы обновление применялось сразу» — это решает одну проблему и создаёт другую: страница, загруженная со старым SW, начинает получать ресурсы через новый SW в середине сессии. Результат: смешанные версии JS-чанков, ошибки типа `ChunkLoadError`, белый экран.

**How to avoid:**
**Не использовать `skipWaiting: true` по умолчанию.** Рекомендованный паттерн:

1. Новый SW остаётся в `waiting` (поведение по умолчанию в Serwist — `skipWaiting: false`)
2. SW отправляет сообщение странице через `postMessage` при обнаружении обновления (`updatefound` + `statechange: 'installed'`)
3. Страница показывает баннер: «Доступно обновление. Обновить сейчас?»
4. Только при нажатии «Обновить» — страница отправляет SW команду `SKIP_WAITING`, затем делает `location.reload()`

```typescript
// В компоненте UpdateBanner.tsx
useEffect(() => {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      window.location.reload(); // перезагрузка только по согласию
    });
  }
}, []);
```

**Warning signs:**
- После деплоя агенты сообщают «всё равно старое»
- В Chrome DevTools Application → Service Workers новый SW в статусе `waiting` часами
- `ChunkLoadError` в консоли после `skipWaiting: true` + деплоя
- Агент видит UI-изменения только после «закрыть все вкладки и открыть заново»

**Phase to address:**
Фаза 1 (базовый SW) — правильная конфигурация `skipWaiting: false`. Фаза 3 (UX обновления) — компонент баннера.

---

### Pitfall 4: Кэширование `force-dynamic` API — каталог застыл навсегда

**What goes wrong:**
`/api/products` помечен `export const dynamic = 'force-dynamic'` — Vercel не кэширует ответ на сервере. Но SW перехватывает этот запрос и кэширует его в `Cache Storage`. Если использовать стратегию `CacheFirst` для этого маршрута — агент никогда не получит новые данные, даже когда онлайн. Новые товары, изменённые цены, скрытые позиции — всё игнорируется. Данные в SW-кэше не имеют срока истечения и могут жить месяцами.

**Второй сценарий:** разработчик не добавляет `/api/products` в `runtimeCaching` совсем. SW использует `NetworkOnly` для API по умолчанию. В офлайн — запрос падает с ошибкой сети, `getProducts()` возвращает `[]`, каталог пустой. Данные в IndexedDB есть, но они не используются как fallback.

**Why it happens:**
Разработчик не разделяет «данные приложения» (JS/CSS — кэш надолго) и «данные каталога» (всегда свежие). `force-dynamic` сигнализирует только серверу Vercel, но SW ничего не знает о директивах Next.js.

**How to avoid:**
Двухслойная стратегия:

1. **SW `NetworkFirst` для `/api/products`** с `networkTimeoutSeconds: 5`:
   - При сети — свежий ответ + сохраняется в SW Cache как fallback
   - В офлайн — SW отдаёт последний закэшированный JSON
   - `networkTimeoutSeconds: 5` — если Google Sheets тормозит, через 5 сек отдаёт кэш

2. **IndexedDB (idb) как второй уровень** — клиентский код после успешного fetch записывает `Product[]` в IndexedDB. Если SW cache тоже промахивается (iOS очистил) — React компонент читает из IndexedDB напрямую.

```typescript
// В sw.ts
registerRuntimeCaching({
  matcher: ({ url }) => url.pathname === '/api/products',
  handler: new NetworkFirst({
    cacheName: 'api-cache',
    networkTimeoutSeconds: 5,
    plugins: [new ExpirationPlugin({ maxEntries: 1, maxAgeSeconds: 24 * 60 * 60 })],
  }),
});
```

**Warning signs:**
- После обновления прайсов на сервере агент видит старые цены при наличии сети
- В DevTools: Cache Storage содержит `/api/products` с датой недельной давности
- `force-dynamic` в коде и одновременно `CacheFirst` в SW — явное противоречие

**Phase to address:**
Фаза 2 (синхронизация данных) — правильная стратегия кэширования API и IndexedDB-слой.

---

### Pitfall 5: SW кэширует всё в разработке — невозможно отлаживать

**What goes wrong:**
Разработчик добавляет `@serwist/next` без опции `disable: process.env.NODE_ENV === 'development'`. SW регистрируется в dev-режиме, кэширует страницы и API. Дальнейшие изменения кода не отображаются в браузере — SW отдаёт старую версию. Разработчик тратит часы в поисках «почему правка не применяется». Hard refresh (`Ctrl+Shift+R`) не помогает. Нужно вручную идти в DevTools → Application → Service Workers → Unregister.

**Второй сценарий:** тестирование iOS производится только в симуляторе Xcode или через Chrome DevTools Remote Debug. Симулятор показывает рабочую установку, Chrome Remote Debug не воспроизводит quirks iOS Safari standalone. На реальном iPhone обнаруживаются: другое поведение viewport при standalone mode, иная обработка `beforeinstallprompt` (которого нет совсем), другие лимиты Cache API.

**Why it happens:**
SW — браузерная фича, работающая независимо от hot-reload Next.js. После регистрации живёт до явного удаления. Эмулятор Safari в macOS не полностью воспроизводит iOS Safari standalone PWA поведение.

**How to avoid:**
1. **Обязательно** в `next.config.mjs`:
```javascript
withSerwistInit({
  swSrc: "app/sw.ts",
  swDest: "public/sw.js",
  disable: process.env.NODE_ENV === "development", // SW только в production
})
```
2. Для тестирования PWA-специфики в dev — запускать `npm run build && npm run start`, не `npm run dev`.
3. **Тестировать на реальном iPhone**, не в симуляторе. Для iOS-специфики (install prompt, standalone mode, Cache Storage лимиты) симулятор даёт ложную уверенность. Минимум: проверить установку на home screen, открытие в standalone, кэш при offline — на физическом устройстве.
4. Добавить в `.gitignore`:
```
public/sw.js
public/swe-worker*.js
```
Иначе сгенерированный SW попадает в git и может конфликтовать при следующей сборке.

**Warning signs:**
- «Я изменил компонент, но в браузере ничего не изменилось» при активном SW
- DevTools → Application → Service Workers показывает статус `activated` в dev-режиме
- После `git pull` + сборки в браузере старая версия SW из `public/sw.js` предыдущего коммита

**Phase to address:**
Фаза 1 (базовый SW) — конфигурация `disable` и добавление в `.gitignore`. Тестирование на реальном iPhone — обязательное условие приёмки каждой фазы.

---

### Pitfall 6: Vercel-специфичные грабли (заголовки, scope, кэш SW-файла)

**What goes wrong:**
Несколько независимых проблем, каждая — отдельная ловушка:

**6а. SW-файл сам закэшировался на Vercel CDN** — `public/sw.js` отдаётся с `Cache-Control: public, max-age=31536000, immutable` (стандартная политика Vercel для статических файлов в `public/`). Браузер не перепроверяет SW год. После деплоя новой версии кода агенты получают старый SW ещё долго.

**6б. Scope SW ограничен папкой расположения файла** — если `sw.js` случайно окажется не в корне (например, попытка положить в `app/` или `pages/`), браузер выдаёт ошибку `ServiceWorker scope must be within the path of the script`. Каталог живёт по пути `/catalog/<UUID>/...` — если SW не в корне `/`, он не перехватывает запросы к каталогу.

**6в. `manifest.json` отдаётся без правильного Content-Type** — браузер игнорирует манифест PWA или показывает ошибку в DevTools. Особенно на iOS.

**Why it happens:**
Vercel применяет `immutable` к файлам в `public/` по умолчанию. Разработчик не добавляет кастомные заголовки для `sw.js`. Scope указывается неверно или не указывается вовсе.

**How to avoid:**
В `next.config.mjs` (или `vercel.json`) добавить явные заголовки для SW-файла:
```javascript
// next.config.mjs headers section
async headers() {
  return [
    {
      source: '/sw.js',
      headers: [
        { key: 'Cache-Control', value: 'public, max-age=0, must-revalidate' },
        { key: 'Service-Worker-Allowed', value: '/' },
      ],
    },
    {
      source: '/manifest.json',
      headers: [
        { key: 'Content-Type', value: 'application/manifest+json' },
      ],
    },
  ];
}
```
`Service-Worker-Allowed: /` разрешает SW контролировать весь origin, даже если `sw.js` физически в корне `public/`, а каталог по пути `/catalog/<UUID>/`.

При использовании `app/manifest.ts` (Next.js built-in) Content-Type выставляется автоматически — предпочтительный вариант.

**Warning signs:**
- После деплоя новой версии у агентов всё равно старый UI через 2–3 дня (признак SW с `immutable` кэшем)
- В DevTools Application → Service Workers: статус показывает версию недельной давности
- SW не перехватывает запросы к `/catalog/...` — ошибка scope в консоли
- `manifest.json` в вкладке Manifest DevTools показывает ошибку парсинга

**Phase to address:**
Фаза 1 (базовый SW) — заголовки и scope конфигурируются сразу при регистрации SW.

---

### Pitfall 7: Кнопка «Отправить заказ» работает офлайн и молча ничего не делает

**What goes wrong:**
Пользователь набрал корзину офлайн, нажимает «Отправить заказ». Код выполняет `window.open("https://t.me/ZhukOleh?text=...")`. На Android Chrome в офлайн это открывает Telegram с заранее сформированным текстом (Telegram сам offline-способен). На iOS Safari в standalone PWA — поведение непредсказуемо: `window.open()` может быть заблокирован как popup, либо открывается с ошибкой сети, либо не открывается вообще без обратной связи. Агент думает, что заказ отправлен — но он нет. Клиент не получает заказ, агент не знает об этом.

**Второй сценарий:** разработчик добавляет Background Sync для «отложенной отправки заказа» — чтобы заказ ушёл, когда появится сеть. Background Sync не поддерживается на iOS до iOS 16.4+. На Android поддерживается, но браузер может не выполнить синк если приложение долго не открывалось. Реализация Background Sync добавляет значительную сложность (очередь в IndexedDB, обработка ошибок, дедупликация) ради функции, которая работает непредсказуемо.

**Why it happens:**
Telegram deep-link (`window.open`) кажется надёжным — «всегда работал в онлайн». Разработчик не думает об офлайн-состоянии для кнопки отправки. Background Sync кажется элегантным решением, но переоценивается в плане поддержки iOS.

**How to avoid:**
1. **Деактивировать кнопку «Отправить заказ» в офлайн** с явным объяснением:
```typescript
// В cart/page.tsx
const isOnline = useOnlineStatus(); // navigator.onLine + событие offline/online

<button
  disabled={!isOnline}
  title={!isOnline ? "Подключитесь к сети для отправки заказа" : undefined}
  onClick={handleSendOrder}
>
  {isOnline ? "Отправить заказ" : "Нет сети — заказ недоступен"}
</button>
```
2. Корзина продолжает работать офлайн — добавление, редактирование, просмотр.
3. Добавить текстовое примечание на странице корзины: «Заказ формируется здесь. Для отправки нужна сеть».
4. **Не реализовывать Background Sync** в v1.3 — не работает надёжно на iOS, добавляет сложность без гарантии результата.

**Warning signs:**
- Кнопка «Отправить заказ» активна и кликабельна в офлайн-состоянии
- `window.open()` вызывается без проверки `navigator.onLine`
- В коде есть Background Sync регистрация без проверки поддержки iOS

**Phase to address:**
Фаза 2 (синхронизация данных) или отдельная задача в рамках «Офлайн UX» — проверка `navigator.onLine` в компоненте корзины.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| `skipWaiting: true` глобально | Обновления применяются «сами» | Смешанные версии JS-чанков, `ChunkLoadError`, белый экран у части агентов | Never — использовать только управляемый `postMessage SKIP_WAITING` |
| CacheFirst для `/api/products` | Быстрый ответ из кэша | Агент никогда не получает новые цены при наличии сети | Never — только NetworkFirst с таймаутом |
| Precache всех фото при установке | «Всё офлайн с первого открытия» | Взрывает квоту iOS (50 МБ), долгая установка, случайные QuotaExceededError | Never — CacheFirst on-demand + maxEntries |
| SW включён в dev-режиме | Тест в `npm run dev` | «Почему правки не применяются?» — часы потерянного времени | Never в разработке; только `npm run build && start` |
| `public/sw.js` в git | Единый репозиторий | Конфликты при сборке, случайный деплой старого SW | Never — в `.gitignore` |
| Background Sync для отправки заказа | «Умная» отложенная отправка | iOS не поддерживает до 16.4+; сложность очереди, дедупликации; неочевидные сбои | Never в v1.3 — вместо этого явное отключение кнопки офлайн |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Cloudinary + SW | Добавить `res.cloudinary.com` в precache manifest | `runtimeCaching` только — CacheFirst при реальных запросах. Precache для внешних CDN невозможен (нет URL в момент сборки) |
| Google Sheets API (`/api/products`) | Не добавлять в runtimeCaching (SW не кэширует) | NetworkFirst с `networkTimeoutSeconds: 5` и ExpirationPlugin |
| Vercel free tier + SW | Рассчитывать на серверный кэш при офлайн | Vercel free tier не даёт надёжный edge cache; весь офлайн — только SW Cache + IndexedDB |
| Telegram deep-link + SW | Ожидать что SW «пробросит» window.open | SW не перехватывает `window.open()`; офлайн-блокировка кнопки — единственная защита |
| `next/image` + Cloudinary + SW | Думать что SW кэширует `/_next/image?url=...` | Next.js Image optimizer меняет URL фото при трансформации. SW должен кэшировать оригинальный URL Cloudinary ИЛИ `/_next/image` — нужно определиться с одним подходом. `/_next/image` с параметрами — разные URL для разных размеров |
| `force-dynamic` + SW | Считать что `force-dynamic` передаётся SW | SW не видит директив Next.js. Стратегию для `/api/products` надо задавать явно в `sw.ts` |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Sync всех 850 фото при каждом обновлении каталога | Обновление занимает 3–10 мин, трафик 50+ МБ ежедневно | Diff по `imageUrl`: качать только URL, которых не было в предыдущем JSON | С первого дня если не внедрён diff |
| SW перехватывает все запросы включая Google Sheets API | Тихие ошибки, кэшированные 500-ответы от Sheets | Явный allowlist в `runtimeCaching` — только `/api/products`, `/catalog/*`, `res.cloudinary.com` | При любом сбое Google Sheets если кэшируется ошибочный ответ |
| IndexedDB чтение в главном потоке (синхронно через `localforage` старой версии) | UI фризится при старте на слабых телефонах | `idb` (Promise-based) + `useEffect` — не блокирует рендер | На Android бюджетных телефонах с медленным NAND |
| Регистрация SW внутри `useEffect` каждый рендер | Множественные перерегистрации, лишние update-check запросы | Регистрировать один раз через Serwist `register()` в `layout.tsx`, не в компонентах | При любом рефакторинге компонентов |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Кэширование ответа `/api/products` без валидации UUID | Теоретически: ответ с данными каталога доступен через SW Cache без UUID в URL | SW кэширует только `fetch`-запросы от страниц, уже прошедших проверку UUID на сервере. Прямой доступ к SW Cache требует DevTools или атаки на устройство. Риск минимален для данной модели угроз |
| `CATALOG_SECRET` в `start_url` манифеста | UUID попадает в `manifest.json` → виден в HTTP-ответе | UUID в манифесте неизбежен (без него установка ведёт на заглушку). Митигация: UUID уже не является секретом на устройстве агента; основная угроза — утечка через git, а не через манифест |
| SW кэширует 401/403 ответы от Google Sheets | Если ключ истёк — SW отдаёт кэшированный ошибочный ответ как «данные» | В `NetworkFirst` стратегии добавить `CacheableResponsePlugin({ statuses: [200] })` — кэшировать только успешные ответы |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Нет индикатора офлайн-режима | Агент не понимает почему фото не грузятся или кнопка не работает; думает «сайт сломался» | Цветная полоска или бейдж «Офлайн» в шапке при `navigator.onLine === false` |
| iOS: нет подсказки «как установить» | iOS-агент не знает про Share → Add to Home Screen; продолжает работать в браузере без офлайн-функции | Кастомный bottom-sheet с иконкой Share и стрелкой «нажми сюда» — показать один раз после 3-го посещения |
| Промпт установки сразу при первом посещении | Агент ещё не понял что это за приложение — игнорирует или отклоняет | Показать через `localStorage`-флаг: только после первого успешного просмотра каталога |
| «Обновить» во время показа клиенту меняет цены | Агент смотрит каталог с клиентом — цены меняются на глазах | «Обновить сейчас / Позже?» промпт, а не авто-обновление; применять после завершения показа |
| Пустой экран вместо «нет данных» | Агент смотрит на пустой каталог без объяснения | Явный empty-state: «Нет данных офлайн. Обновите при наличии сети» + кнопка «Попробовать» |
| Кнопка отправки заказа просто не реагирует офлайн | Агент нажимает несколько раз, думает «сломалось», злится | Кнопка задизейблена + tooltip «Для отправки нужна сеть» |

---

## "Looks Done But Isn't" Checklist

- [ ] **SW зарегистрирован:** Проверить DevTools Application → Service Workers → статус `activated`. Мало того что файл существует — нужно убедиться что регистрация прошла без ошибок.
- [ ] **Кэш фото работает на iOS:** Тест на реальном iPhone в Safari: просмотреть 20+ товаров → включить режим самолёта → открыть те же товары — фото должны быть.
- [ ] **Данные каталога в IndexedDB:** DevTools → Application → IndexedDB → `catalog-products` store — должен содержать Product[].
- [ ] **Установка на home screen iOS:** Тест на реальном iPhone: Share → Add to Home Screen → открыть иконку → убедиться что открывается в standalone режиме без адресной строки.
- [ ] **Android install prompt:** На Android Chrome после посещения каталога должен появиться баннер «Добавить на экран» или кнопка в интерфейсе.
- [ ] **Свежесть данных при обновлении:** После изменения прайса на сервере + нажатия «Обновить каталог» → список должен отражать новые данные без перезагрузки страницы.
- [ ] **SW-файл не кэшируется Vercel:** Проверить заголовок `Cache-Control` для `/sw.js` в Network tab: должен быть `max-age=0, must-revalidate`, не `immutable`.
- [ ] **Отправка заказа заблокирована офлайн:** Включить режим самолёта → открыть корзину → кнопка «Отправить» должна быть неактивна с объяснением.
- [ ] **Пустой кэш при первом открытии:** Открыть в режиме инкогнито в офлайн — должен появиться экран «Нет данных», а не пустой список.
- [ ] **`navigator.storage.persist()` вызван:** В `Application → Storage` DevTools → `Storage Persistence` должно показывать `persisted: true` после первой синхронизации (хотя iOS может отказать).

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Quota exceeded, часть фото не закэшировалась | MEDIUM | Уменьшить `maxEntries` в ExpirationPlugin → удалить старый `image-cache` через DevTools → повторная прокрутка каталога |
| Агент застрял на старой версии SW | LOW | Инструкция: «Закройте все вкладки приложения и откройте заново» — новый waiting SW активируется |
| SW кэшировал устаревший API-ответ навсегда | MEDIUM | Изменить `cacheName` в `api-cache` → при следующем деплое старый кэш игнорируется и создаётся новый |
| iOS очистил весь кэш (7-day eviction) | LOW | Агент открывает приложение при сети → повторная синхронизация |
| `sw.js` задеплоен с `immutable` кэшем | HIGH | Добавить заголовок `must-revalidate` в конфиге → дождаться истечения TTL (или сообщить агентам очистить кэш браузера) |
| Background Sync потерял заказ (если был реализован) | HIGH | Не реализовывать Background Sync; вместо этого — блокировка кнопки офлайн. Нет Background Sync → нет этого риска |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Quota exceeded при precache фото | Фаза 1: SW + manifest | Тест на реальном iPhone: прокрутить каталог, проверить Cache Storage < 40 МБ |
| 7-day iOS eviction | Фаза 1: `persist()` + Фаза 2: проверка данных при старте | Проверить `navigator.storage.persisted()` возвращает `true` (iOS) / протестировать после 7 дней |
| Устаревший SW после деплоя | Фаза 1: `skipWaiting: false` + Фаза 3: баннер обновления | Сделать деплой → убедиться что новый SW в `waiting` → баннер виден в UI |
| Стало устаревшим API в кэше | Фаза 2: NetworkFirst для `/api/products` | Обновить прайс → открыть приложение онлайн → данные обновились без ручного refresh |
| SW в dev-режиме ломает разработку | Фаза 1: `disable: development` + `.gitignore` | Запустить `npm run dev` → DevTools не показывает активного SW |
| Vercel кэширует `sw.js` с immutable | Фаза 1: заголовки в `next.config.mjs` | Проверить Network tab заголовок `/sw.js`: `max-age=0, must-revalidate` |
| Молчащий сбой отправки заказа офлайн | Фаза 2 или 3: `navigator.onLine` в корзине | Включить авиарежим → кнопка задизейблена + пояснение видно |
| Тест только на эмуляторе | Каждая фаза: приёмка на реальном iPhone | Чеклист: установка, offline фото, standalone режим — только физическое устройство |

---

## Sources

- [WebKit: Updates to Storage Policy (iOS 17+)](https://webkit.org/blog/14403/updates-to-storage-policy/) — официальная политика квот iOS, eviction, `navigator.storage.persist()` — HIGH confidence
- [web.dev: Service Worker Update Lifecycle](https://web.dev/learn/pwa/update/) — skipWaiting риски, safe update pattern — HIGH confidence
- [MDN: Offline and background operation (PWA)](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Offline_and_background_operation) — Background Sync поддержка платформ — HIGH confidence
- [Vercel: Cache-Control headers documentation](https://vercel.com/docs/caching/cache-control-headers) — приоритеты заголовков, Function override — HIGH confidence
- [Vite PWA: Vercel deployment guide](https://vite-pwa-org.netlify.app/deployment/vercel) — sw.js `must-revalidate`, Content-Type манифеста — MEDIUM confidence
- [magicbell.com: PWA iOS Limitations 2026](https://www.magicbell.com/blog/pwa-ios-limitations-safari-support-complete-guide) — 50 МБ лимит Cache API, beforeinstallprompt, 7-day eviction — MEDIUM confidence
- [love2dev.com: Cache Storage Limits](https://love2dev.com/blog/what-is-the-service-worker-cache-storage-limit/) — квоты по платформам — MEDIUM confidence
- [Apple Developer Forums: Safari iOS PWA Data Persistence](https://developer.apple.com/forums/thread/710157) — реальные случаи eviction — MEDIUM confidence
- [searchengineland.com: What Safari's 7-day cap means for PWA developers](https://searchengineland.com/what-safaris-7-day-cap-on-script-writeable-storage-means-for-pwa-developers-332519) — детали 7-day policy — MEDIUM confidence
- [web.dev: Tools and debug PWA](https://web.dev/learn/pwa/tools-and-debug) — real device vs emulator, iOS testing — HIGH confidence
- [GitHub: Serwist Next.js getting started](https://serwist.pages.dev/docs/next/getting-started) — конфигурация disable, precache — HIGH confidence

---

*Pitfalls research for: Offline PWA поверх Next.js/Vercel B2B-каталога (веха v1.3)*
*Researched: 2026-06-12*
