---
phase: 08-1
verified: 2026-06-11T00:00:00Z
status: passed
score: 5/5
overrides_applied: 0
---

# Этап 8: Скрытие товаров «глазиком» — Отчёт верификации

**Цель этапа:** Владелец одним нажатием скрывает ненужный товар с витрины (и так же возвращает) — без правки кода и таблиц; скрытие переживает перепрогон прайсов.

**Проверено:** 2026-06-11
**Статус:** PASSED
**Повторная верификация:** Нет — первичная

---

## Достижение цели

### Наблюдаемые истины (Критерии успеха из ROADMAP)

| # | Истина | Статус | Доказательство |
|---|--------|--------|----------------|
| 1 | Владелец нажимает глазик в карточке — товар исчезает с витрины; повторный клик возвращает товар обратно | VERIFIED | `toggleHidden()` в `uploader/admin.py:1319`: optimistic toggle → `apiCall` с `type:"скрыт"`, `value:"1"/""`; откат при ошибке. Витрина фильтрует скрытых в `lib/sheets.ts:88` |
| 2 | Скрытая карточка в панели визуально тускнеет, иконка меняется — сразу видно, что товар скрыт | VERIFIED | CSS `.pcard.hidden { opacity: 0.45; }` (`admin.py:801`); глифы `&#128065;`/`&#128584;` в `buildCard` (`admin.py:1115`); чип `<span class="badge-hidden">скрыт</span>` (`admin.py:1126`) |
| 3 | После перепрогона прайсов (`upload.py`) скрытые товары по-прежнему остаются скрытыми | VERIFIED | `upload.py:503` — `"скрыт"` в `ALLOWED_TYPES`; `apply_edit_memory` разворачивает правку в `p["hidden"]` (`upload.py:608`); колонка «Скрыт» (L) записывается в лист (`upload.py:852`) |
| 4 | Запрос `/api/products` не возвращает скрытые товары — браузер клиента их не получает вообще | VERIFIED | `lib/sheets.ts:88`: `return products.filter((p) => !p.hidden)` — последняя операция перед return, после fallback-блока structure_map. `app/api/products/route.ts` использует `force-dynamic` |
| 5 | Товар остаётся в листе «Товары» Google Sheet — владелец может вернуть его в любой момент | VERIFIED | `upload.py:606-609` — комментарий «Товар НЕ вырезается»; `p["hidden"] = edit["скрыт"]` устанавливает флаг, строка товара записывается в лист без изъятия. Боевой прогон: 807 товаров без ошибок, 12 колонок в листе |

**Счёт: 5/5 истин подтверждены**

---

## Проверка артефактов

### Уровень 1: Существование файлов

| Артефакт | Существует | Коммит(ы) |
|----------|-----------|-----------|
| `scripts/sheet_helper.py` | ДА | `bf57304` |
| `scripts/upload.py` | ДА | `bd02e40` |
| `lib/types.ts` | ДА | `d3e61b5` |
| `lib/sheets.ts` | ДА | `d3e61b5`, `7f03081`, `6437674` |
| `uploader/admin.py` | ДА | `5d8ea67`, `0645424` |
| `app/catalog/[secret]/page.tsx` | ДА | `6437674` |
| `app/api/products/route.ts` | ДА | `6437674` |

### Уровень 2: Содержимое (не заглушки)

| Артефакт | Ключевая проверка | Статус |
|----------|------------------|--------|
| `scripts/sheet_helper.py` | `ALLOWED_TYPES` содержит `"скрыт"` (стр.42); `hidden_i` (стр.231); наложение правки (стр.278); ключ `"hidden"` в словаре (стр.289) | SUBSTANTIVE |
| `scripts/upload.py` | `ALLOWED_TYPES` содержит `"скрыт"` (стр.503); разворот в `p["hidden"]` (стр.608); `"Скрыт"` в header (стр.818); `p.get("hidden","")` в rows.append (стр.852); fallback `cols=len(rows[0]) if rows else 12` (стр.949) | SUBSTANTIVE |
| `lib/types.ts` | Поле `hidden?: boolean` с комментарием «колонка L — «Скрыт»» (стр.14) | SUBSTANTIVE |
| `lib/sheets.ts` | Диапазон `Товары!A2:L` (стр.18); `cache:"no-store"` (стр.24); маппинг `hidden: row[11] === "1"` (стр.47); фильтр `products.filter((p) => !p.hidden)` (стр.88) | SUBSTANTIVE |
| `uploader/admin.py` | `SAVE_ALLOWED_TYPES` содержит `"скрыт"` (стр.228); исключение пустого значения `not in ("photo","badge","скрыт")` (стр.237); `.pcard-eye` CSS (стр.788); `.pcard.hidden` (стр.801); `toggleHidden` с откатом (стр.1319); `filteredProducts` ветка `activeFilter === "hidden"` (стр.1050); вкладка `data-filter="hidden"` (стр.899) | SUBSTANTIVE |

### Уровень 3: Связность (wiring)

| Связь | Статус | Доказательство |
|-------|--------|----------------|
| `sheet_helper.py ALLOWED_TYPES` → принимает тип `скрыт` | WIRED | стр.42 + стр.188 — валидация при `append_edit` |
| `upload.py apply_edit_memory` → колонка L в `products_to_rows` | WIRED | стр.608: `p["hidden"]=edit["скрыт"]`; стр.852: `p.get("hidden","")` 12-м элементом |
| `uploader/admin.py /save` → `sheet_helper append_edit` | WIRED | стр.237: кортеж исключений; стр.228: `SAVE_ALLOWED_TYPES`; путь записи переиспользован |
| `toggleHidden` → `apiCall` → `/save type="скрыт"` | WIRED | стр.1349: `body: JSON.stringify({ key: p.name, type: "скрыт", value: next ? "1" : "" })` |
| `lib/sheets.ts getProducts` → фильтр перед return | WIRED | стр.88: `return products.filter((p) => !p.hidden)` — после fallback-блока structure_map |
| `app/catalog/[secret]/page.tsx` → `force-dynamic` | WIRED | стр.8: `export const dynamic = "force-dynamic"` |
| `lib/sheets.ts` → `cache:"no-store"` | WIRED | стр.24: `fetch(url, { cache: "no-store" })` |

### Уровень 4: Поток данных

| Артефакт | Переменная | Источник | Реальные данные | Статус |
|----------|-----------|---------|-----------------|--------|
| `lib/sheets.ts getProducts` | `products` | Google Sheets API `Товары!A2:L` | Да — `fetch` с реальным URL из `GOOGLE_SHEETS_ID` + `GOOGLE_API_KEY` | FLOWING |
| `toggleHidden` в `admin.py` | `p.hidden` | Список товаров `sheet_helper.py list` → JSON → JS | Да — `sheet_helper load_products` читает колонку «Скрыт» из листа + накладывает правки | FLOWING |

---

## Проверка ключевых связей (Key Links из планов)

| От | До | Через | Статус | Строка кода |
|----|----|-------|--------|-------------|
| `upload.py apply_edit_memory` | `products_to_rows` колонка L | `p["hidden"]` → 12-й элемент строки | WIRED | `upload.py:608`, `upload.py:852` |
| `lib/sheets.ts getProducts` | ответ `/api/products` | `products.filter((p) => !p.hidden)` | WIRED | `lib/sheets.ts:88` |
| кнопка-глазик JS `toggleHidden` | `POST /<TOKEN>/save` | `apiCall` с `type:"скрыт"`, `value:"1"/"пусто"` | WIRED | `admin.py:1347-1350` |
| `/save` обработчик | `sheet_helper append_edit` | shell-out с `type=скрыт` | WIRED | `admin.py:237-228` (переиспользованный путь) |

---

## Критическая грабля: три белых списка

Проект задокументировал известную граблю: тип правки `скрыт` должен присутствовать во ВСЕХ ТРЁХ белых списках.

| Файл | Белый список | Значение | Статус |
|------|-------------|---------|--------|
| `scripts/sheet_helper.py:42` | `ALLOWED_TYPES` | `"скрыт"` | PRESENT |
| `scripts/upload.py:503` | `ALLOWED_TYPES` | `"скрыт"` | PRESENT |
| `uploader/admin.py:228` | `SAVE_ALLOWED_TYPES` | `"скрыт"` | PRESENT |

Все три белых списка закрыты. Грабля не реализовалась.

---

## Кэш-починка (gap, закрытый в плане 04)

Проблема, выявленная при боевой проверке владельцем: скрытие не отражалось на витрине до 5 минут из-за двух слоёв ISR-кэша по 300 с.

| Место | До починки | После починки | Коммит |
|-------|-----------|--------------|--------|
| `lib/sheets.ts` | `next: { revalidate: 300 }` | `cache: "no-store"` | `6437674` |
| `app/catalog/[secret]/page.tsx` | `export const revalidate = 300` | `export const dynamic = "force-dynamic"` | `6437674` |
| `app/api/products/route.ts` | `revalidate = 300` удалён | остался `force-dynamic` | `6437674` |

Эта починка критична для HIDE-05: без неё скрытие появлялось только при следующем деплое.

---

## Покрытие требований

| Требование | Описание | Этап/план | Статус | Доказательство |
|-----------|---------|----------|--------|----------------|
| HIDE-01 | Кнопка-глазик для скрытия | 08-03 | SATISFIED | `toggleHidden()` + `apiCall` в `admin.py:1319-1378` |
| HIDE-02 | Возврат скрытого повторным кликом | 08-03 | SATISFIED | `value: next ? "1" : ""` + фильтр «Скрытые» в admin.py |
| HIDE-03 | Скрытая карточка визуально отличается | 08-03 | SATISFIED | `.pcard.hidden { opacity:0.45 }`, глифы 👁/🙈, чип `badge-hidden` |
| HIDE-04 | Скрытие переживает перепрогон прайсов | 08-01 | SATISFIED | `"скрыт"` в ALLOWED_TYPES обоих Python-файлов; `p["hidden"]` в `apply_edit_memory`; колонка «Скрыт» (L) |
| HIDE-05 | Скрытые товары не попадают на витрину | 08-02, 08-04 | SATISFIED | `products.filter((p) => !p.hidden)` в `lib/sheets.ts:88`; `cache:"no-store"` + `force-dynamic` |

**Покрытие: 5/5 требований HIDE-01..05 выполнены**

---

## Поведенческие проверки (Spot-checks)

| Поведение | Проверка | Результат | Статус |
|-----------|---------|---------|--------|
| `sheet_helper.py` компилируется | Присутствие `"скрыт"` в `ALLOWED_TYPES` | Grep: строка 42 — FOUND | PASS |
| `upload.py` компилируется | `"скрыт"` в ALLOWED_TYPES, `"Скрыт"` в header | Grep: строки 503, 818, 852 — FOUND | PASS |
| `admin.py` компилируется | `SAVE_ALLOWED_TYPES` + `toggleHidden` + `.pcard.hidden` | Grep: строки 228, 801, 1319 — FOUND | PASS |
| `lib/sheets.ts` диапазон | `A2:L` (не устаревший `A2:K`) | Grep: строка 18 — `Товары!A2:L` FOUND | PASS |
| Фильтр скрытых — последняя операция | `filter` после fallback-блока | `lib/sheets.ts:88` — после строк 54-83 | PASS |
| Кэш отключён | `no-store` + `force-dynamic` везде | `lib/sheets.ts:24`, `page.tsx:8`, `route.ts:4` — FOUND | PASS |
| Все три белых списка | `"скрыт"` присутствует в каждом | `sheet_helper.py:42`, `upload.py:503`, `admin.py:228` — FOUND | PASS |
| Боевой прогон | 807 товаров, 12 колонок в листе, цикл скрыть/вернуть подтверждён владельцем | SUMMARY 08-04: подтверждено владельцем | PASS |

---

## Антипаттерны

При проверке изменённых файлов (`sheet_helper.py`, `upload.py`, `lib/types.ts`, `lib/sheets.ts`, `uploader/admin.py`, `app/catalog/[secret]/page.tsx`, `app/api/products/route.ts`) антипаттернов не обнаружено:

- Нет маркеров `TBD`, `FIXME`, `XXX`
- Нет заглушек `return null`, `return []` без логики
- Нет пустых обработчиков (`onClick={() => {}}`)
- Все новые функции содержат реальную логику (toggleHidden с откатом, filter в getProducts, разворот правки в apply_edit_memory)

---

## Что НЕ попало в этот этап (корректно отложено)

Десктопный вид витрины (DESK-01..04) — это этап 9, отдельная веха. Требования v1.2 в части скрытия (HIDE-01..05) закрыты полностью.

---

## Сводка

Цель этапа 8 достигнута полностью. Все пять критериев успеха из ROADMAP.md подтверждены в коде:

1. Три белых списка (`sheet_helper.py`, `upload.py`, `admin.py`) содержат тип `"скрыт"` — известная грабля закрыта.
2. Колонка «Скрыт» (L) добавлена по паттерну expand-contract — старые колонки не сдвинуты.
3. Фильтрация скрытых — строго на сервере (`lib/sheets.ts:88`), до отдачи в браузер.
4. Кэш отключён (`no-store` + `force-dynamic`) — скрытие отражается на витрине сразу после «Применить сейчас», без деплоя.
5. Боевая проверка: 8-шаговый чек-лист пройден владельцем в проде (коммит `6437674` — gap-fix кэша закрыт по результатам проверки).

---

_Проверено: 2026-06-11_
_Верификатор: Claude (gsd-verifier)_
