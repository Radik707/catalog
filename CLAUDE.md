# Каталог торгового представителя

## О проекте
Мобильный B2B-каталог товаров для владельцев магазинов.
Клиент открывает ссылку → видит товары с ценами → набирает корзину → отправляет заказ в Telegram.
Данные из Excel поставщиков загружаются через Python-скрипт в Google Sheet, сайт читает оттуда.

## Стек
- **Сайт:** Next.js 14 (App Router) + Tailwind CSS + TypeScript
- **Данные:** Google Sheets API (только чтение)
- **Скрипт:** Python (openpyxl, gspread, python-dotenv, cloudinary)
- **Корзина:** localStorage
- **Заказ:** deep link Telegram
- **Фото:** Cloudinary (бесплатный план)
- **Хостинг:** Vercel (бесплатный план)

## Структура файлов
```
C:\catalog\
├── app\
│   ├── catalog\[secret]\         # Защищённый каталог (UUID в URL)
│   │   ├── page.tsx              # Главная каталога
│   │   ├── layout.tsx            # Макет с шапкой
│   │   └── cart\page.tsx         # Страница корзины
│   ├── api\products\route.ts     # API: товары из Google Sheets
│   ├── page.tsx                  # Заглушка (404)
│   ├── globals.css
│   └── layout.tsx                # Корневой макет
├── components\
│   ├── CartIcon.tsx
│   ├── CatalogView.tsx
│   ├── CategoryFilter.tsx
│   ├── ProductCard.tsx           # Карточка с бейджиком и фото
│   └── SearchBar.tsx
├── lib\
│   ├── sheets.ts
│   └── types.ts                  # Product: badge?, imageUrl?
├── scripts\
│   ├── upload.py                 # Excel → Google Sheet (+ badges + images)
│   ├── upload_images.py          # Загрузка фото в Cloudinary
│   ├── category_map.json         # 84 категории → 11 групп
│   ├── badges.json               # Хиты, новинки, акции
│   ├── image_map.json            # Название товара → файл фото
│   ├── requirements.txt
│   └── credentials.json          # НЕ в Git!
├── .env                          # Python-переменные (НЕ в Git!)
├── .env.local                    # Next.js переменные (НЕ в Git!)
└── .gitignore
```

## Стандарты кода
- TypeScript для всего нового кода
- Компоненты — функциональные с хуками
- Стили — только Tailwind CSS
- Названия компонентов: PascalCase

## Команды
- `npm run dev` — запустить локально
- `npm run build` — проверить сборку
- `python scripts/upload.py` — обновить данные из Excel
- `python scripts/upload_images.py` — загрузить фото в Cloudinary

## Важные правила
- НЕ коммить .env, .env.local, credentials.json — они в .gitignore
- После upload.py удалять кэш: `Remove-Item -Recurse -Force C:\catalog\.next`
- PowerShell использует ";" вместо "&&" для цепочки команд
- UUID для секретной ссылки — ТОЛЬКО в переменных окружения (CATALOG_SECRET)
- Проверку UUID делать на сервере (серверный компонент)
- badges.json и image_map.json — поиск по частичному совпадению, регистронезависимый
- Если badges.json или image_map.json отсутствуют — скрипт работает без ошибок
- Cloudinary домен добавить в next.config.mjs (remotePatterns)

## Текущий этап: 3 — Полировка и деплой
Задачи в файле tasks_stage3.md, выполнять по порядку: 3.1 → 3.2 → 3.3 → 3.4

## Выполнено
- Этап 0: upload.py (Excel → Google Sheet) ✅
- Этап 1: Каталог с фильтрами и поиском ✅
- Этап 2: Корзина + Telegram ✅
- Пересортировка категорий, фасовка, скрытие остатков ≤1 ✅
