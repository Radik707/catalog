# Phase 10: Фундамент SW и Manifest - Context

**Gathered:** 2026-06-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Подключить service worker (SW) и Web App Manifest так, чтобы каталог стал устанавливаемым PWA-приложением: SW активен и не падает, приложение ставится на домашний экран с иконкой и именем, запускается в standalone-режиме (без адресной строки браузера).

**Закрывает требование:** PWA-01.

**В границах этапа:** инфраструктура SW (`@serwist/next`), manifest, иконки, бренд-метаданные (имя/цвет/заставка), конфигурация Vercel-заголовков, отключение SW в dev, `.gitignore`.

**Вне границ этапа (другие этапы вехи):** офлайн-кэш товаров в IndexedDB (этап 11), кэш фото и умный diff (этап 13), офлайн-индикаторы и корзина (этап 12), install-промпт/инструкция (этап 14). На этом этапе SW лишь активируется и кэширует app-shell — он ещё НЕ хранит данные каталога и фото.

</domain>

<decisions>
## Implementation Decisions

### Идентичность приложения (имя)
- **D-01:** Полное имя (`name` в manifest) — **«Каталог Вкусный Дом»**.
- **D-02:** Короткое имя (`short_name`, под иконкой на домашнем экране) — **«Вкусный Дом»** (слово «Каталог» отбрасываем — под иконкой влезает ~12 символов).

### Иконка приложения
- **D-03:** Логотипа у проекта нет. Иконку генерируем сами: **синий квадрат `#2563eb` + белый шрифт-вензель «ВД»**, со скруглением.
- **D-04:** Форматы/размеры: PNG **192×192** и **512×512**, плюс **maskable**-вариант 512×512 (с safe-zone ~80% для Android adaptive icons). Также `apple-touch-icon` для iOS (180×180, без прозрачности, фон синий).
- **D-05:** Иконка — временная, легко заменяемая. Если владелец позднее даст реальный логотип — подменить файлы без правки кода.

### Бренд-цвета (тема и заставка)
- **D-06:** `theme_color` (цвет полоски статуса в standalone) — **`#2563eb`** (синий `bg-blue-600`, совпадает с шапкой каталога — `app/catalog/[secret]/layout.tsx:28`).
- **D-07:** `background_color` (фон splash-заставки при запуске) — **`#ffffff`** (белый, как фон карточек каталога — запуск выглядит чисто и быстро).

### Поведение при запуске
- **D-08:** `display: standalone` — без адресной строки браузера.
- **D-09:** `start_url` — секретный путь каталога с `CATALOG_SECRET`; тап по иконке открывает каталог напрямую (главная каталога, текущее поведение по умолчанию). Секрет НЕ хардкодить — брать из переменной окружения, как в существующем коде.
- **D-10:** `orientation` — portrait (агент работает с телефоном вертикально); не блокировать жёстко, если это усложняет — `any` приемлем.

### Технические решения (зафиксированы исследованием v1.3 — НЕ переобсуждать)
- **D-11:** Библиотека — **`@serwist/next` ^9** (+ `serwist` dev). next-pwa/@ducanh2912 устарели, App Router не поддерживают.
- **D-12:** **`skipWaiting: false`** (Serwist default) — обновление SW только по явному согласию; форсированный skipWaiting при активной вкладке → `ChunkLoadError` / белый экран у агента.
- **D-13:** **`disable: process.env.NODE_ENV === 'development'`** — SW отключён в `npm run dev`; PWA-поведение проверяется только через `npm run build && npm start`.
- **D-14:** Заголовок для `/sw.js`: **`Cache-Control: max-age=0, must-revalidate`** + `Service-Worker-Allowed: /` в `next.config.mjs` — иначе Vercel «залипнет» на старом SW (immutable) после деплоя.
- **D-15:** `app/manifest.ts` — встроенный Next.js-механизм (Content-Type выставляется автоматически, внешняя либа не нужна).
- **D-16:** Стратегии кэширования в `app/sw.ts` (NetworkFirst для `/api/products`, CacheFirst для Cloudinary с `maxEntries`) **закладываются** в SW на этом этапе как каркас, но их офлайн-эффект проверяется на этапах 11/13. На этапе 10 проверяем только: SW `activated`, app-shell precache, заголовки, standalone.

### Claude's Discretion
Владелец делегировал технические и оформительские детали («сделай сам, ко мне только за важными правками»). Под мою ответственность: точная реализация генерации иконок, набор размеров/линков в `<head>`, структура `app/sw.ts`, формулировки manifest-полей, какие именно ассеты прекэшировать. Решения D-01…D-10 приняты мной по делегированию и открыты для правки владельцем.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Веха v1.3 — исследование и требования
- `.planning/research/SUMMARY.md` — ⭐ главный источник: рекомендованный стек (`@serwist/next`, `idb`), все 7 критических ловушек, архитектура, раздел «Этап 1: Фундамент (SW + Manifest)». Технические решения D-11…D-16 взяты отсюда.
- `.planning/REQUIREMENTS.md` §PWA — требование PWA-01 (установка на домашний экран, standalone).
- `.planning/ROADMAP.md` → «Phase 10: Фундамент SW и Manifest» — цель и 5 критериев успех. Критерии №2 (Cache-Control), №4 (dev disable), №5 (.gitignore) — приёмочные.

### Официальная документация (из SUMMARY.md, для планировщика)
- `@serwist/next` getting-started: https://serwist.pages.dev/docs/next/getting-started
- Next.js PWA guide: https://nextjs.org/docs/app/guides/progressive-web-apps
- Vercel Cache-Control headers: https://vercel.com/docs/caching/cache-control-headers

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/catalog/[secret]/layout.tsx:28` — шапка `bg-blue-600` (`#2563eb`): источник фирменного цвета для `theme_color`.
- Паттерн `CATALOG_SECRET` в переменных окружения (`.env.local`, проверка на сервере) — переиспользовать для `start_url` в `app/manifest.ts`, не хардкодить секрет.
- `next.config.mjs` — уже есть (минимальный, только `images.remotePatterns` для Cloudinary). Сюда оборачиваем `withSerwist` и добавляем `headers()`.

### Established Patterns
- Стек: Next.js 14 App Router + TypeScript + Tailwind. Зависимостей PWA пока нет (`package.json` чистый от serwist/idb) — этап ставит их впервые.
- `public/` директории НЕТ — её нужно создать (туда лягут сгенерированные `sw.js`, иконки; `public/sw.js` и `public/swe-worker*.js` → в `.gitignore`).
- Иконок/логотипа/favicon в проекте нет (`app/` без `icon.*`/`apple-icon.*`) — всё создаётся с нуля.

### Integration Points
- `app/layout.tsx` (корневой) — сюда добавляются `<link>`-и иконок и PWA-метаданные (`apple-mobile-web-app-*`), регистрация SW через Serwist.
- `next.config.mjs` — точка подключения SW-плагина и заголовков Vercel.
- `app/manifest.ts` — новый файл, отдаёт Web App Manifest.

</code_context>

<specifics>
## Specific Ideas

- Иконка-монограмма «ВД» в фирменном синем — как временная узнаваемая иконка до появления настоящего логотипа.
- Единый фирменный синий `#2563eb` сквозь весь бренд (шапка → theme_color → фон иконки → apple-touch-icon).
- Запуск приложения = мгновенный вход в каталог по секретной ссылке, без лишних экранов.

</specifics>

<deferred>
## Deferred Ideas

- **Install-промпт / iOS-инструкция «Поделиться → На экран Домой»** — это этап 14 (PWA-02), не сейчас. На этапе 10 установка происходит только через штатное меню браузера.
- **Реальный логотип бренда** — если владелец захочет заменить временную монограмму на дизайнерский логотип, это правка ассетов (не требует отдельного этапа); зафиксировано как возможная будущая «важная правка».
- **Кастомные splash-заставки под размеры iOS-экранов** — iOS генерирует splash из `background_color` + иконки; точечные `apple-touch-startup-image` под каждый размер экрана — необязательная полировка, не входит в MVP.

</deferred>

---

*Phase: 10-sw-manifest*
*Context gathered: 2026-06-12*
