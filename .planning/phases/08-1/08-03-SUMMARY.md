---
phase: 08-1
plan: 03
subsystem: admin-ui
tags: [python, flask, admin-panel, hide-feature, optimistic-ui]

# Dependency graph
requires:
  - phase: 08-1
    plan: 01
    provides: "тип «скрыт» в sheet_helper.ALLOWED_TYPES и upload.ALLOWED_TYPES — путь записи готов"
provides:
  - "тип «скрыт» в SAVE_ALLOWED_TYPES admin.py — третий белый список закрыт"
  - "пустое значение для type=скрыт разрешено — снятие скрытия через value=''"
  - "кнопка-глазик .pcard-eye в левом верхнем углу фото каждой карточки"
  - "оптимистичная функция toggleHidden с откатом по образцу toggleBadge"
  - "CSS .pcard.hidden {opacity:0.45} — скрытая карточка тускнеет, остаётся интерактивной"
  - "чип .badge-hidden «скрыт» в .pcard-badges — виден во всех режимах"
  - "фильтр «Скрытые» в filter-tabs — только p.hidden; совместно с поиском"
affects:
  - "08-04: боевой прогон upload.py через сисадмина — проверка интеграции на проде"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "оптимистичный UI с откатом: toggleHidden строго по образцу toggleBadge (prev → apply → apiCall → rollback)"
    - "CSS-оверлей кнопки в углу фото: позиция left:4px, top:4px — не мешает карандашу right:4px"
    - "тусклость скрытого товара через CSS-класс, не через pointer-events — карточка остаётся интерактивной"
    - "клиентский фильтр filteredProducts расширяется одной веткой else if — без изменения механики вкладок"

key-files:
  created: []
  modified:
    - uploader/admin.py

key-decisions:
  - "[08-03] Глазик — left:4px, top:4px (не right) — карандаш кадрирования уже занимает right:4px"
  - "[08-03] Зона нажатия 44px — увеличена относительно карандаша 40px согласно D-05"
  - "[08-03] Глифы: 👁 (&#128065;) = видимый товар; 🙈 (&#128584;) = скрытый — понятная метафора"
  - "[08-03] badge-hidden — серо-синий стиль (slate), отличается от badge-attn (оранжевый) и badge-new (синий)"
  - "[08-03] Ветка all в filteredProducts НЕ фильтрует скрытые — они показываются тусклыми (D-08)"

requirements-completed: [HIDE-01, HIDE-02, HIDE-03]

# Metrics
duration: 3min
completed: 2026-06-11
---

# Phase 8 Plan 03: Кнопка-глазик и управление скрытием в admin.py Summary

**Бэкенд /save принимает тип `скрыт` под ADMIN_SECRET с разрешённым пустым значением; в карточке кнопка-глазик с оптимистичным переключением, тускнеющей карточкой, чипом «скрыт» и фильтром видимости — третий белый список закрыт, HIDE-01..03 выполнены**

## Performance

- **Duration:** ~3 мин
- **Started:** 2026-06-11T15:23:49Z
- **Completed:** 2026-06-11T15:26:37Z
- **Tasks:** 2 / 2
- **Files modified:** 1

## Accomplishments

### Task 1: Бэкенд /save — приём типа `скрыт`

- `SAVE_ALLOWED_TYPES` расширен: добавлен `"скрыт"` — третий (последний) белый список закрыт
- Кортеж исключений пустого значения: `("photo", "badge", "скрыт")` — `value=""` означает снятие скрытия
- Защита ADMIN_SECRET не изменена — новый тип проходит через тот же маршрут `/<TOKEN>/save`
- Путь записи (нормализация ключа → shell-out `sheet_helper append_edit`) не тронут

### Task 2: UI карточки — глазик, toggle, тускнение, чип, фильтр

**CSS:**
- `.pcard-eye`: `position:absolute; top:4px; left:4px; 44px×44px` — слева, чтобы не перекрывать карандаш `right:4px`
- `.pcard.hidden { opacity: 0.45; }` — без `pointer-events:none`, карточка остаётся интерактивной
- `.badge-hidden`: серо-синий чип по образцу `.badge-attn`

**buildCard:**
- Класс карточки `pcard hidden` при `p.hidden`
- `eyeBtn` с глифом `&#128065;` (👁, видимый) / `&#128584;` (🙈, скрытый) и `title`
- Чип `badge-hidden` в `.pcard-badges` при `p.hidden`

**JS — toggleHidden:**
- Строго по образцу `toggleBadge`: `const prev = p.hidden; const next = !p.hidden;`
- Оптимистично: `p.hidden = next; syncProduct(p);` + класс карточки, глиф кнопки, title, чип
- `apiCall` с `type: "скрыт", value: next ? "1" : ""`
- При ошибке: полный откат к `prev` (класс, глиф, title, чип) + `toast("err", ...)`
- БЕЗ диалога подтверждения (D-06)

**Фильтр видимости:**
- `filteredProducts`: ветка `activeFilter === "hidden"` → только `p.hidden`
- Ветка `all` не изменена — показывает ВСЕ, скрытые тусклыми
- `filter-tabs`: добавлена вкладка `data-filter="hidden"` «Скрытые»

## Task Commits

1. **Task 1: Бэкенд /save — тип `скрыт`** — `5d8ea67` (feat)
2. **Task 2: UI карточки — глазик, toggle, чип, фильтр** — `0645424` (feat)

## Files Created/Modified

- `uploader/admin.py` — SAVE_ALLOWED_TYPES + кортеж исключений + CSS глазика/тускнения/чипа + buildCard + toggleHidden + filteredProducts + filter-tabs

## Decisions Made

- Глазик слева (`left:4px`) — карандаш занимает `right:4px`, нельзя перекрывать
- Зона нажатия 44px (больше карандаша 40px) — соответствует мобильным тач-нормам
- Глифы 👁/🙈 — понятная метафора «видимый/скрытый»
- `badge-hidden` — стиль slate (серо-синий), визуально отличается от прочих бейджей
- Ветка `all` показывает всё включая скрытые — они тускнеют через CSS, не исчезают

## Deviations from Plan

Нет — план выполнен точно по спецификации. Все аналоги из 08-PATTERNS.md использованы напрямую.

## Threat Surface Scan

Нет новых сетевых эндпоинтов и путей записи. Тип `скрыт` проходит через существующий `/<TOKEN>/save` под `hmac.compare_digest` (T-08-05 mitigated).

## Known Stubs

Нет. Визуальная проверка в браузере — после деплоя на сервер (план 04).

## Self-Check: PASSED

- `uploader/admin.py` существует
- `python -m py_compile uploader/admin.py` — OK (проверено дважды)
- grep: `"скрыт"` в `SAVE_ALLOWED_TYPES` — FOUND
- grep: `not in ("photo", "badge", "скрыт")` — FOUND
- grep: `.pcard-eye`, `.pcard.hidden`, `badge-hidden` — FOUND
- grep: `toggleHidden`, `type: "скрыт"` — FOUND
- grep: `activeFilter === "hidden"` — FOUND
- grep: `data-filter="hidden"` — FOUND
- Коммиты `5d8ea67` и `0645424` присутствуют в git log

## Next Phase Readiness

- admin.py готов: все три белых списка закрыты, глазик работает
- Следующий шаг: план 04 — боевой прогон через сисадмина (деплой + проверка в браузере)

---
*Phase: 08-1*
*Completed: 2026-06-11*
