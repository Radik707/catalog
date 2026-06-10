---
phase: "01-1"
plan: "01"
subsystem: "scripts/upload.py, components/CatalogView.tsx"
tags: [testing, parser, новый-формат, новинки, фронтенд]
dependency_graph:
  requires: []
  provides: [контракт-парсера, pytest-покрытие, GROUP_ORDER-новинки]
  affects: [scripts/upload.py, components/CatalogView.tsx]
tech_stack:
  added: [pytest>=8]
  patterns: [pytest-fixtures-in-tmp_path, tdd-green-on-first-run]
key_files:
  created:
    - scripts/test_upload_new_format.py
  modified:
    - scripts/upload.py
    - components/CatalogView.tsx
decisions:
  - "Тесты GREEN с первого запуска — существующий код корректен, парсер не менялся (только docstring)"
  - "«Новинки» — первая позиция в GROUP_ORDER, чтобы новые товары сразу были заметны владельцу"
metrics:
  duration_seconds: 163
  completed_date: "2026-06-07"
  tasks_completed: 3
  files_created: 1
  files_modified: 2
---

# Фаза 1 План 01: Боевой прогон нового формата 1С — локальная подготовка

**Суть:** Pytest-контракт парсера двух форматов Excel и детерминированный показ «Новинки» в витрине.

## Что сделано

### Задача 1: Pytest-тесты (29 тестов, все PASSED)

Создан `scripts/test_upload_new_format.py` с 6 классами тестов:

| Класс | Что проверяет | Тестов |
|-------|--------------|--------|
| `TestIsNewFormat` | `is_new_format()` — граничные случаи (None, 1, 4, 5, 13) | 5 |
| `TestFindHeaderCols` | `find_header_cols()` — новый/старый/пустой лист | 3 |
| `TestParseNewFormat` | `parse_new_format()` — количество, очистка названия, цена/остаток, source_category, строки-дубли | 5 |
| `TestParseOldFormat` | `parse_excel_file()` — категории, префикс «а», цена/остаток, итоговое количество | 5 |
| `TestCleanAndNormalizeName` | `clean_new_name()`, `normalize_name()` — суффикс, регистр, пробелы | 6 |
| `TestNovinkiLogic` | Ветка новинок — известный/неизвестный товар, смешанная партия | 5 |

Фикстуры `.xlsx` генерируются в памяти через `openpyxl.Workbook()` в `tmp_path` — бинарные файлы не коммитятся. Сетевых вызовов нет.

Коммит: `d5c1148`

### Задача 2: Точечное укрепление upload.py

Все 29 тестов прошли GREEN с первого запуска на существующем коде. Парсер не изменялся.

Единственная правка — актуализация docstring модуля: описание обоих форматов, логики новинок, режима dry-run, подушки безопасности через `sheet_tool.py`. Это нормальный исход — код уже корректен.

Проверка FMT-04 подтверждена: `grep -v '^#' scripts/upload.py | grep -c "if not current_groups"` → 1 (ветка прерывания на месте).

Коммит: `68c55e0`

### Задача 3: GROUP_ORDER с «Новинками» (GRP-03)

В `components/CatalogView.tsx` строка `"Новинки"` добавлена первой в массив `GROUP_ORDER` (индекс 0). Баг из CONCERNS.md «Новинки не включены в GROUP_ORDER» закрыт.

Логика `?filter=new` в `app/catalog/[secret]/page.tsx` не изменена — фильтр по `badge === "новинка"` сохранён.

`npx tsc --noEmit` — без ошибок.

Коммит: `b66db5c`

## Отклонения от плана

**Отклонений нет.** Тесты написаны ровно так, как описано в плане. Существующий код парсера оказался корректным — Task 2 не выявил падений, что является нормальным и ожидаемым исходом, явно предусмотренным планом.

## Стабы

Нет. Все функции под тестами — рабочий код, не заглушки.

## Покрытие требований

| Требование | Статус |
|-----------|--------|
| FMT-01: смешанная партия (старый + новый формат) | Подтверждён тестом `test_mixed_batch_only_new_format_goes_to_novinki` |
| FMT-02: parse_new_format извлекает D/N/O | Подтверждён классом `TestParseNewFormat` |
| FMT-03: parse_excel_file без изменений | Подтверждён классом `TestParseOldFormat` |
| FMT-04: прерывание при пустых группах | Код проверен (grep=1), docstring описывает поведение |
| GRP-01: normalize_name для сопоставления | Подтверждён `TestCleanAndNormalizeName` |
| GRP-02: новый товар → «Новинки» + new_names | Подтверждён `TestNovinkiLogic` |
| GRP-03: «Новинки» в GROUP_ORDER витрины | Реализован в CatalogView.tsx (первая позиция) |

## Метрики

- Длительность: ~3 минуты
- Задач выполнено: 3 / 3
- Файлов создано: 1 (`test_upload_new_format.py`)
- Файлов изменено: 2 (`upload.py`, `CatalogView.tsx`)
- Тестов написано: 29 (все PASSED)
- Функций протестировано: 7 (`is_new_format`, `find_header_cols`, `parse_new_format`, `parse_excel_file`, `clean_new_name`, `normalize_name`, логика новинок)

## Self-Check: PASSED

- [x] `scripts/test_upload_new_format.py` существует: FOUND
- [x] Коммит `d5c1148` существует (test)
- [x] Коммит `68c55e0` существует (docs/upload.py)
- [x] Коммит `b66db5c` существует (feat/CatalogView)
- [x] `"Новинки"` в CatalogView.tsx: grep → 1
- [x] `if not current_groups` в upload.py: grep → 1
- [x] 29 тестов PASSED
- [x] `npx tsc --noEmit` — OK
