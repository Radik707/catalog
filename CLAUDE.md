# Каталог торгового представителя

## О проекте
Мобильный B2B-каталог товаров для владельцев магазинов. Клиент открывает сайт с телефона → видит товары с ценами и наличием → набирает корзину → отправляет заказ в Telegram.

Данные: Excel-файлы поставщиков → Python-скрипт upload.py → Google Sheet → сайт читает через API.

## Стек технологий
- **Сайт:** Next.js 14 (App Router) + Tailwind CSS + TypeScript
- **Данные:** Google Sheets API (публичная таблица, только чтение)
- **Скрипт-конвертер:** Python (openpyxl + gspread)
- **Корзина:** localStorage в браузере
- **Отправка заказа:** deep link Telegram (без сервера)
- **Хостинг:** Vercel (пока локально)

## Структура папок
```
C:\catalog\
├── app\
│   ├── api\products\route.ts   # API: товары из Google Sheets
│   ├── cart\page.tsx            # Страница корзины
│   ├── globals.css
│   ├── layout.tsx               # Общий макет (шапка, подвал)
│   └── page.tsx                 # Главная страница каталога
├── components\
│   ├── CartIcon.tsx
│   ├── CatalogView.tsx
│   ├── CategoryFilter.tsx
│   ├── ProductCard.tsx
│   └── SearchBar.tsx
├── lib\
│   ├── sheets.ts                # Клиент Google Sheets API
│   └── types.ts                 # TypeScript типы
├── scripts\                     # Python-скрипт для загрузки данных
├── .env.local                   # Переменные для Next.js
└── CLAUDE.md
```

## Стандарты кода
- TypeScript для всего нового кода
- Компоненты — функциональные (не классовые)
- Стили — только Tailwind CSS, не создавай отдельные CSS-файлы
- Названия компонентов: PascalCase (ProductCard, OrderForm)
- Mobile-first: сначала мобильная версия

## Команды
- `npm run dev` — запустить локально (http://localhost:3000)
- `npm run build` — проверить сборку
- `python scripts/upload.py` — обновить данные из Excel

## Данные
- 959 товаров, 12 категорий (группы в category_map.json)
- Товар: name, price, stock, category, supplier
- Google Sheet ID в .env.local

## Важные правила
- НЕ трогай .env.local и scripts/credentials.json
- НЕ меняй логику API в api/products/route.ts без запроса
- НЕ делай коммит без одобрения
- Всё должно хорошо выглядеть на телефоне (320px минимум)
- Проверяй что существующий функционал не сломался после изменений

## Текущий статус
- ✅ Этап 1 готов: каталог, поиск, фильтр по категориям
- ⬜ Этап 2 в работе: корзина + отправка заказа в Telegram
