<!-- refreshed: 2026-06-06 -->
# Architecture

**Analysis Date:** 2026-06-06

## System Overview

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                        ОПЕРАТОР / ПОСТАВЩИК                              │
│              C:\price\ (Excel-прайсы 3 файла в день)                     │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │ .xlsx upload (drag-and-drop или curl)
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│              Flask Web Uploader  (сервер «daniella»)                     │
│              uploader/app.py  — HTTPS/<APP_SECRET>                       │
│  POST /upload → POST /update → subprocess(upload.py)                     │
│  POST /rollback → subprocess(sheet_tool.py rollback)                     │
└──────────┬───────────────────────────────────────┬───────────────────────┘
           │ subprocess                             │ subprocess
           ▼                                       ▼
┌──────────────────────┐             ┌─────────────────────────────────────┐
│  scripts/upload.py   │             │  scripts/sheet_tool.py              │
│  Excel → Google Sheet│             │  backup / rollback / stash_new      │
│  (openpyxl + gspread)│             │  Товары ↔ Товары_BACKUP             │
└──────────┬───────────┘             └─────────────────────────────────────┘
           │ gspread write                     │ gspread write
           ▼                                   │
┌──────────────────────────────────────────────▼───────────────────────────┐
│                         Google Sheet «Товары»                            │
│   Наименование | Цена | Остаток | Категория | Группа | Поставщик |       │
│   Badge | ImageUrl | Description                          (A:I)          │
│   + «Товары_BACKUP», «Товары_NEW» (резервные листы)                      │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │ Sheets REST API (revalidate 300s)
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                 Next.js 14 App  (Vercel)                                  │
│  app/api/products/route.ts → lib/sheets.ts → Google Sheets API          │
│  app/catalog/[secret]/page.tsx  (ISR revalidate=300)                     │
│  components/CatalogView.tsx  (client: filter, search, lightbox)          │
│  components/ProductCard.tsx  (flip, grid/list/presentation)              │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │ Telegram deep link (корзина → заказ)
                                  ▼
                           КЛИЕНТ В TELEGRAM
                           (владелец магазина)

══════ БОКОВОЙ КАНАЛ АДМИНИСТРАТОРА ══════

┌──────────────────────────┐    notify_tg.py (subprocess)    ┌────────────┐
│  uploader/app.py         │ ───────────────────────────────► │  Telegram  │
│  (итог обновления)       │    plain / decision / error      │  (бот)     │
└──────────────────────────┘                                  └─────┬──────┘
                                                                    │ callback_query (inline-кнопки)
                                                             long polling
                                                                    ▼
                                                        ┌────────────────────┐
                                                        │  admin_bot/        │
                                                        │  admin_bot.py      │
                                                        │  keep / apply /    │
                                                        │  files             │
                                                        │  → sheet_tool.py   │
                                                        └────────────────────┘
```

## Component Responsibilities

| Компонент | Ответственность | Файл |
|-----------|-----------------|------|
| Flask Uploader | Приём .xlsx от оператора, запуск upload.py, откат | `uploader/app.py` |
| upload.py | Парсинг Excel (2 формата), маппинг категорий/фото/badge, запись в Sheet | `scripts/upload.py` |
| sheet_tool.py | Backup/rollback листа «Товары», stash/apply «Товары_NEW» | `scripts/sheet_tool.py` |
| notify_tg.py | CLI-утилита отправки Telegram-уведомления (plain / decision / error) | `scripts/notify_tg.py` |
| admin_bot.py | Long-polling бот: обработка inline-кнопок keep/apply/files | `admin_bot/admin_bot.py` |
| Sheets API client | Чтение листа «Товары» A2:I, кэш ISR 5 мин | `lib/sheets.ts` |
| Products API route | GET /api/products → JSON массив Product[] | `app/api/products/route.ts` |
| Catalog page | Server component: проверка UUID, фильтрация hit/new, рендер | `app/catalog/[secret]/page.tsx` |
| Catalog layout | Sticky header, NavTabs, CartIcon, SettingsButton | `app/catalog/[secret]/layout.tsx` |
| CatalogView | Client: фильтр по группе, поиск, lightbox, управление видом | `components/CatalogView.tsx` |
| ProductCard | Client: flip-карточка, grid/list/presentation режимы, бейдж | `components/ProductCard.tsx` |
| CartProvider | React Context поверх useCart (localStorage) | `components/CartProvider.tsx` |
| CatalogSettings | React Context: viewMode/gridPreset/showPhotos/showPrices | `components/CatalogSettings.tsx` |
| Cart page | Управление корзиной, формирование Telegram deep link | `app/catalog/[secret]/cart/page.tsx` |
| Telegram Bot (grammY) | Customer-facing bot: каталог, корзина, ИИ-консультант (в разработке) | `bot/index.ts` |

## Pattern Overview

**Overall:** Многоуровневый pipeline данных + Server-first Next.js с thin client layer

**Key Characteristics:**
- Данные движутся в одну сторону: Excel → Google Sheet → Next.js (нет обратной записи из UI)
- Google Sheet — единственный источник истины для каталога; обновляется только Python-скриптами
- Next.js использует ISR (revalidate=300): страница рендерится на сервере, кэш сбрасывается каждые 5 мин
- Секретность через UUID в URL (`CATALOG_SECRET`), не через session/auth
- Admin-канал полностью асинхронен: notify_tg.py → admin_bot.py через Telegram inline-кнопки

## Layers

**Data Pipeline (Python, сервер «daniella»):**
- Purpose: Трансформация прайсов поставщиков в структурированный каталог
- Location: `scripts/`, `uploader/`, `admin_bot/`
- Contains: парсинг Excel, маппинг категорий/фото/badge, gspread-клиент, Flask web, Telegram-уведомления
- Depends on: Google Sheets API (gspread), Cloudinary (photo_urls.json), Telegram Bot API
- Used by: веб-загрузчик запускает скрипты как subprocess

**Google Sheet (внешний хранилище):**
- Purpose: Общее хранилище между Python-pipeline и Next.js
- Location: Google Sheets (ID в `GOOGLE_SHEETS_ID`)
- Contains: лист «Товары» (A:I), «Товары_BACKUP», «Товары_NEW»
- Зависимостей нет: обе стороны работают с ним напрямую через API

**Next.js API layer (Vercel, serverless):**
- Purpose: Прокси между Google Sheets и клиентом + авторизация по UUID
- Location: `app/api/products/route.ts`, `lib/sheets.ts`
- Contains: один GET endpoint, Sheets-клиент
- Depends on: Google Sheets API (через HTTP, ключ `GOOGLE_API_KEY`)
- Used by: серверные компоненты страницы каталога (прямой импорт `getProducts()`)

**Next.js UI layer (Client Components):**
- Purpose: Интерактивность — фильтры, поиск, flip-карточки, корзина, настройки
- Location: `components/`, `app/catalog/[secret]/cart/`
- Contains: React Context (корзина, настройки), client-side filter/search, localStorage persist
- Depends on: Product[] props от серверного компонента

## Data Flow

### Основной путь обновления каталога (ежедневный)

1. Оператор открывает `https://<host>/<APP_SECRET>` (`uploader/app.py`)
2. Загружает .xlsx → `POST /<token>/upload` → файлы в `uploader/price/`
3. Нажимает «Обновить» → `POST /<token>/update`
4. `app.py` вызывает `sheet_tool.py backup` (резервная копия листа «Товары» → «Товары_BACKUP»)
5. `app.py` вызывает `upload.py --path uploader/price/` (`scripts/upload.py`)
6. `upload.py` парсит .xlsx (функции `parse_excel_file` / `parse_new_format`), применяет `category_map.json`, `badges.json`, `photo_overrides.json`, `photo_urls.json`
7. `upload.py` пишет строки в лист «Товары» через gspread (Service Account)
8. `app.py` проверяет count: если < 50% прежнего → stash_new + rollback + notify decision
9. `app.py` вызывает `notify_tg.py plain/decision/error` → Telegram-сообщение владельцу
10. Vercel ISR кэш обновляется при следующем запросе (≤5 мин)

### Просмотр каталога (клиент)

1. Клиент открывает `/catalog/<UUID>` → Next.js Server Component (`app/catalog/[secret]/page.tsx`)
2. Server Component проверяет `params.secret === process.env.CATALOG_SECRET`; при несовпадении — `notFound()`
3. Вызывается `getProducts()` (`lib/sheets.ts`) → GET `https://sheets.googleapis.com/.../Товары!A2:I`
4. Фильтрация hit/new на сервере → `<CatalogView products={...} />`
5. `CatalogView` (client) применяет клиентскую фильтрацию по группе и поиску (stock > 1)
6. `ProductCard` рендерит карточки в трёх режимах (list / grid / presentation)

### Корзина и заказ

1. `AddToCartButton` → `useCart` hook → `CartProvider` context → `localStorage` (ключ `catalog-cart`)
2. `CartIcon` читает `totalItems` из `CartProvider`
3. Страница корзины `app/catalog/[secret]/cart/page.tsx` формирует текст заказа
4. Кнопка → `window.open("https://t.me/ZhukOleh?text=...")` (Telegram deep link, username захардкожен)

### Admin side-channel (откат/принятие решения)

1. `notify_tg.py decision "<text>"` → `sendMessage` с inline keyboard → `admin_bot.py` слушает long polling
2. Владелец нажимает [Оставить прошлую] → callback `keep` → `sheet_tool.py drop_new`
3. Владелец нажимает [Всё равно применить] → callback `apply` → `sheet_tool.py apply_new` (Товары_NEW → Товары)
4. Владелец нажимает [Показать файлы] → callback `files` → `sendDocument` .xlsx из `uploader/last_batch/`

**State Management:**
- Серверное состояние: Google Sheet (единственный источник истины)
- Клиентское состояние корзины: `localStorage` через `useCart` + `CartProvider` (React Context)
- Настройки отображения: `localStorage` через `CatalogSettings` (React Context)
- Состояния «подозрительная версия»: лист «Товары_NEW» в Google Sheet (временный)

## Key Abstractions

**Product (тип данных):**
- Purpose: Единый тип товара от API до UI
- Examples: `lib/types.ts`
- Pattern: `interface Product { id, name, price, stock, category, group, supplier, badge?, imageUrl?, description? }`

**getProducts() (data access):**
- Purpose: Единственная точка чтения данных из Google Sheet
- Examples: `lib/sheets.ts`
- Pattern: `fetch(sheetsUrl, { next: { revalidate: 300 } })` → mapping rows → `Product[]`

**CatalogSettings (presentation context):**
- Purpose: Хранит viewMode / gridPreset / showPhotos / showPrices, персистент в localStorage
- Examples: `components/CatalogSettings.tsx`
- Pattern: React Context + localStorage read/write в сеттерах

**PresentationSizes (адаптивные размеры):**
- Purpose: Масштабирование шрифтов и высоты фото под плотность сетки презентации
- Examples: `components/ProductCard.tsx`, `components/CatalogSettings.tsx`
- Pattern: `PRESENTATION_PRESETS: Record<GridPreset, { label, cols, sizes: PresentationSizes }>`

**секретный UUID (авторизация):**
- Purpose: Защита каталога без логина — UUID в URL
- Examples: `app/catalog/[secret]/page.tsx` (строка 14), `app/catalog/[secret]/layout.tsx`
- Pattern: сравнение `params.secret !== process.env.CATALOG_SECRET` → `notFound()` на сервере

## Entry Points

**Catalog UI:**
- Location: `app/catalog/[secret]/page.tsx`
- Triggers: HTTP GET от браузера клиента
- Responsibilities: проверка UUID, загрузка продуктов, фильтрация hit/new, рендер CatalogView

**Products API:**
- Location: `app/api/products/route.ts`
- Triggers: HTTP GET (только для внешних потребителей; каталог-страница вызывает lib/sheets.ts напрямую)
- Responsibilities: обертка `getProducts()` → JSON

**Telegram Bot Webhook:**
- Location: `app/api/bot/route.ts` → `bot/index.ts`
- Triggers: POST от Telegram (webhook), проверка `x-telegram-bot-api-secret-token`
- Responsibilities: маршрутизация обновлений к обработчикам grammY

**Flask Uploader:**
- Location: `uploader/app.py` (systemd: `catalog-uploader.service`)
- Triggers: HTTP от оператора (браузер или curl)
- Responsibilities: приём файлов, backup, запуск upload.py, rollback, уведомления

**Admin Bot:**
- Location: `admin_bot/admin_bot.py` (systemd: `catalog-admin-bot.service`)
- Triggers: long polling Telegram `getUpdates`
- Responsibilities: обработка callback_query от inline-кнопок уведомлений

## Architectural Constraints

- **Однопоточность uploader:** gunicorn запускается с `-w 1` (один воркер), чтобы upload.py не запускался параллельно
- **Proxy для Telegram:** `admin_bot.py` и `notify_tg.py` ходят к Telegram через `TG_PROXY` (SOCKS); Google Sheets — всегда напрямую (admin_bot явно снимает proxy-переменные перед запуском sheet_tool)
- **force-dynamic в route.ts:** `export const dynamic = 'force-dynamic'` обязателен, иначе Vercel кэширует ответ навсегда
- **Нет reverse flow:** Next.js не пишет в Google Sheet; только читает
- **UUID в URL:** единственный механизм авторизации для каталога; `app/page.tsx` возвращает 404
- **Cloudinary domainallow:** `res.cloudinary.com` добавлен в `next.config.mjs` `remotePatterns` — без этого `next/image` блокирует

## Anti-Patterns

### Захардкоженный username Telegram

**What happens:** `TELEGRAM_USERNAME = "ZhukOleh"` задан прямо в `app/catalog/[secret]/cart/page.tsx` строка 5
**Why it's wrong:** При смене username или владельца требуется деплой; строка попадает в публичный код git
**Do this instead:** Вынести в env-переменную (`NEXT_PUBLIC_TELEGRAM_USERNAME`) и читать через `process.env`

### Маппинг группы PRODUCT_OVERRIDES захардкожен в коде

**What happens:** `PRODUCT_OVERRIDES` и `PRODUCT_CONTAINS_OVERRIDES` — Python-словари прямо в `scripts/upload.py` строки 295-319
**Why it's wrong:** Добавление нового переопределения требует правки кода и деплоя/перезапуска скрипта
**Do this instead:** Вынести в отдельный `product_overrides.json` (по аналогии с `category_map.json`)

### GROUP_ORDER захардкожен в CatalogView

**What happens:** `GROUP_ORDER` — массив из 12 строк в `components/CatalogView.tsx` строка 19
**Why it's wrong:** Добавление новой группы требует правки компонента и редеплоя Vercel
**Do this instead:** Пробрасывать с сервера или вынести в конфигурационный файл

## Error Handling

**Strategy:** Fail-safe с автоматическим откатом; уведомления асинхронны

**Patterns:**
- `upload.py` → ошибка разбора/записи: uploader откатывает «Товары» из BACKUP и уведомляет владельца
- Подозрительно мало товаров (< WARN_RATIO): stash_new → rollback → decision-сообщение владельцу с кнопками
- `lib/sheets.ts`: при ошибке API возвращает `[]` (пустой массив), не бросает исключение
- `notify_tg.py`: при отсутствии TELEGRAM_TOKEN/OWNER_CHAT_ID выходит с SKIP, не ошибка
- `app/api/bot/route.ts`: всегда возвращает HTTP 200 Telegram (даже при внутренней ошибке)

## Cross-Cutting Concerns

**Logging:** Python-скрипты — `logging.basicConfig` (stdout, формат `HH:MM:SS [LEVEL] msg`); Next.js — `console.error` в lib/sheets.ts
**Validation:** Авторизация по UUID — только на сервере в server component; Flask — `abort(404)` при несовпадении token
**Authentication:** UUID в URL (`CATALOG_SECRET` / `APP_SECRET`); Telegram-бот — проверка `OWNER_CHAT_ID` и `x-telegram-bot-api-secret-token`

---

*Architecture analysis: 2026-06-06*
