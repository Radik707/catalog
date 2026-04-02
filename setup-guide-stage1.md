# Этап 1 — Запуск каталога

## Что уже есть
У тебя настроен Google Cloud проект и Google Sheet с данными (Этап 0).
Теперь нужно создать API Key для чтения и сделать таблицу публичной.

---

## Шаг 1: Сделать Google Sheet публичной (только чтение)

1. Открой свою Google Sheet с товарами
2. Нажми **«Share»** (Поделиться)
3. Внизу нажми **«Change to anyone with the link»**
4. Убедись что стоит роль **«Viewer»** (Читатель)
5. Нажми **«Done»**

Это безопасно — таблицу можно только смотреть, но не редактировать.

---

## Шаг 2: Создать API Key

1. Открой: https://console.cloud.google.com/apis/credentials
2. Убедись что выбран твой проект **catalog**
3. Нажми **«+ Create Credentials»** → **«API Key»**
4. Скопируй ключ
5. (Рекомендуется) Нажми **«Edit API key»** → в разделе **«API restrictions»**
   выбери **«Restrict key»** → отметь только **«Google Sheets API»** → Save

---

## Шаг 3: Настроить .env.local

Создай файл `.env.local` в корне проекта `C:\catalog\`:

```
GOOGLE_SHEETS_ID=твой_id_таблицы
GOOGLE_API_KEY=твой_api_key
```

---

## Шаг 4: Скопировать файлы проекта

Скопируй всё содержимое папки `catalog/` из скачанного архива в `C:\catalog\`.
Итоговая структура:

```
C:\catalog\
├── app/
│   ├── api/products/route.ts
│   ├── cart/page.tsx
│   ├── globals.css
│   ├── layout.tsx
│   └── page.tsx
├── components/
│   ├── CartIcon.tsx
│   ├── CatalogView.tsx
│   ├── CategoryFilter.tsx
│   ├── ProductCard.tsx
│   └── SearchBar.tsx
├── lib/
│   ├── sheets.ts
│   └── types.ts
├── scripts/           ← уже есть с Этапа 0
├── .env.local         ← из Шага 3
├── .gitignore
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.mjs
└── next.config.mjs
```

---

## Шаг 5: Установить и запустить

```
cd C:\catalog
npm install
npm run dev
```

Открой в браузере: http://localhost:3000

---

## Что должно работать

- Список товаров с ценами и остатками
- Кнопки групп (горизонтальный скролл, sticky)
- Поиск по названию с счётчиком
- Товары с остатком 0 — серые, кнопка неактивна
- Кнопка «В корзину» (пока просто увеличивает счётчик)
- Страница /cart (заглушка для Этапа 2)

---

## Если что-то не так

| Проблема | Решение |
|----------|---------|
| Пустой список товаров | Проверь .env.local — GOOGLE_SHEETS_ID и GOOGLE_API_KEY |
| 403 от Google API | Таблица не публичная (Шаг 1) или API Key без доступа к Sheets API |
| Ошибка сборки | Удали node_modules и package-lock.json, запусти npm install заново |
