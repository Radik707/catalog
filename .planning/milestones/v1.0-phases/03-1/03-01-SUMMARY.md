---
phase: 03-1
plan: 01
subsystem: database
tags: [gspread, google-sheets, python, edit-memory, override, upload-pipeline]

# Dependency graph
requires:
  - phase: 01-1
    provides: "upload.py pipeline с форматами прайсов, normalize_name, apply_group_mapping, products_to_rows"
  - phase: 02-1
    provides: "веб-загрузчик прайсов (uploader/app.py) — запускает upload.py на сервере"
provides:
  - "load_edit_memory() — чтение вкладки «Правки» Google Sheet; возвращает {normalize_name: {тип: значение}}"
  - "apply_edit_memory() — наложение памяти (group/photo/description) поверх авто-маппинга"
  - "products_to_rows с приоритетом override-полей p['photo_override']/p['desc_override']"
  - "Лог числа товаров без правок (MEM-03 — основа «новых для разметки»)"
affects:
  - "03-02 (миграция PRODUCT_OVERRIDES во вкладку «Правки»)"
  - "этап 4 (админ-панель владельца — будет писать во вкладку «Правки»)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Вкладка Google Sheet как хранилище пользовательских правок (MEM-01)"
    - "Override-поля в словаре товара (photo_override/desc_override) для точного совпадения"
    - "Graceful-fallback: нет вкладки/credentials → {} без исключения, прогон продолжается"
    - "Два уровня обработки ошибок: WorksheetNotFound → log.info; Exception → log.warning"

key-files:
  created: []
  modified:
    - "scripts/upload.py — добавлены load_edit_memory(), apply_edit_memory(); изменены products_to_rows и main()"

key-decisions:
  - "Схема вкладки «Правки»: колонки Товар | Тип | Значение (по строке на правку, расширяемая)"
  - "Фото/описание через override-поля (вариант а), не через _find_photo_entry — гарантирует точное совпадение D-04"
  - "Отдельный бэкап вкладки «Правки» в Этапе 3 не создаётся (upload.py её только читает, T-03-05 accepted)"
  - "WorksheetNotFound — log.info (норма), широкий Exception — log.warning (ошибка доступа)"
  - "normalize_name() — единственный ключ сопоставления (D-04), никаких вторых нормализаций"

patterns-established:
  - "load_edit_memory: скопирован скелет load_current_groups (ленивый импорт gspread, цепочка credentials, scopes)"
  - "apply_edit_memory: чистая функция, не инлайн в main() — легко тестируется"
  - "Override приоритет в products_to_rows: p.get('photo_override') or get_photo_url(...)"

requirements-completed: [MEM-01, MEM-02, MEM-03]

# Metrics
duration: 4min
completed: 2026-06-07
---

# Этап 3 / План 01: Ядро памяти правок — Summary

**Вкладка «Правки» Google Sheet как персистентное хранилище правок владельца: load_edit_memory() + apply_edit_memory() в upload.py, точное совпадение по normalize_name (D-04), приоритет над авто-маппингом (D-06)**

## Performance

- **Duration:** ~4 мин
- **Started:** 2026-06-07T08:48:15Z
- **Completed:** 2026-06-07T08:52:21Z
- **Tasks:** 3
- **Files modified:** 1 (scripts/upload.py)

## Accomplishments

- Построена функция `load_edit_memory()` — читает вкладку «Правки» той же Google-таблицы, возвращает `{normalize_name(товар): {тип: значение}}`, graceful-fallback при отсутствии вкладки/credentials
- Построена функция `apply_edit_memory()` — накладывает group/photo/description поверх авто-маппинга строго по точному нормализованному имени (D-04, без риска «приклеивания» к другому товару)
- Интеграция в `main()`: память загружается рядом с `photo_data`, накладывается ПОСЛЕ `apply_group_mapping` и блока нового формата, ПЕРЕД `products_to_rows` (порядок D-06)
- `products_to_rows` изменён: `p.get("photo_override") or get_photo_url(...)` — override-поля имеют приоритет
- Лог `"Товаров без правок (новые для памяти): N"` — реализует MEM-03
- Локальная проверка подтвердила все три типа правок И точное совпадение D-04 (правка «Сок» не приклеилась к «Сок ананасовый»)

## Схема вкладки «Правки» (зафиксировано для Task миграции и панели Этапа 4)

| Колонка | Заголовок | Описание |
|---------|-----------|----------|
| A | Товар | Нормализованное имя товара (ключ для сопоставления, D-04) |
| B | Тип | Тип правки: `group`, `photo`, `description` |
| C | Значение | Новое значение: название группы / URL фото / текст описания |

Несколько типов на один товар — несколько строк с одинаковым «Товар».
Схема расширяемая — Этап 4 добавит типы `price`, `name` без переделки.

## Подтверждение технических решений (D-04 и T-03-05)

**D-04 (точное совпадение):** Фото/описание применяются через поля `p["photo_override"]` / `p["desc_override"]`, которые заполняет `apply_edit_memory()` строго по `normalize_name`. Путь `_find_photo_entry` (подстрока) для правок НЕ используется. Доказано локальной проверкой: правка «Сок» не применилась к «Сок ананасовый».

**T-03-05 (бэкап вкладки «Правки»):** Отдельный бэкап вкладки «Правки» в Этапе 3 НЕ создаётся. Обоснование: `upload.py` вкладку только ЧИТАЕТ, не перезаписывает — риск повреждения штатным прогоном отсутствует. Вкладка автоматически бэкапируется Google. Дополнительный бэкап избыточен.

## Task Commits

1. **Task 1: load_edit_memory()** — `fa4530e` (feat)
2. **Task 2: apply_edit_memory() + интеграция + лог** — `26e5940` (feat)
3. **Task 3: локальная проверка** — нет отдельного коммита (изменений в upload.py не потребовалось; все проверки через Bash python -c)

## Files Created/Modified

- `scripts/upload.py` — добавлены `load_edit_memory()` (102 строки), `apply_edit_memory()` (31 строка); изменены `products_to_rows` (приоритет override-полей) и `main()` (загрузка + наложение памяти)

## Decisions Made

- **Колонки вкладки «Правки»:** `Товар | Тип | Значение` — по строке на правку, расширяемая схема
- **Вариант (а) для фото/описания:** override-поля `photo_override`/`desc_override` в словаре товара, не слияние с `photo_data` — гарантирует точное совпадение D-04
- **Бэкап вкладки «Правки» не нужен** в Этапе 3: upload.py её только читает, Google бэкапит автоматически
- **WorksheetNotFound → log.info** (норма, не ошибка), широкий **Exception → log.warning**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Исправлено ожидание счётчика в команде verify Task 3**
- **Найдено при:** Task 3 (локальная проверка)
- **Проблема:** Команда verify из плана требовала `n >= 2`, но при 3 товарах в памяти из 4 синтетических счётчик корректно возвращает 1 (только «Сок ананасовый» без правки)
- **Исправление:** Реализация `apply_edit_memory()` верна; ожидание в verify исправлено на `n == 1`; функциональные требования MEM-03 выполнены — счётчик возвращает ровно число товаров без записи в памяти
- **Файлы:** изменений в upload.py нет, ошибка только в тестовом условии
- **Подтверждение:** Все остальные 5 проверок Task 3 прошли с первого запуска (group, photo, description, D-04 exact, counter)

---

**Итого отклонений:** 1 (исправление ожидания в тестовом условии)
**Влияние:** Только тестовое условие; реализация верна, функциональные требования выполнены полностью.

## Issues Encountered

Кодировка терминала Windows (cp1252) не поддерживает кириллицу в `print()` внутри Python `python -c`. Решение: запуск с `PYTHONIOENCODING=utf-8` и/или использование латинских тестовых данных для промежуточных проверок.

## User Setup Required

Для использования памяти правок владелец должен создать вкладку «Правки» в Google-таблице с заголовками `Товар | Тип | Значение`. Вкладка создаётся вручную один раз — до или после деплоя этапа. Если вкладка отсутствует, upload.py работает без ошибок (память пуста).

## Next Phase Readiness

- Ядро памяти правок готово: load_edit_memory + apply_edit_memory в production-коде
- Следующий шаг: **03-02** — перенос `PRODUCT_OVERRIDES`/`PRODUCT_CONTAINS_OVERRIDES` из кода во вкладку «Правки» (migrate_overrides.py + удаление словарей из upload.py)
- Вкладка «Правки» должна быть создана вручную перед боевым прогоном (см. User Setup Required)

## Self-Check: PASSED

- FOUND: `scripts/upload.py` содержит `load_edit_memory` ✓
- FOUND: `scripts/upload.py` содержит `apply_edit_memory` ✓
- FOUND: поля `photo_override`, `desc_override` ✓
- FOUND: счётчик `new_for_memory` ✓
- FOUND: коммит `fa4530e` (Task 1) ✓
- FOUND: коммит `26e5940` (Task 2) ✓

---
*Этап: 03-1*
*Завершено: 2026-06-07*
