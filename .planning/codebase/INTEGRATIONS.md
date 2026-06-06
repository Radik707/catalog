# External Integrations

**Analysis Date:** 2026-06-06

## APIs & External Services

**Google Sheets (основное хранилище данных):**
- Назначение: единственный источник данных каталога (товары, цены, остатки, фото, бейджи)
- SDK (чтение, Next.js): встроенный `fetch` к REST `https://sheets.googleapis.com/v4/spreadsheets/{ID}/values/{range}?key={API_KEY}`
  - Файл: `lib/sheets.ts` — ISR-кэш 5 минут (`next: { revalidate: 300 }`)
  - Файл: `bot/services/products.ts` — in-memory кэш 15 минут
- SDK (запись, Python): `gspread ^6.0` + `google-auth ^2.20`
  - Файл: `scripts/upload.py` — полная перезапись листа «Товары» (очистка + batch update)
  - Файл: `scripts/sheet_tool.py` — backup/rollback через копирование листов
- Auth (чтение): публичный API key (`GOOGLE_API_KEY`) — только чтение
- Auth (запись): Service Account credentials.json (`GOOGLE_CREDENTIALS_PATH`)
- Scopes: `spreadsheets`, `drive`
- Листы: `Товары` (рабочий), `Товары_BACKUP` (до обновления), `Товары_NEW` (отложенная новая версия)
- Схема листа: Наименование | Цена | Остаток | Категория | Группа | Поставщик | Badge | ImageUrl | Description (колонки A–I)

**Cloudinary (CDN фото):**
- Назначение: хранение и раздача фото товаров (1093 файла: 318 в `akkond/`, 775 в `presenter/`)
- SDK: `cloudinary ^1.36` (Python, только загрузка) — файл `scripts/upload_photos.py`
- Чтение: прямые HTTPS-URL в поле ImageUrl Google Sheet; Next.js отдаёт через `next/image` с remotePattern `res.cloudinary.com`
- Auth: `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`
- Формат ключей в `scripts/photo_overrides.json`: `"akkond/500.jpg"` или `"presenter/447.webp"` (папка/файл)
- Конфиг Next.js: `next.config.mjs` → `remotePatterns: [{ hostname: "res.cloudinary.com" }]`

**Telegram Bot API (клиентский бот — grammY):**
- Назначение: B2B-консультант для клиентов (поиск товаров, корзина, отправка заказа)
- SDK: `grammy ^1.41.1` (TypeScript, webhook mode)
- Webhook endpoint: `app/api/bot/route.ts` (Vercel serverless POST)
- Верификация: заголовок `x-telegram-bot-api-secret-token` == `TELEGRAM_WEBHOOK_SECRET`
- Auth: `TELEGRAM_BOT_TOKEN`
- Отправка заказа владельцу: `ctx.api.sendMessage(OWNER_CHAT_ID, orderText)` — файл `bot/handlers/order.ts`
- Команды: `/start`, `/cart`, `/order`; свободный текст → Gemini AI

**Telegram Bot API (admin-бот — notify + long polling):**
- Назначение: уведомления администратора об итогах обновления каталога; кнопки решения при проблемах
- Реализация: raw `requests` (Python, без фреймворка)
- Файлы: `scripts/notify_tg.py` (отправка) + `admin_bot/admin_bot.py` (long polling getUpdates)
- Режим: long polling (не webhook); работает как постоянный systemd-сервис на сервере
- Auth: `TELEGRAM_TOKEN`, `OWNER_CHAT_ID`
- SOCKS5-прокси: `TG_PROXY=socks5h://127.0.0.1:1080` (обход блокировки Telegram в РФ); пакет `PySocks ^1.7`
- Inline-кнопки: `keep` (оставить прошлую), `apply` (применить новую), `files` (получить .xlsx)

**Google Gemini (AI-консультант бота):**
- Назначение: обработка свободных текстовых запросов клиентов через function calling
- SDK: `@google/generative-ai ^0.24.1` (TypeScript)
- Модель: `gemini-2.0-flash`
- Auth: `GEMINI_API_KEY`
- Function calling: `search_products`, `add_to_cart`, `remove_from_cart`, `show_cart`, + другие
- Файлы: `bot/ai/consultant.ts`, `bot/ai/tools.ts`, `bot/ai/system-prompt.ts`
- Fallback при ошибке: сообщение «Извините, произошла ошибка. Попробуйте позже...»

**Anthropic Claude Vision (только для скриптов):**
- Назначение: извлечение фото товаров из PDF-каталогов поставщиков + генерация описаний
- SDK: `anthropic ^0.40` (Python)
- Auth: `ANTHROPIC_API_KEY`
- Файл: `scripts/extract_photos.py`
- Одноразовый скрипт (не постоянный сервис)

## Data Storage

**Databases:**
- Тип: Google Sheets (не реляционная БД; электронная таблица как хранилище)
  - Connection: `GOOGLE_SHEETS_ID` + `GOOGLE_API_KEY` (чтение) / `credentials.json` (запись)
  - Client: `gspread` (Python) / `fetch` REST (TypeScript)
- Тип: Vercel KV (Redis-совместимый, managed)
  - Connection: `KV_REST_API_URL`, `KV_REST_API_TOKEN`
  - Client: `@vercel/kv ^3.0.0`
  - Использование: корзина Telegram-бота, ключ `cart:{telegram_user_id}`, TTL 24 часа

**File Storage:**
- Cloudinary — фото товаров (только CDN, загрузка через Python-скрипты)
- Локальная файловая система сервера Daniella:
  - `uploader/price/` — входящие .xlsx прайсы (временная очередь)
  - `uploader/last_batch/` (`LAST_BATCH_DIR`) — архив последней партии прайсов
- Локальная файловая система (Windows, разработка):
  - `C:\price\` — Excel-прайсы поставщиков
  - `photos/akkond/` — 318 исходных фото Акконд
  - `pdf/` — PDF-каталоги поставщиков

**Caching:**
- Next.js ISR: 5 минут (`revalidate: 300`) в `lib/sheets.ts` и `app/api/products/route.ts`
- In-memory (module-level): 15 минут в `bot/services/products.ts` (переменные `cachedProducts`, `cacheTimestamp`)

## Authentication & Identity

**Auth Provider — Next.js каталог:**
- Подход: UUID-секрет в URL (`CATALOG_SECRET`); проверяется на сервере в route handler
- Нет сессий, нет куки — доступ только тем, у кого ссылка

**Auth Provider — Flask веб-загрузчик:**
- Подход: секретный сегмент в URL (`APP_SECRET`); функция `check(token)` → `abort(404)` при несовпадении
- Файл: `uploader/app.py`; опционально — Basic-Auth на уровне nginx

**Auth Provider — Telegram-боты:**
- Клиентский бот: webhook secret header `TELEGRAM_WEBHOOK_SECRET`
- Admin-бот: фильтр по `OWNER_CHAT_ID` — игнорирует все сообщения не от владельца

## Monitoring & Observability

**Error Tracking:**
- Не подключен (ни Sentry, ни аналоги)

**Logs:**
- Next.js: стандартный `console.error/log` → Vercel Logs
- Flask/gunicorn: стандартный Python `logging` (`%(asctime)s [%(levelname)s]`) → journald (`journalctl -u catalog-uploader -f`)
- admin_bot.py: аналогичный Python logging → journald (`journalctl -u catalog-admin-bot -f`)

## CI/CD & Deployment

**Frontend (Next.js):**
- Hosting: Vercel (бесплатный план)
- Репозиторий: GitHub `Radik707/catalog`
- Деплой: автоматически при `git push origin main`
- Ручная пересборка: `Remove-Item -Recurse -Force .next; npm run build`

**Backend (Python uploader + admin bot) — сервер Daniella:**
- Serving: gunicorn (`-w 1`) за nginx (TLS)
- Process management: systemd
  - `catalog-uploader.service` — Flask `uploader/app.py`; `EnvironmentFile=uploader/.env`; `WorkingDirectory=/srv/catalog/uploader`
  - `catalog-admin-bot.service` — `admin_bot/admin_bot.py`; `EnvironmentFile=uploader/.env`; `WorkingDirectory=/opt/apps/catalog/admin_bot`
- Обновление кода: `git pull` → `sudo systemctl restart catalog-uploader catalog-admin-bot`

**nginx (TLS reverse proxy):**
- Протоколы: только HTTPS 443 (TLS сертификат `fullchain.pem`/`privkey.pem`)
- `client_max_body_size 50m` — для загрузки .xlsx
- Проксирует на `http://127.0.0.1:8000` (gunicorn)

## Environment Configuration

**Required env vars (Vercel / Next.js):**
- `GOOGLE_SHEETS_ID` — ID Google-таблицы
- `GOOGLE_API_KEY` — публичный ключ Google Sheets API
- `CATALOG_SECRET` — UUID секретной ссылки каталога
- `TELEGRAM_BOT_TOKEN` — токен клиентского Telegram-бота
- `TELEGRAM_WEBHOOK_SECRET` — секрет для webhook
- `OWNER_CHAT_ID` — Telegram ID владельца
- `GEMINI_API_KEY` — ключ Google Gemini
- `KV_REST_API_URL`, `KV_REST_API_TOKEN` — Vercel KV

**Required env vars (сервер Daniella — `uploader/.env`):**
- `APP_SECRET` — секрет загрузчика
- `TELEGRAM_TOKEN` — токен admin-бота
- `OWNER_CHAT_ID` — Telegram ID владельца
- `TG_PROXY` — SOCKS5-прокси (напр. `socks5h://127.0.0.1:1080`)
- `LAST_BATCH_DIR` — путь к архиву прайсов
- `INCOMING_DIR`, `UPLOAD_SCRIPT`, `PYTHON_BIN`, `UPLOAD_TIMEOUT`
- `WARN_RATIO` — порог предупреждения (по умолчанию `0.5`)

**Required env vars (Python ETL — `.env` в корне):**
- `GOOGLE_SHEETS_ID`, `GOOGLE_CREDENTIALS_PATH`
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`
- `ANTHROPIC_API_KEY`

**Secrets location:**
- Vercel: Dashboard → Environment Variables (не в git)
- Сервер: `uploader/.env` и `scripts/credentials.json` (только на сервере, в `.gitignore`)
- Локально (Windows): `.env` и `.env.local` в корне проекта (в `.gitignore`)

## Webhooks & Callbacks

**Incoming (Vercel принимает):**
- `POST /api/bot` — Telegram Bot API webhook updates (клиентский бот)
  - Верификация: заголовок `x-telegram-bot-api-secret-token`
  - Файл: `app/api/bot/route.ts`
  - Настройка URL: `scripts/setup-webhook.ts` (запуск: `npm run setup-webhook`)

**Outgoing (приложение вызывает):**
- Telegram Bot API: `sendMessage`, `sendDocument`, `editMessageText`, `answerCallbackQuery`
  - Клиентский бот (grammY): через `ctx.api.*` внутри webhook handler
  - Admin-бот (Python): через `requests.post` к `https://api.telegram.org/bot{TOKEN}/...` через SOCKS5-прокси
  - notify_tg.py: через `requests.post` при завершении upload.py

---

*Integration audit: 2026-06-06*
