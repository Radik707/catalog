---
phase: 05-структура-данных
plan: 01
subsystem: data
tags: [python, json, pytest, category-map, structure-map, navigation]

requires:
  - phase: 04-admin-panel
    provides: "upload.py pipeline + category_map.json — образец для structure_map.json"

provides:
  - "scripts/structure_map.json — единый источник правды двухуровневой навигации (5 разделов → подгруппы → 117 категорий)"
  - "scripts/test_structure_map.py — 9 pytest-тестов, защищающих контракт данных"

affects:
  - "05-02 (upload.py): читает structure_map.json для проставления Подгруппа/Раздел"
  - "06-navigation-ui: разделы и подгруппы из structure_map.json становятся основой аккордеона витрины"
  - "07-admin-subgroups: выбор подгруппы в панели опирается на этот же файл"

tech-stack:
  added: []
  patterns:
    - "Вложенный JSON-конфиг рядом с category_map.json: разделы → подгруппы → массивы категорий"
    - "Порядок = позиция в массиве (без числовых полей order)"
    - "pytest-тесты как формальная защита data-контракта (покрытие множеств через set equality)"

key-files:
  created:
    - scripts/structure_map.json
    - scripts/test_structure_map.py
  modified: []

key-decisions:
  - "D-01/D-02: вложенный JSON без числовых полей order — переставить строку = переставить кластер"
  - "D-06: 7 коробочных конфет (Коробочные/Подарки/Торты/Набор конфет ЛЮСИ/МВН/Сонуар/Фас. кор.) — кластером в конце «Конфеты»"
  - "REGRP-01: группа «Стоевъ и Сэнсой» расформирована по смыслу категорий (без ручной разметки товаров)"
  - "REGRP-02/D-10: Конфеты и Печенье и вафли — две отдельные подгруппы; Сладонеж в «Печенье и вафли»"
  - "REGRP-03/D-11: Мистраль Крупы варпак в «Крупы и бакалея»"
  - "D-07/D-08/D-09: Let's Be, Продако, Квас в «Воды и газировки»"

patterns-established:
  - "Тест test_полное_покрытие: set(structure_map категорий) == set(category_map ключей) — шаблон для защиты JSON-контрактов от потерь при ручной правке"

requirements-completed: [STRUCT-01, STRUCT-02, STRUCT-03, STRUCT-05, REGRP-01, REGRP-02, REGRP-03]

duration: 8min
completed: 2026-06-09
---

# Phase 5 Plan 01: Структура данных двухуровневой навигации — Summary

**Вложенный JSON `structure_map.json` — 5 разделов → 13 подгрупп → 117 категорий (дословно из category_map.json), с кластером коробочных конфет и pytest-защитой полного покрытия**

## Performance

- **Duration:** ~8 мин
- **Started:** 2026-06-09
- **Completed:** 2026-06-09
- **Tasks:** 2 из 2
- **Files modified:** 2

## Accomplishments

- Создан `scripts/structure_map.json` — единый источник правды двухуровневой структуры каталога: 5 разделов в заданном порядке, 13 подгрупп, 117 категорий (0 пропущенных)
- Расформирована группа «Стоевъ и Сэнсой» (REGRP-01): 12 категорий разложены по смыслу без ручной разметки товаров
- Создан `scripts/test_structure_map.py` — 9 pytest-тестов, защищающих контракт: полное покрытие 117/117 категорий, порядок разделов, кластеры, перекладка

## Task Commits

1. **Задача 1: Создать scripts/structure_map.json** — `b5fdc8f` (feat)
2. **Задача 2: Pytest — покрытие всех 117 категорий** — `8012938` (test)

## Files Created/Modified

- `scripts/structure_map.json` — вложенный JSON-конфиг: 5 разделов → 13 подгрупп → 117 категорий; порядок = позиция в массиве (D-02)
- `scripts/test_structure_map.py` — 9 pytest-тестов без сетевых вызовов; выполняется за 0.06 с

## Decisions Made

- Порядок в файле = позиция в массиве (без полей order). Переставить строку = переставить кластер. Владелец может редактировать без знания кода.
- Тест `test_полное_покрытие` использует равенство множеств (set equality) — точная формальная гарантия без пропусков.
- Категории «Стоевъ и Сэнсой» раскладываются по смыслу имени (СэнСой Соусы → соусы, Стоевъ Консервация → консервация) — без поштучной разметки товаров.

## Deviations from Plan

Нет — план выполнен точно по инструкции.

## Issues Encountered

Нет.

## User Setup Required

Нет — конфигурация не требует ручных действий. Файл `structure_map.json` создан и готов к использованию в плане 05-02 (`upload.py`).

## Known Stubs

Нет.

## Threat Flags

Нет новых поверхностей атаки — локальный JSON-конфиг, сетевых эндпоинтов нет (T-05-03: accepted в threat_model плана).

## Next Phase Readiness

- `scripts/structure_map.json` готов — план 05-02 может читать его через `load_structure_map()` и проставлять поля «Подгруппа» и «Раздел» в upload.py
- pytest-тесты подтверждают контракт: 117/117 категорий покрыто, порядок и кластеры зафиксированы
- Перед боевым прогоном upload.py нужна ручная сверка владельцем через `python scripts/upload.py --dry-run` (D-13 из контекста этапа)

## Self-Check: PASSED

- `scripts/structure_map.json` — существует, парсится ✓
- `scripts/test_structure_map.py` — существует, 9 тестов GREEN ✓
- Коммиты `b5fdc8f` и `8012938` — в истории ✓

---
*Phase: 05-структура-данных*
*Completed: 2026-06-09*
