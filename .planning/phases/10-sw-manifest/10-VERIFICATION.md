---
phase: 10-sw-manifest
verified: 2026-06-12T14:00:00Z
status: human_needed
score: 8/9
overrides_applied: 0
human_verification:
  - test: "Открыть продакшн-сборку в Chrome или Firefox, зайти на секретный URL каталога, убедиться что в адресной строке появляется иконка установки (или меню → «Установить приложение»), установить и запустить — приложение открывается без адресной строки браузера, сразу на каталоге по секретной ссылке"
    expected: "Standalone-запуск без адресной строки; под иконкой на домашнем экране — «Вкусный Дом»; иконка синяя с «ВД»"
    why_human: "Физический жест установки PWA и проверка standalone-режима нельзя автоматизировать без реального браузера/устройства; DevTools → Application → Manifest уже проверено координатором (APPROVED), но сам установочный поток требует ручного действия"
---

# Phase 10: SW + Manifest — Отчёт верификации

**Цель этапа:** Подключить фундамент PWA вехи v1.3 — активный service worker (через @serwist/next) и устанавливаемое приложение (Web App Manifest + иконки). Требование PWA-01.
**Верифицировано:** 2026-06-12
**Статус:** HUMAN_NEEDED (8/9 автоматически подтверждены; 1 поведение требует ручной проверки установки)
**Повторная верификация:** Нет — первичная

---

## Достижение цели

### Наблюдаемые истины

| # | Истина | Статус | Доказательство |
|---|--------|--------|----------------|
| 1 | Service worker регистрируется и переходит в статус `activated and running` после `npm run build && npm start` | ✓ VERIFIED | Подтверждено координатором в продакшн-сборке: `navigator.serviceWorker` статус `activated`, scope `http://localhost:3000/`, scriptURL `/sw.js` (Firefox) |
| 2 | Ответ для `/sw.js` содержит заголовок `Cache-Control: max-age=0, must-revalidate` | ✓ VERIFIED | curl-проверка: заголовок присутствует; `next.config.mjs` содержит `headers()` с точным значением |
| 3 | В режиме `npm run dev` service worker отключён | ✓ VERIFIED | `next.config.mjs`: `disable: process.env.NODE_ENV === "development"` |
| 4 | Сгенерированные `public/sw.js` и `public/swe-worker*.js` не попадают в git | ✓ VERIFIED | `.gitignore` строки 44-46: блок `# PWA: сгенерированные service worker файлы` + `public/sw.js` + `public/swe-worker*.js` |
| 5 | `app/sw.ts` содержит каркас стратегий NetworkFirst (`/api/products`) и CacheFirst (Cloudinary) | ✓ VERIFIED | Файл читается: matcher `/\/api\/products/` (без `^`, исправлено в коммите cd8f0b5), CacheFirst + ExpirationPlugin maxEntries:450 для `res.cloudinary.com` |
| 6 | Каталог устанавливается на домашний экран и запускается в standalone-режиме без адресной строки | ? UNCERTAIN | Все технические предпосылки выполнены (SW активен + manifest корректен), но физический жест установки не проверялся автоматически |
| 7 | Под иконкой отображается короткое имя «Вкусный Дом», иконка синяя с монограммой «ВД» | ✓ VERIFIED | `app/manifest.ts`: `short_name: "Вкусный Дом"`; 4 иконки PNG в `public/icons/` (размеры 2375–8187 байт, ненулевые); координатором подтверждены HTTP 200 для всех 4 |
| 8 | Splash-заставка и полоска статуса используют фирменные цвета: `theme_color #2563eb`, `background_color #ffffff` | ✓ VERIFIED | `app/manifest.ts`: оба поля присутствуют; `app/layout.tsx`: `viewport.themeColor: "#2563eb"` |
| 9 | Тап по иконке открывает каталог по секретной ссылке без хардкода секрета | ✓ VERIFIED | `app/manifest.ts`: `start_url: \`/catalog/${process.env.CATALOG_SECRET ?? ""}\`` — секрет из env; подтверждено координатором в `/manifest.webmanifest` |

**Счёт:** 8/9 истин подтверждены автоматически; 1 требует человека

---

## Необходимые артефакты

| Артефакт | Ожидается | Статус | Детали |
|----------|-----------|--------|--------|
| `app/sw.ts` | SW с precache + NetworkFirst/CacheFirst, skipWaiting:false | ✓ VERIFIED | Файл 81 строка, все ключевые конструкции присутствуют |
| `next.config.mjs` | withSerwist + disable:dev + заголовки /sw.js | ✓ VERIFIED | withSerwist, swSrc: "app/sw.ts", disable:dev, headers() |
| `.gitignore` | Игнор public/sw.js и public/swe-worker*.js | ✓ VERIFIED | Блок добавлен в конце файла |
| `package.json` | @serwist/next + idb в deps, serwist в devDeps | ✓ VERIFIED | deps: @serwist/next ^9.5.11, idb ^8.0.3; devDeps: serwist ^9.5.11 |
| `app/manifest.ts` | MetadataRoute.Manifest, standalone, start_url из env | ✓ VERIFIED | Все обязательные поля присутствуют |
| `public/icons/icon-192x192.png` | Иконка 192×192 | ✓ VERIFIED | Существует, 2879 байт |
| `public/icons/icon-512x512.png` | Иконка 512×512 | ✓ VERIFIED | Существует, 8187 байт |
| `public/icons/icon-512x512-maskable.png` | Maskable-иконка | ✓ VERIFIED | Существует, 5777 байт |
| `public/icons/apple-touch-icon.png` | iOS 180×180 без прозрачности | ✓ VERIFIED | Существует, 2375 байт; координатором подтверждён colorType RGB (без альфа) |
| `app/layout.tsx` | appleWebApp, icons, viewport.themeColor | ✓ VERIFIED | Все три блока присутствуют |

---

## Проверка ключевых связей

| От | До | Через | Статус | Детали |
|----|----|-------|--------|--------|
| `next.config.mjs` | `app/sw.ts` | `swSrc: "app/sw.ts"` | ✓ WIRED | Точное значение найдено в файле |
| `next.config.mjs` | `/sw.js` | `headers()` Cache-Control max-age=0 | ✓ WIRED | `value: "max-age=0, must-revalidate"` найдено |
| `app/manifest.ts` | `CATALOG_SECRET` | `process.env` в start_url | ✓ WIRED | `process.env.CATALOG_SECRET` в строке start_url |
| `app/layout.tsx` | `apple-touch-icon.png` | `metadata.icons.apple` | ✓ WIRED | `url: "/icons/apple-touch-icon.png"` найдено |

---

## Трассировка требований

| Требование | Источник плана | Описание | Статус | Доказательство |
|------------|----------------|----------|--------|----------------|
| PWA-01 | 10-01-PLAN.md, 10-02-PLAN.md | Каталог устанавливается на домашний экран и запускается как приложение, без браузерной строки | ✓ SATISFIED (технически) / ? РУЧНАЯ ПРОВЕРКА (поведение) | SW активен + manifest корректен + иконки есть; сам установочный поток требует человека |

---

## Поведенческие spot-checks

| Поведение | Команда | Результат | Статус |
|-----------|---------|-----------|--------|
| npm run build завершается с кодом 0 | `npm run build` | Код 0 (подтверждено координатором, sw.js ~42 КБ) | ✓ PASS |
| package.json содержит все PWA-зависимости | `node -e "..."` | @serwist/next: ^9.5.11, idb: ^8.0.3, serwist: ^9.5.11 | ✓ PASS |
| .gitignore содержит public/sw.js | grep | строки 45-46 файла | ✓ PASS |
| Все 4 иконки существуют и непустые | `fs.statSync` | 2375–8187 байт каждая | ✓ PASS |
| SW отключён в dev | code review | `disable: process.env.NODE_ENV === "development"` | ✓ PASS |
| SW активен в прод-сборке | координатор | `activated`, scope `/`, scriptURL `/sw.js` | ✓ PASS |
| /sw.js имеет корректные HTTP-заголовки | curl | `Cache-Control: max-age=0, must-revalidate` + `Service-Worker-Allowed: /` | ✓ PASS |
| /manifest.webmanifest корректен | координатор | `application/manifest+json`, все поля, включая maskable | ✓ PASS |

---

## Антипаттерны

| Файл | Строка | Паттерн | Серьёзность | Влияние |
|------|--------|---------|-------------|---------|
| `app/sw.ts` (исходная версия) | ~49 | matcher `/^\/api\/products/` с якорем `^` — regex никогда не совпадал бы (Serwist проверяет по `url.href`, начинающемуся с `https://`) | 🛑 BLOCKER (исправлен) | Стратегия NetworkFirst для API товаров не работала бы в кэше; исправлено в коммите cd8f0b5, код-ревью 10-REVIEW.md |

> Критический баг с якорем `^` был обнаружен в 10-REVIEW.md и устранён до верификации. Текущий `app/sw.ts` содержит исправленный matcher `/\/api\/products/` (без `^`).

Нарушений типа TBD / FIXME / XXX без ссылок на задачи — не обнаружено.

---

## Ручная верификация

### 1. Установка PWA и standalone-режим

**Тест:** Открыть продакшн-сборку (`npm run build && npm start`) в Chrome или Firefox на десктопе. Зайти на секретный URL каталога. В адресной строке должна появиться иконка установки (или меню ⋮ → «Установить приложение»). Установить. Запустить установленное приложение.

**Ожидается:**
- Приложение открывается без адресной строки браузера (standalone-режим)
- Сразу открывается каталог по секретной ссылке (`/catalog/<secret>`)
- Под иконкой на домашнем экране / в списке приложений — название «Вкусный Дом»
- Иконка — синий квадрат с белой монограммой «ВД»

**Желательно дополнительно:** проверить на реальном Android (Chrome) — жест «Поделиться → На экран Домой» или баннер установки.

**Почему человек:** Физический жест установки PWA и запуск в standalone-режиме нельзя автоматизировать без реального браузера/устройства в интерактивном режиме. DevTools → Application → Manifest уже подтверждён координатором (APPROVED), но сам установочный поток требует ручного действия.

---

## Итог

Все 9 технических предпосылок реализованы и подтверждены в кодовой базе:
- @serwist/next интегрирован, SW активен в продакшн-сборке, отключён в dev
- Критическая ошибка (matcher `^`) обнаружена code-review и устранена
- Web App Manifest корректен, все поля заполнены, секрет из env
- 4 иконки присутствуют, apple-touch-icon без альфа-канала, maskable с safe-zone
- layout.tsx содержит все PWA/iOS-метаданные

Единственный пункт, требующий человека — финальный ручной шаг «установить и запустить в standalone» на реальном браузере/устройстве. Это ожидаемо для PWA-этапа и не является признаком незавершённости кода.

---

_Верифицировано: 2026-06-12_
_Верификатор: Claude (gsd-verifier)_
