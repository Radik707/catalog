# Каталог торгового представителя
 
> Обновлено: 5 апреля 2026 | CLAUDE.md v4
 
## О проекте
Мобильный B2B-каталог товаров для владельцев магазинов.
Клиент открывает ссылку → видит товары с ценами, фото и наличием → набирает корзину → отправляет заказ в Telegram.
Данные из Excel поставщиков загружаются через Python-скрипт в Google Sheet, сайт читает оттуда.
 
## Стек
- **Сайт:** Next.js 14 (App Router) + Tailwind CSS + TypeScript
- **Данные:** Google Sheets API (только чтение)
- **Скрипт:** Python (openpyxl, gspread, python-dotenv, cloudinary)
- **Фото:** Cloudinary (папки akkond/ и presenter/, автосжатие WebP)
- **Корзина:** localStorage → deep link Telegram
- **Хостинг:** Vercel (бесплатный план)
- **Репозиторий:** GitHub Radik707/catalog
 
## Структура файлов
```
C:\catalog\
├── app\
│   ├── catalog\[secret]\         # Защищённый каталог (UUID в URL)
│   │   ├── page.tsx              # Главная каталога
│   │   ├── layout.tsx            # Макет с шапкой + навигация (Каталог/Хит/Новинка)
│   │   └── cart\page.tsx         # Страница корзины
│   ├── api\products\route.ts     # API: товары из Google Sheets (force-dynamic)
│   ├── page.tsx                  # Заглушка (404)
│   ├── globals.css
│   └── layout.tsx                # Корневой макет
├── components\
│   ├── AddToCartButton.tsx
│   ├── CartIcon.tsx
│   ├── CatalogView.tsx           # Переключатели: Список/Сетка, С фото/Без фото
│   ├── CategoryFilter.tsx
│   ├── ProductCard.tsx           # Карточка: фото + flip + бейдж + цена + корзина
│   ├── ScrollToTop.tsx           # Кнопка прокрутки вверх
│   └── SearchBar.tsx
├── lib\
│   ├── sheets.ts                 # Google Sheets API (A2:H)
│   └── types.ts                  # Product: badge?, imageUrl?, description?
├── scripts\
│   ├── upload.py                 # Excel → Google Sheet (+ badges + images + descriptions)
│   ├── extract_photos.py         # PDF → фото + photo_map.json (Claude Vision)
│   ├── upload_photos.py          # Фото → Cloudinary (--folder, --source)
│   ├── make_manual_sheet.py      # Создаёт/дописывает photo_manual.xlsx (--append)
│   ├── apply_manual_sheet.py     # photo_manual.xlsx → photo_overrides.json
│   ├── category_map.json         # 84 категории → 11 групп
│   ├── badges.json               # Хиты, новинки, акции (поиск частичный, регистронезависимый)
│   ├── photo_map.json            # Авто-маппинг из PDF: название → файл → описание
│   ├── photo_urls.json           # Файл → URL Cloudinary (1093 записи: 318 akkond + 775 presenter)
│   ├── photo_overrides.json      # Товар → "папка/файл" (889 привязок)
│   ├── description_overrides.json
│   ├── requirements.txt
│   └── credentials.json          # Ключ сервисного аккаунта (НЕ в Git!)
├── photos\
│   └── akkond\                   # Фото Акконд (318 файлов)
├── pdf\                          # PDF-каталоги поставщиков
├── .env                          # Python: API ключи, Cloudinary
├── .env.local                    # Next.js переменные
├── photo_manual.xlsx             # Ручная привязка фото (полные пути file:///)
└── .gitignore                    # photos/, pdf/, ~$*.xlsx, .env, credentials.json
```
 
## Данные
- 3 Excel-файла в день из C:\price\ (Ефимова, Лазуткина, Пелих)
- Google Sheet: Наименование | Цена | Остаток | Категория | Группа | Поставщик | Badge | ImageUrl
- 935 товаров, 853 с фото, 36 без фото
 
## Фото: две папки Cloudinary
- **akkond/** — 318 фото конфет Акконд
- **presenter/** — 775 фото остальных товаров
- В photo_overrides.json формат: "akkond/500.jpg" или "presenter/447.webp"
- Путь в photo_manual.xlsx определяет папку (/akkond/ в пути → akkond, иначе → presenter)
- Cloudinary домен добавлен в next.config.mjs (remotePatterns)
 
## UI каталога
- **Два режима:** Список и Сетка (по умолчанию Сетка с фото, сохраняется в localStorage)
- **Адаптивная сетка:** 2 колонки (мобильный) / 3 (планшет) / 4 (десктоп)
- **Карточка:** фото (object-contain, белый фон) → название (полное, 2-3 строки) → цена + корзина
- **Flip:** нажатие на карточку → описание + цена + корзина на обороте
- **Без фото:** карточки сжимаются до размера текста, сетка сохраняется
- **ScrollToTop:** появляется после 6 рядов (сетка) / 10 элементов (список), полупрозрачная
- **Навигация:** Каталог / Хит / Новинка в синей шапке (query ?filter=hit|new)
- **Бейджи:** новинка > хит > акция (приоритет), исключения в badges.json
- Фасовка под ценой (~40 правил: за шт/блок/кг/ящик/упаковку/коробку/пак/пачку)
- Скрытие товаров с остатком ≤1
- Товары без фото — заглушка-иконка
 
## Стандарты кода
- TypeScript для всего нового кода
- Компоненты — функциональные с хуками
- Стили — только Tailwind CSS
- Названия компонентов: PascalCase
 
## Команды
 
### Ежедневное обновление данных
```powershell
python scripts/upload.py
Remove-Item -Recurse -Force C:\catalog\.next
npm run build
git add --all ; git commit -m "Обновление данных" ; git push origin main
```
 
### Добавление фото нового поставщика
```powershell
# 1. Загрузить фото в Cloudinary
python scripts/upload_photos.py --folder имя_папки --source "путь_к_фото"
# 2. Дописать новые товары
python scripts/make_manual_sheet.py --append
# 3. Заполнить привязки в Excel, затем:
python scripts/apply_manual_sheet.py
python scripts/upload.py
Remove-Item -Recurse -Force C:\catalog\.next ; npm run build
git add --all ; git commit -m "описание" ; git push origin main
```
 
## Важные правила
- НЕ коммить .env, .env.local, credentials.json — они в .gitignore
- После upload.py ВСЕГДА удалять кэш: `Remove-Item -Recurse -Force C:\catalog\.next`
- PowerShell: ";" вместо "&&"
- UUID секретной ссылки — ТОЛЬКО в переменных (CATALOG_SECRET), проверка на сервере
- badges.json и photo_overrides.json — поиск частичный, регистронезависимый
- Если badges.json или photo_overrides.json отсутствуют — скрипт работает без ошибок
- force-dynamic в route.ts обязателен
- Закрывать photo_manual.xlsx в Excel перед запуском скриптов
- Старые привязки в photo_manual.xlsx НЕ удалять (товары могут вернуться)
- В photo_overrides.json формат "папка/имя_файла" — НЕ просто имя
- category_map.json работает только с заголовками Excel (строки без цены)
- Для переноса отдельных товаров между категориями — product_overrides в upload.py
 
## Выполнено
- ✅ Этап 0: upload.py (Excel → Google Sheet, 959 товаров, 84→11 категорий)
- ✅ Этап 1: Каталог с фильтрами и поиском
- ✅ Этап 2: Корзина + Telegram
- ✅ 3.1: Деплой Vercel (catalog-khaki.vercel.app)
- ✅ 3.2: Секретная UUID-ссылка
- ✅ 3.3: Спецметки badges.json
- 🔄 3.4: Фото — 853/935 с фото, описания не заполнены
 
## Что осталось
- [ ] Заполнить описания товаров в photo_manual.xlsx
- [ ] Загрузить 36 недостающих фото (Screenshot_213-334.png и др.)
- [ ] Адаптация карточек для десктопной версии
- [ ] Подключить PDF других поставщиков (Стоевъ, Мистраль, Richard)
 
---
 
## Telegram-бот «Каталог-консультант» (ПЛАНИРУЕТСЯ)
 
### Назначение
Telegram-бот для B2B-клиентов (владельцы магазинов). Консультирует по товарам через ИИ, принимает заказы. Работает на тех же данных из Google Sheet, что и сайт.
 
### Стек бота
- **Framework:** grammY (TypeScript, webhook mode)
- **ИИ:** Google Gemini Flash API (бесплатно, function calling)
- **Корзина:** Vercel KV (Redis)
- **Хостинг:** тот же Vercel, webhook через /api/bot
- **Заказы:** Telegram Bot API → сообщение владельцу
 
### Структура файлов бота
```
app/api/bot/route.ts          — Webhook endpoint
bot/
  index.ts                    — Инициализация grammY
  handlers/
    start.ts                  — /start, приветствие, меню
    catalog.ts                — Навигация по категориям (inline-кнопки)
    cart.ts                   — Просмотр и управление корзиной
    order.ts                  — Оформление и отправка заказа
  ai/
    consultant.ts             — Gemini Flash: обработка свободного текста
    tools.ts                  — Function calling: search, add_to_cart и т.д.
    system-prompt.ts          — Системный промпт + динамические данные
  services/
    products.ts               — Товары из Google Sheet (кэш 15 мин)
    cart-store.ts             — Корзина в Vercel KV (ключ: cart:{user_id})
    notify.ts                 — Отправка заказа владельцу
```
 
### Переменные окружения (добавить в .env.local)
```
TELEGRAM_BOT_TOKEN=           # от @BotFather
TELEGRAM_WEBHOOK_SECRET=      # случайная строка
OWNER_CHAT_ID=                # Telegram ID Олега
GEMINI_API_KEY=               # от ai.google.dev
KV_REST_API_URL=              # от Vercel KV
KV_REST_API_TOKEN=            # от Vercel KV
```
 
### Правила разработки бота
- Webhook-режим (Vercel serverless), НЕ polling
- Товары кэшировать на 15 мин
- Корзина в Vercel KV, ключ `cart:{telegram_user_id}`
- ИИ использует function calling для действий
- При ошибке Gemini — fallback: «Извините, попробуйте позже»
- Формат корзины: `[{productName, price, quantity, unit}]`
 
### Команды бота
- /start — приветствие + меню
- /cart — показать корзину
- /order — отправить заказ
- Свободный текст — обрабатывает ИИ
 
### Зависимости бота
```
grammy @google/generative-ai @vercel/kv
```
 