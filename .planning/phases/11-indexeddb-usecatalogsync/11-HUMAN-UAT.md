---
status: partial
phase: 11-indexeddb-usecatalogsync
source: [11-VERIFICATION.md]
started: 2026-06-12T17:00:00Z
updated: 2026-06-12T17:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Офлайн-запуск с данными (OFF-01)
expected: Открыть каталог онлайн → закрыть вкладку → авиарежим → открыть снова. Весь список товаров с ценами, остатками и бейджами, без белого экрана и спиннеров.
result: [pending]

### 2. Офлайн-навигация (OFF-02)
expected: В авиарежиме переключать разделы/подгруппы, вводить поиск, открывать Хит/Новинка. Все фильтры работают по данным из IndexedDB без обращений к сети.
result: [pending]

### 3. IndexedDB в DevTools (OFF-03)
expected: После первого онлайн-открытия DevTools → Application → IndexedDB → catalog-db: два store (products, meta), в products под ключом 'all' массив Product[], в meta — syncTimestamp.
result: [pending]

### 4. Скелетон при первой загрузке (D-02)
expected: Первое открытие на медленной сети (или Network throttling) показывает сетку из 12 серых карточек с анимацией pulse — не спиннер и не пустой экран.
result: [pending]

### 5. Заглушка офлайн-без-данных (D-03)
expected: Чистый профиль браузера + сеть выключена до первого открытия → иконка 📵, заголовок «Каталог ещё не загружен», текст «Подключитесь к интернету один раз…», без кнопки обновления.
result: [pending]

### 6. Реальный iPhone (критерий ROADMAP №5)
expected: Safari на iPhone → каталог онлайн → авиарежим → открыть каталог. Товары видны без сети. Обязательная проверка — эмулятор недостаточен (iOS Storage API + отсутствие 7-дневного eviction).
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps
