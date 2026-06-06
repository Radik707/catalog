# Technology Stack

**Analysis Date:** 2026-06-06

## Languages

**Primary:**
- TypeScript 5.x — Next.js frontend (app/, components/, lib/), Telegram bot (bot/), API routes (app/api/)
- Python 3.13 — всё, что связано с данными: ETL-скрипты (scripts/), веб-загрузчик (uploader/), Telegram admin-бот (admin_bot/)

**Secondary:**
- JavaScript — встроенный vanilla JS в HTML-странице Flask-загрузчика (uploader/app.py)

## Runtime

**Environment:**
- Node.js 22.x — для Next.js (frontend + serverless functions)
- Python 3.13 — для scripts/, uploader/, admin_bot/ (рекомендован venv)

**Package Manager:**
- npm — lockfile `package-lock.json` присутствует
- pip — lockfile отсутствует; зависимости в `scripts/requirements.txt` и `uploader/requirements.txt`

## Frameworks

**Core (Frontend):**
- Next.js ^14.2.0 (App Router) — SPA-каталог, ISR-кэш, serverless API routes
- React ^18.3.0 + React DOM ^18.3.0 — UI-компоненты
- Tailwind CSS ^3.4.0 — стилизация, PostCSS + Autoprefixer

**Telegram Bot (TypeScript/Webhook):**
- grammY ^1.41.1 — Bot framework (webhook mode через `webhookCallback`)
- @google/generative-ai ^0.24.1 — Gemini 2.0 Flash API (function calling)
- @vercel/kv ^3.0.0 — Redis-совместимое хранилище корзины (Vercel KV)

**Веб-загрузчик прайсов (Python):**
- Flask ^3.0 — минимальный HTTP-сервер с секретным URL
- gunicorn ^21.2 — WSGI-сервер для продакшн (один воркер `-w 1`)

**Скрипты ETL (Python):**
- openpyxl ^3.1 — чтение Excel-прайсов поставщиков
- gspread ^6.0 + google-auth ^2.20/2.28 — запись/чтение Google Sheets (Service Account)
- cloudinary ^1.36 — загрузка фото в CDN
- anthropic ^0.40 — Claude Vision API (извлечение фото из PDF)
- PyMuPDF ^1.23 — рендеринг страниц PDF в изображения
- transliterate ^1.10 — транслитерация кириллицы для имён файлов
- requests ^2.31 — HTTP-клиент для Telegram Bot API (admin_bot, notify_tg)
- PySocks ^1.7 — SOCKS5-прокси для обхода блокировки Telegram в РФ

**Build/Dev:**
- tsx ^4.21.0 — выполнение TypeScript напрямую (scripts/setup-webhook.ts)
- TypeScript ^5.0.0 — компиляция (noEmit, strict mode)
- postcss ^8.4.0, autoprefixer ^10.4.0 — PostCSS pipeline для Tailwind

## Key Dependencies

**Critical:**
- `next ^14.2.0` — полный фреймворк фронтенда; App Router, ISR, serverless functions
- `grammy ^1.41.1` — единственный Telegram bot framework; удаление ломает весь бот
- `gspread` — единственный источник данных каталога; без него сайт возвращает пустой список
- `@vercel/kv` — хранилище корзины бота; без него корзина не работает

**Infrastructure:**
- `@anthropic-ai/sdk ^0.82.0` — Claude Vision (extract_photos.py использует Python-SDK напрямую, не этот пакет; JS-пакет присутствует в package.json, но не используется в текущем коде)
- `cloudinary ^1.36` — CDN для 1093 фото товаров; смена провайдера требует правки next.config.mjs и всех URL

## Configuration

**Environment (Next.js — `.env.local`):**
- `GOOGLE_SHEETS_ID` — ID Google Таблицы (читает `lib/sheets.ts`)
- `GOOGLE_API_KEY` — публичный API-ключ для чтения Sheets (только чтение)
- `CATALOG_SECRET` — UUID-сегмент секретной ссылки каталога
- `TELEGRAM_BOT_TOKEN` — токен клиентского Telegram-бота (grammY)
- `TELEGRAM_WEBHOOK_SECRET` — секрет для верификации webhook-запросов от Telegram
- `OWNER_CHAT_ID` — Telegram ID владельца (отправка заказов)
- `GEMINI_API_KEY` — ключ Google Gemini Flash API
- `KV_REST_API_URL`, `KV_REST_API_TOKEN` — Vercel KV (Redis)

**Environment (Python ETL — `.env` в корне проекта):**
- `GOOGLE_SHEETS_ID`, `GOOGLE_CREDENTIALS_PATH` — запись через Service Account
- `EXCEL_DIR` — путь к папке с Excel-прайсами (по умолчанию `C:\price`)
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`
- `ANTHROPIC_API_KEY` — для extract_photos.py (Claude Vision)

**Environment (Flask uploader + admin bot — `uploader/.env`):**
- `APP_SECRET` — секретный сегмент URL загрузчика
- `INCOMING_DIR`, `UPLOAD_SCRIPT`, `PYTHON_BIN`, `UPLOAD_TIMEOUT`
- `LAST_BATCH_DIR`, `WARN_RATIO`
- `TELEGRAM_TOKEN`, `OWNER_CHAT_ID`, `TG_PROXY`

**Build:**
- `next.config.mjs` — разрешены remote images только с `res.cloudinary.com`
- `tsconfig.json` — strict, noEmit, `@/*` alias на корень; папка `scripts/` исключена из компиляции
- `tailwind.config.ts` — стандартная конфигурация
- `postcss.config.mjs` — Tailwind + Autoprefixer

## Platform Requirements

**Development (Windows):**
- Node.js 22+, npm
- Python 3.13+ с venv
- PowerShell: разделитель команд `;` (не `&&`)
- Удалять кэш Next.js перед сборкой: `Remove-Item -Recurse -Force .next`

**Production (два окружения):**
- **Vercel** (бесплатный план) — Next.js frontend + serverless API routes + grammY webhook
  - Vercel KV для корзины бота
- **VPS «Daniella»** (Linux) — Flask-загрузчик и Python admin-бот
  - gunicorn + systemd (`catalog-uploader.service`, `catalog-admin-bot.service`)
  - nginx с TLS (HTTPS proxy до `127.0.0.1:8000`)
  - SOCKS5-прокси на `127.0.0.1:1080` (для Telegram через `TG_PROXY`)
  - Код: `/srv/catalog/` или `/opt/apps/catalog/`; venv: `.venv/`

---

*Stack analysis: 2026-06-06*
