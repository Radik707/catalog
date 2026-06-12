---
phase: 08-1
plan: 01
subsystem: api
tags: [python, google-sheets, edit-memory, expand-contract]

# Dependency graph
requires:
  - phase: 07-1
    provides: "тип правки «подгруппа» в ALLOWED_TYPES — образец для expand-contract и наложения ожидающей правки"
provides:
  - "тип «скрыт» принят в белых списках sheet_helper.py и upload.py"
  - "колонка «Скрыт» (L, 12-я) добавлена в конец строки листа «Товары» — expand-contract"
  - "upload.py разворачивает правку «скрыт» в p[\"hidden\"]; скрытый товар остаётся в листе"
  - "sheet_helper.load_products читает hidden_i, накладывает ожидающую правку, кладёт «hidden» в словарь товара"
affects:
  - "08-02: lib/sheets.ts фильтрует скрытые по колонке L"
  - "08-03: admin.py белый список + глазик-кнопка"
  - "08-04: боевой прогон upload.py через сисадмина"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "expand-contract: новая колонка «Скрыт» добавляется В КОНЕЦ строки Sheet, не сдвигая существующие колонки A–K"
    - "ожидающая правка из edit_values накладывается поверх значения из листа перед возвратом из load_products"

key-files:
  created: []
  modified:
    - scripts/sheet_helper.py
    - scripts/upload.py

key-decisions:
  - "[08-01] Значение «скрыт» хранится как строка «1»/«» (не bool) — фронтенд admin.py сравнивает с «1»"
  - "[08-01] Скрытый товар НЕ вырезается из строк products_to_rows — остаётся в листе «Товары» с флагом (HIDE-02)"
  - "[08-01] Фильтрация скрытых происходит на стороне Next.js (lib/sheets.ts) — план 02"

patterns-established:
  - "expand-contract колонка 12-я (L): дописать в конец header + rows.append, fallback add_worksheet обновить"

requirements-completed: [HIDE-04]

# Metrics
duration: 8min
completed: 2026-06-11
---

# Phase 8 Plan 01: Тип правки «скрыт» в Python-пайплайне Summary

**Тип правки `скрыт` принят обоими белыми списками (sheet_helper + upload), колонка «Скрыт» (L) добавлена expand-contract в конец строки Sheet, скрытый товар остаётся в листе с флагом «1»**

## Performance

- **Duration:** ~8 мин
- **Started:** 2026-06-11T~15:10:00Z
- **Completed:** 2026-06-11T~15:18:00Z
- **Tasks:** 2 / 2
- **Files modified:** 2

## Accomplishments

- `scripts/sheet_helper.py`: добавлен `"скрыт"` в `ALLOWED_TYPES`; `load_products` читает колонку «Скрыт» через опциональный `hidden_i`, накладывает ожидающую правку из `edit_values`, кладёт `"hidden"` в словарь товара
- `scripts/upload.py`: добавлен `"скрыт"` в `ALLOWED_TYPES`; `apply_edit_memory` разворачивает правку в `p["hidden"]`; заголовок и строка `products_to_rows` расширены колонкой «Скрыт» 12-м элементом; `add_worksheet` fallback обновлён с 11 до 12
- Оба файла прошли `python -m py_compile` без ошибок; grep подтвердил наличие всех ключевых строк

## Task Commits

1. **Task 1: Тип `скрыт` в памяти правок — sheet_helper.py** — `bf57304` (feat)
2. **Task 2: Разворот правки `скрыт` и колонка «Скрыт» (L) — upload.py** — `bd02e40` (feat)

## Files Created/Modified

- `scripts/sheet_helper.py` — ALLOWED_TYPES расширен; load_products: hidden_i, чтение hidden, наложение правки, ключ «hidden» в словаре
- `scripts/upload.py` — ALLOWED_TYPES расширен; apply_edit_memory: разворот в p["hidden"]; products_to_rows: заголовок+строка +«Скрыт»; add_worksheet fallback 11→12

## Decisions Made

- Значение хранится как строка `"1"`/`""`, не bool — admin.py на стороне сервера сравнивает с `"1"`, конвертация в TypeScript делается в `lib/sheets.ts` в плане 02
- Скрытый товар остаётся в листе «Товары» — иначе нельзя вернуть товар через панель (HIDE-02)
- Фильтр `p => !p.hidden` применяется на сервере Next.js (план 02), не в upload.py

## Deviations from Plan

Нет — план выполнен точно по спецификации.

## Issues Encountered

Нет.

## Known Stubs

Нет — Python-пайплайн не работает с UI-компонентами.

## Self-Check: PASSED

- `scripts/sheet_helper.py` существует и содержит `"скрыт"` в ALLOWED_TYPES
- `scripts/upload.py` существует и содержит `"скрыт"` в ALLOWED_TYPES, `"Скрыт"` в header, `p.get("hidden","")` в rows.append
- Коммиты `bf57304` и `bd02e40` присутствуют в git log

## Next Phase Readiness

- Python-пайплайн готов: правка «скрыт» записывается, читается и разворачивается в `p["hidden"]`
- Следующий шаг: план 02 — `lib/sheets.ts` расширить диапазон до A2:L, добавить `hidden` в Product, фильтровать скрытые на сервере

---
*Phase: 08-1*
*Completed: 2026-06-11*
