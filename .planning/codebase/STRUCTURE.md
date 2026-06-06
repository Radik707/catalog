# Codebase Structure

**Analysis Date:** 2026-06-06

## Directory Layout

```
C:\catalog\                         # корень проекта (Next.js + Python)
├── app\                            # Next.js App Router
│   ├── catalog\[secret]\           # защищённый каталог (UUID в URL)
│   │   ├── page.tsx                # Server Component: каталог (ISR 5 мин)
│   │   ├── layout.tsx              # макет с шапкой: NavTabs, CartIcon, Settings
│   │   └── cart\page.tsx           # страница корзины + Telegram deep link
│   ├── api\
│   │   ├── products\route.ts       # GET /api/products → Product[] JSON
│   │   └── bot\route.ts            # POST /api/bot → Telegram webhook (grammY)
│   ├── page.tsx                    # корневой маршрут → notFound() (заглушка)
│   ├── layout.tsx                  # корневой layout: CartProvider, metadata
│   └── globals.css                 # глобальные стили (Tailwind base)
├── components\                     # React UI-компоненты (все PascalCase)
│   ├── ProductCard.tsx             # flip-карточка: grid/list/presentation
│   ├── CatalogView.tsx             # фильтр + поиск + lightbox + сетка
│   ├── CategoryFilter.tsx          # горизонтальный скролл фильтра по группам
│   ├── SearchBar.tsx               # поле поиска с счётчиком результатов
│   ├── AddToCartButton.tsx         # кнопка «+» / счётчик в корзине
│   ├── CartIcon.tsx                # иконка корзины с бейджем в шапке
│   ├── CartProvider.tsx            # React Context корзины (над useCart)
│   ├── CatalogSettings.tsx         # React Context настроек + PRESENTATION_PRESETS
│   ├── SettingsButton.tsx          # кнопка-шестерёнка (открывает SettingsPanel)
│   ├── SettingsPanel.tsx           # выпадающая панель: выбор вида / пресета
│   ├── NavTabs.tsx                 # вкладки «Каталог / Хит / Новинка»
│   ├── TelegramButton.tsx          # плавающая кнопка «Написать в Telegram»
│   ├── Lightbox.tsx                # полноэкранный просмотрщик-галерея фото
│   └── ScrollToTop.tsx             # кнопка «наверх» (появляется после N строк)
├── lib\                            # серверные утилиты и типы
│   ├── types.ts                    # interface Product (id, name, price, ...)
│   ├── sheets.ts                   # getProducts() → Google Sheets API
│   ├── useCart.ts                  # useCart hook (localStorage)
│   └── packaging.ts                # getPackaging(group, name) → «за шт» / «за кг»
├── bot\                            # Telegram customer-facing bot (grammY, в разработке)
│   ├── index.ts                    # инициализация Bot, регистрация handlers
│   ├── handlers\
│   │   ├── start.ts                # /start, приветствие, меню
│   │   ├── catalog.ts              # навигация по категориям (inline-кнопки)
│   │   ├── cart.ts                 # просмотр и управление корзиной
│   │   └── order.ts                # оформление и отправка заказа
│   ├── ai\
│   │   ├── consultant.ts           # Gemini Flash: обработка свободного текста
│   │   ├── tools.ts                # function calling: search, add_to_cart и др.
│   │   └── system-prompt.ts        # системный промпт + динамические данные
│   └── services\
│       ├── products.ts             # товары из Google Sheet (кэш 15 мин)
│       ├── cart-store.ts           # корзина в Vercel KV (ключ cart:{user_id})
│       └── notify.ts               # отправка заказа владельцу
├── scripts\                        # Python data pipeline (запускается локально или на сервере)
│   ├── upload.py                   # ГЛАВНЫЙ: Excel → Google Sheet (парсинг + запись)
│   ├── sheet_tool.py               # backup / rollback / stash / apply листа «Товары»
│   ├── notify_tg.py                # CLI: отправить Telegram-уведомление (plain/decision/error)
│   ├── upload_photos.py            # загрузка фото → Cloudinary (--folder, --source)
│   ├── make_manual_sheet.py        # создание/дополнение photo_manual.xlsx (--append)
│   ├── apply_manual_sheet.py       # photo_manual.xlsx → photo_overrides.json
│   ├── extract_photos.py           # PDF → фото + photo_map.json (Claude Vision)
│   ├── fetch_web_photos.py         # поиск фото товаров в интернете
│   ├── apply_web_photos.py         # применение найденных веб-фото
│   ├── search_missing_photos.py    # поиск товаров без фото
│   ├── auto_match_photos.py        # автоматическое сопоставление фото
│   ├── make_photo_sheet.py         # утилита работы с photo sheet
│   ├── apply_photo_matching.py     # применение сопоставленных фото
│   ├── fix_photo_paths.py          # исправление путей в photo_overrides.json
│   ├── rename_photos.py            # переименование фото-файлов
│   ├── update.bat                  # Windows bat: запуск upload.py (ежедневное обновление)
│   ├── category_map.json           # 84 категории Excel → 11 групп UI
│   ├── badges.json                 # правила хит/новинка/акция (частичный поиск)
│   ├── photo_map.json              # автомаппинг: название → файл → описание (PDF extraction)
│   ├── photo_urls.json             # имя_файла → URL Cloudinary (1093 записи)
│   ├── photo_overrides.json        # «название товара» → «папка/файл» (889 ручных привязок)
│   ├── description_overrides.json  # ручные описания товаров
│   ├── requirements.txt            # Python зависимости pipeline
│   └── credentials.json            # ключ Service Account Google (НЕ в git)
├── uploader\                       # Flask web uploader (запускается на сервере «daniella»)
│   ├── app.py                      # Flask: upload/update/rollback endpoints + HTML-UI
│   ├── requirements.txt            # Flask, gunicorn, gspread, requests, PySocks
│   ├── .env.example                # шаблон переменных (APP_SECRET, INCOMING_DIR, ...)
│   └── README.md                   # инструкция по деплою (gunicorn + nginx + systemd)
├── admin_bot\                      # Telegram-бот администратора (long polling, сервер «daniella»)
│   ├── admin_bot.py                # Bot: callback keep/apply/files → sheet_tool.py
│   └── README.md                   # инструкция по деплою (systemd)
├── photos\                         # локальные фото поставщика Акконд (318 файлов, не в git)
│   └── akkond\
├── pdf\                            # PDF-каталоги поставщиков (не в git)
├── practice\                       # экспериментальный мусор (hello.html)
├── app\globals.css                 # (см. выше)
├── next.config.mjs                 # remotePatterns: res.cloudinary.com
├── tailwind.config.ts              # конфигурация Tailwind
├── tsconfig.json                   # TypeScript (paths alias @/ → ./)
├── package.json                    # Next.js 14, grammy, @google/generative-ai, @vercel/kv
├── .env.local                      # Next.js env (GOOGLE_SHEETS_ID, GOOGLE_API_KEY, CATALOG_SECRET, ...)
├── .env.local.example              # шаблон env для Vercel
├── photo_manual.xlsx               # ручная таблица привязки фото (не в git при открытом Excel)
└── .gitignore                      # photos/, pdf/, .env*, credentials.json, ~$*.xlsx
```

## Directory Purposes

**`app/`:**
- Purpose: Next.js App Router — страницы, layout-ы, API routes
- Contains: Server Components, Client Components, API route handlers
- Key files: `app/catalog/[secret]/page.tsx`, `app/api/products/route.ts`, `app/layout.tsx`

**`components/`:**
- Purpose: Переиспользуемые React-компоненты UI каталога
- Contains: клиентские компоненты с `"use client"`, React Context providers
- Key files: `CatalogView.tsx`, `ProductCard.tsx`, `CartProvider.tsx`, `CatalogSettings.tsx`

**`lib/`:**
- Purpose: Серверные утилиты, типы данных, клиентские хуки
- Contains: TypeScript типы, Google Sheets клиент, useCart hook, логика фасовки
- Key files: `types.ts`, `sheets.ts`, `useCart.ts`, `packaging.ts`

**`bot/`:**
- Purpose: Customer-facing Telegram bot (grammY, webhook через `/api/bot`)
- Contains: handlers/, ai/, services/ — в разработке
- Key files: `bot/index.ts` (инициализация + handleUpdate)

**`scripts/`:**
- Purpose: Python data pipeline — парсинг Excel и запись в Google Sheet
- Contains: upload.py (главный), вспомогательные скрипты фото, JSON-конфиги
- Key files: `upload.py`, `sheet_tool.py`, `notify_tg.py`, `category_map.json`, `photo_overrides.json`

**`uploader/`:**
- Purpose: Flask web UI для операторов (загрузка .xlsx, запуск обновления)
- Contains: один файл `app.py` со всей логикой и встроенным HTML
- Key files: `app.py`, `.env.example`

**`admin_bot/`:**
- Purpose: Telegram-бот для администратора (принятие решений при проблемах обновления)
- Contains: один файл `admin_bot.py`, README с инструкцией по systemd
- Key files: `admin_bot.py`

## Key File Locations

**Entry Points:**
- `app/catalog/[secret]/page.tsx`: каталог клиента (Server Component, ISR)
- `app/api/products/route.ts`: REST API товаров (force-dynamic)
- `app/api/bot/route.ts`: Telegram webhook endpoint
- `uploader/app.py`: Flask uploader (запускается как systemd `catalog-uploader`)
- `admin_bot/admin_bot.py`: Admin bot (запускается как systemd `catalog-admin-bot`)

**Configuration:**
- `scripts/category_map.json`: маппинг 84 категорий Excel → 11 групп UI
- `scripts/badges.json`: правила простановки хит/новинка/акция
- `scripts/photo_overrides.json`: 889 ручных привязок «название → папка/файл»
- `scripts/photo_urls.json`: 1093 записи «файл → URL Cloudinary»
- `next.config.mjs`: разрешённые домены для next/image
- `.env.local`: переменные Next.js (GOOGLE_SHEETS_ID, GOOGLE_API_KEY, CATALOG_SECRET, ...)
- `uploader/.env`: переменные Flask + Python (APP_SECRET, TELEGRAM_TOKEN, TG_PROXY, ...)

**Core Logic:**
- `scripts/upload.py`: парсинг Excel 2 форматов, маппинг категорий, badge, фото, запись в Sheet
- `lib/sheets.ts`: единственная точка чтения Google Sheet в Next.js
- `lib/types.ts`: тип Product (контракт между backend и UI)
- `components/CatalogSettings.tsx`: PRESENTATION_PRESETS, viewMode context
- `lib/packaging.ts`: ~40 правил определения единицы фасовки

## Naming Conventions

**Файлы:**
- React компоненты: PascalCase.tsx (`ProductCard.tsx`, `CatalogView.tsx`)
- Next.js специальные: строчные (`page.tsx`, `layout.tsx`, `route.ts`, `globals.css`)
- Утилиты/хуки: camelCase.ts (`useCart.ts`, `sheets.ts`, `packaging.ts`)
- Python скрипты: snake_case.py (`upload.py`, `sheet_tool.py`, `notify_tg.py`)
- JSON конфиги: snake_case.json (`category_map.json`, `photo_overrides.json`)

**Компоненты:**
- Все компоненты именуются в PascalCase
- Providers имеют суффикс `Provider` (`CartProvider`, `CatalogSettingsProvider`)
- Кастомные хуки имеют префикс `use` (`useCart`, `useCatalogSettings`, `useCartContext`)

**Директории:**
- Next.js маршруты: строчные с дефисами по конвенции Next.js; динамические сегменты в `[brackets]`
- Python-модули: snake_case (`admin_bot/`, `uploader/`)

## Where to Add New Code

**Новая страница каталога:**
- Создать: `app/catalog/[secret]/<route>/page.tsx`
- Добавить в NavTabs: `components/NavTabs.tsx`
- Проверку UUID брать как образец из `app/catalog/[secret]/page.tsx` строка 14

**Новый UI компонент:**
- Implementation: `components/<ComponentName>.tsx`
- Если client-only: добавить `"use client"` в первой строке
- Если нужен context: создать Provider по образцу `components/CartProvider.tsx`

**Новый API endpoint:**
- Implementation: `app/api/<name>/route.ts`
- Добавить `export const dynamic = 'force-dynamic'` если нет кэширования
- Типы данных: `lib/types.ts`

**Новый Python-скрипт обработки данных:**
- Implementation: `scripts/<action_name>.py`
- Читать .env по образцу `scripts/sheet_tool.py` функция `load_env()`
- Зависимости добавить в `scripts/requirements.txt`

**Новые правила категоризации:**
- Новые группы товаров: `scripts/category_map.json`
- Переопределения конкретных товаров: `PRODUCT_OVERRIDES` в `scripts/upload.py` строки 295-313
- Порядок отображения групп: `GROUP_ORDER` в `components/CatalogView.tsx` строки 18-31

**Новые правила фасовки:**
- Implementation: `lib/packaging.ts` в функции `getPackaging()`

**Новые badge-правила:**
- `scripts/badges.json` — добавить подстроки в нужные разделы (новинка/хит/акция/исключения)

**Новый поставщик с фото:**
1. Загрузить фото в Cloudinary: `scripts/upload_photos.py --folder <name> --source <path>`
2. Создать привязки: `scripts/make_manual_sheet.py --append` → заполнить `photo_manual.xlsx`
3. Применить: `scripts/apply_manual_sheet.py` → обновляет `scripts/photo_overrides.json`
4. Запустить `scripts/upload.py` для записи в Sheet

## Special Directories

**`photos/`:**
- Purpose: локальные оригиналы фото для загрузки в Cloudinary
- Generated: вручную (PDF extraction или скачивание)
- Committed: Нет (в .gitignore)

**`pdf/`:**
- Purpose: PDF-каталоги поставщиков для `extract_photos.py`
- Generated: получаются от поставщиков
- Committed: Нет (в .gitignore)

**`uploader/price/`:**
- Purpose: временная папка входящих .xlsx на сервере «daniella»
- Generated: создаётся `uploader/app.py` автоматически
- Committed: Нет (рабочий каталог сервера)

**`uploader/last_batch/`:**
- Purpose: архив последней партии загруженных файлов (для проверки администратором через бота)
- Generated: `uploader/app.py` (`archive_incoming()`)
- Committed: Нет

**`.next/`:**
- Purpose: кэш сборки Next.js
- Generated: `npm run build`
- Committed: Нет
- ВАЖНО: удалять перед каждым деплоем после `upload.py`: `Remove-Item -Recurse -Force .next`

**`practice/`:**
- Purpose: экспериментальные файлы (не часть продукта)
- Generated: вручную
- Committed: Нет (рекомендуется добавить в .gitignore)

---

*Structure analysis: 2026-06-06*
