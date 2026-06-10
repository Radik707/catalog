# Phase 8: Скрытие товаров «глазиком» — Pattern Map

**Mapped:** 2026-06-10
**Files analyzed:** 6 (5 изменяемых + 0 новых; UI-блоки внутри существующих файлов)
**Analogs found:** 6 / 6 (все — точные, так как этап 7 реализовал тот же механизм для типа `подгруппа`)

> Главный образец всего этапа — **тип правки `подгруппа` (этап 7)**. Новый тип `скрыт`
> воспроизводит его один-в-один: те же три белых списка, та же expand-contract колонка
> в конец строки Sheet, тот же оптимистичный путь `/save` в админ-панели. Где это
> возможно, ближайший аналог для типа `скрыт` — это `badge` (булева/снимаемая правка
> с разрешённым пустым значением), а для колонки Sheet и фильтрации — `подгруппа`/`section`.

---

## File Classification

| Изменяемый файл | Роль | Поток данных | Ближайший аналог | Качество |
|-----------------|------|--------------|------------------|----------|
| `scripts/sheet_helper.py` | data-layer / config | CRUD (read sheet, append edit) | тип `подгруппа` в `ALLOWED_TYPES` + `load_products` | exact |
| `scripts/upload.py` | service / batch | transform (правки → строки Sheet) | `apply_edit_memory` ветка `подгруппа` + колонки «Подгруппа/Раздел» в `products_to_rows` | exact |
| `lib/sheets.ts` | service / model | request-response (read Sheet → Product) | маппинг `subgroup`/`section` (колонки J/K) | exact |
| `lib/types.ts` | model | — | поля `subgroup?`/`section?` в `Product` | exact |
| `uploader/admin.py` (Python /save) | controller | request-response | `SAVE_ALLOWED_TYPES` + обработчик `/save` (ветка `badge`) | exact |
| `uploader/admin.py` (встроенный JS/CSS) | component | event-driven (клик → optimistic save) | `.pcard-edit-photo` (оверлей на фото) + `toggleBadge` (optimistic toggle) + `filteredProducts` (фильтр) | exact |

---

## Shared Patterns (применяются ко всем релевантным файлам)

### SP-1. Тип правки в ТРЁХ белых списках (грабля проекта)
**Apply to:** `sheet_helper.py`, `upload.py`, `admin.py` — забыть один → правка молча пропадёт.

- `scripts/sheet_helper.py:41` — `ALLOWED_TYPES = {"group", "photo", "description", "name", "badge", "подгруппа"}` → добавить `"скрыт"`.
- `scripts/upload.py:503` — `ALLOWED_TYPES = {"group", "photo", "description", "name", "badge", "подгруппа"}` → добавить `"скрыт"`.
- `uploader/admin.py:228` — `SAVE_ALLOWED_TYPES = {"group", "name", "photo", "badge", "подгруппа"}` → добавить `"скрыт"`.

### SP-2. Пустое значение = снятие правки (как `badge`/`photo`)
**Apply to:** `admin.py` обработчик `/save`.

`uploader/admin.py:235-238` — пустое значение допускается только для перечисленных типов:
```python
# Значение обязательно для group и name; для photo и badge допустимо пустое
# (photo — сброс привязки; badge — снятие метки «без метки»)
if not value and edit_type not in ("photo", "badge"):
    return jsonify(ok=False, message="...Значение не указано."), 400
```
Для `скрыт`: `value="1"` = скрыт, `value=""` = показан → добавить `"скрыт"` в кортеж исключений: `("photo", "badge", "скрыт")`.

### SP-3. Expand-contract: новая колонка В КОНЕЦ строки Sheet
**Apply to:** `upload.py` (заголовок + строка) и `lib/sheets.ts` (диапазон + индекс).
Колонки «Подгруппа» (J) и «Раздел» (K) добавлены В КОНЕЦ, не сдвигая старые. Колонка «Скрыт» = **L (12-я)**, тем же приёмом. См. PA-2 и PA-3.

### SP-4. Оптимистичный UI с откатом при ошибке
**Apply to:** JS-обработчик глазика в `admin.py`. Образец — `toggleBadge` (PA-6): сохранить prev → применить оптимистично (`syncProduct` + перерисовка) → `apiCall /save` → при ошибке откат к prev. Без диалога подтверждения (D-06).

---

## Pattern Assignments

### `scripts/sheet_helper.py` (data-layer, CRUD)

**Аналог:** тип `подгруппа` в `ALLOWED_TYPES` и его чтение в `load_products`.

**Белый список** (`sheet_helper.py:39-41`):
```python
# --- Допустимые типы правок (белый список — защита памяти правок от мусора) ---
# «подгруппа» (этап 7) — перенос товара по двухуровневой структуре Раздел→Подгруппа.
ALLOWED_TYPES = {"group", "photo", "description", "name", "badge", "подгруппа"}
```
→ добавить `"скрыт"`. (Этот же набор переиспользуется как `choices` в CLI `--type`, `sheet_helper.py:335`.)

**Чтение ожидающей правки в карточку панели** (`sheet_helper.py:263-278`) — образец для проброса `hidden` в админ-панель: ожидающая правка перебивает значение из листа «Товары», и результат кладётся в словарь товара:
```python
# Ожидающая правка подгруппы перебивает значение из листа «Товары» (как для метки)
if key in edit_values and "подгруппа" in edit_values[key]:
    subgroup = edit_values[key]["подгруппа"]

products.append({
    "name": raw_name, "group": group, "image_url": image_url,
    "is_new": is_new, "badge": badge, "subgroup": subgroup, "section": section,
})
```
→ по образцу: прочитать колонку «Скрыт» из листа «Товары» (опциональный индекс, как `subgroup_i` на `sheet_helper.py:227`), наложить ожидающую правку `скрыт`, добавить `"hidden": hidden` в словарь товара. Для опционального индекса колонки — образец `sheet_helper.py:226-228`:
```python
subgroup_i = header.index("Подгруппа") if "Подгруппа" in header else None
section_i = header.index("Раздел") if "Раздел" in header else None
```

---

### `scripts/upload.py` (service, transform)

**Аналог:** ветка `подгруппа` в `apply_edit_memory` + колонки «Подгруппа/Раздел» в `products_to_rows`.

**Белый список в `load_edit_memory`** (`upload.py:502-503`):
```python
# Допустимые типы правок (Этап 3...; Этап 7: подгруппа)
ALLOWED_TYPES = {"group", "photo", "description", "name", "badge", "подгруппа"}
```
→ добавить `"скрыт"`.

**Разворот правки в поле товара** (`upload.py:596-604`) — для `скрыт` ближайший образец `badge` (булева/снимаемая), запись override-поля:
```python
# Правка метки (badge): ручное значение перебивает авто-определение.
# Пустая строка — явное снятие метки, её тоже сохраняем.
if "badge" in edit:
    p["badge_override"] = edit["badge"]
# Правка подгруппы (этап 7): значение разворачивается позже.
if "подгруппа" in edit:
    p["subgroup_override"] = edit["подгруппа"]
```
→ добавить: `if "скрыт" in edit: p["hidden"] = edit["скрыт"]` (значение `"1"`/`""`).

**Заголовок + новая колонка в конце строки** (`upload.py:807-846`) — паттерн expand-contract:
```python
header = [
    "Наименование", "Цена", "Остаток", "Категория",
    "Группа", "Поставщик", "Badge", "ImageUrl", "Description",
    "Подгруппа",        # новое поле этапа 5
    "Раздел",           # новое поле этапа 5
]
...
rows.append([
    displayed_name, p["price"], p["stock"], p["source_category"],
    p["display_group"], p["supplier_file"], badge, image_url, description,
    p.get("display_subgroup", ""),   # подгруппа
    p.get("display_section", ""),    # раздел
])
```
→ дописать `"Скрыт"` 12-м элементом заголовка и `p.get("hidden", "")` 12-м элементом строки. **Товар НЕ вырезать** из списка — он остаётся в «Товары» с флагом, иначе панель его не покажет и не даст вернуть (D, HIDE-02).

**Ширина листа при создании** (`upload.py:939-943`) — комментарий упоминает «11 колонок»; при создании ширина берётся из заголовка (`len(rows[0])`), так что новая колонка подхватится автоматически, но обновить комментарий/дефолт на 12:
```python
# Ширину берём из заголовка: колонок стало 11 (добавлены «Подгруппа»/«Раздел»),
worksheet = spreadsheet.add_worksheet(
    title=sheet_name, rows=len(rows) + 10, cols=len(rows[0]) if rows else 11
)
```
→ обновить число в комментарии до 12 и fallback `11` → `12`.

---

### `lib/sheets.ts` (service, request-response)

**Аналог:** чтение колонок J/K (`subgroup`/`section`) + расширение диапазона.

**Диапазон чтения** (`lib/sheets.ts:17-18`):
```typescript
// Диапазон расширен до A2:K для чтения колонок «Подгруппа» (J) и «Раздел» (K)
const range = encodeURIComponent("Товары!A2:K");
```
→ `A2:K` → `A2:L`.

**Маппинг строки в Product** (`lib/sheets.ts:31-44`):
```typescript
const products: Product[] = rows.map((row, index) => ({
  id: String(index + 1),
  name: row[0] || "",
  ...
  subgroup: row[9] || undefined,  // J — «Подгруппа»
  section: row[10] || undefined,  // K — «Раздел»
}));
```
→ добавить `hidden: row[11] === "1"` (L — «Скрыт»).

**Фильтрация скрытых на сервере** (HIDE-05): отфильтровать перед `return products;` (`lib/sheets.ts:81`). Делать это на сервере, скрытые товары не отдавать в браузер вообще:
```typescript
return products.filter((p) => !p.hidden);
```
**Грабля:** учесть fallback-блок `lib/sheets.ts:50-79` (восстановление section по `structure_map`) — он работает с тем же массивом `products`; фильтр по `hidden` должен применяться к итоговому результату (после сортировки), чтобы не сломать сортировку и fallback.

---

### `lib/types.ts` (model)

**Аналог:** опциональные поля `subgroup?`/`section?`.

`lib/types.ts:12-13`:
```typescript
subgroup?: string;     // колонка J — «Подгруппа» (двухуровневая навигация)
section?: string;      // колонка K — «Раздел» (верхний уровень навигации)
```
→ добавить:
```typescript
hidden?: boolean;      // колонка L — «Скрыт» (1 = скрыт с витрины)
```

---

### `uploader/admin.py` — обработчик `/save` (controller, request-response)

**Аналог:** существующий `/save` (ветка `badge`).

**Белый список** (`admin.py:227-228`):
```python
# Белый список типов правок: group + name + photo + badge + подгруппа (этап 7, T-04-02)
SAVE_ALLOWED_TYPES = {"group", "name", "photo", "badge", "подгруппа"}
```
→ добавить `"скрыт"`.

**Разрешить пустое значение** (`admin.py:235-238`) — см. SP-2:
```python
if not value and edit_type not in ("photo", "badge"):
    return jsonify(ok=False, message="...Значение не указано."), 400
```
→ `("photo", "badge", "скрыт")`.

Остальной путь записи (`admin.py:240-278`: нормализация ключа на сервере → shell-out `sheet_helper append_edit` → graceful 500) переиспользуется БЕЗ изменений — он типонезависим.

---

### `uploader/admin.py` — встроенный JS/CSS (component, event-driven)

**Аналог 1 — оверлей-кнопка на фото** (`.pcard-edit-photo`). CSS `admin.py:771-783`:
```css
.pcard-photo { position: relative; }
.pcard-edit-photo {
  position: absolute; top: 4px; right: 4px;
  width: 40px; height: 40px; min-width: 40px;
  display: flex; align-items: center; justify-content: center;
  border: 0; border-radius: 8px; cursor: pointer;
  background: rgba(255,255,255,0.85); color: #374151; font-size: 18px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.18); padding: 0; line-height: 1;
}
.pcard-edit-photo:hover { background: #fff; }
.view-grid.density-s .pcard-edit-photo { width: 34px; height: 34px; min-width: 34px; font-size: 15px; }
```
→ кнопка-глазик `.pcard-eye` строится по этому образцу: `position:absolute` в правом верхнем углу фото (D-04). У `.pcard-edit-photo` уже занят `right:4px` — глазик ставить, например, `top:4px; left:4px` (левый верхний) или сдвинуть по `right`, чтобы не перекрывать карандаш. Тач-цель ≥44px (D-05) — у образца 40px, увеличить до 44 для глазика; компактный вариант для `density-s` по образцу последней строки.

**Аналог 2 — рендер оверлея в `buildCard`** (`admin.py:1082-1084` + вставка `admin.py:1132`):
```javascript
const editPhotoBtn = p.image_url
  ? `<button class="pcard-edit-photo" type="button" title="Кадрировать фото">&#9998;</button>` : "";
...
<div class="pcard-photo">${photoHtml}${editPhotoBtn}</div>
```
→ добавить рядом кнопку-глазик в `.pcard-photo`. Глифы (D-Discretion): открытый глаз `&#128065;` (👁, виден → клик скрыть) / перечёркнутый `&#128584;` (🙈) или 🚫 (скрыт → клик вернуть). Класс карточки при `p.hidden` — `pcard hidden` (см. ниже PA CSS).

**Аналог 3 — оптимистичный toggle с откатом** (`admin.py:1221-1254`, `toggleBadge`) — ПРЯМОЙ образец логики глазика:
```javascript
async function toggleBadge(targetBadge) {
  const prev = p.badge;                          // запомнить для отката
  const newBadge = (p.badge === targetBadge) ? "" : targetBadge;
  saveScrollPos();
  p.badge = newBadge; syncProduct(p); paintBadges();   // оптимистично
  btnNew.disabled = true; btnHit.disabled = true;
  cardStatus("", "Сохраняем...");
  const d = await apiCall(`/${TOKEN}/save`, {
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key: p.name, type: "badge", value: newBadge }),
  });
  if (d && d.ok) { cardStatus("ok", "..."); toast("ok", "..."); }
  else { p.badge = prev; syncProduct(p); paintBadges(); cardStatus("err","..."); toast("err", ...); } // откат
}
```
→ `toggleHidden`: `const prev = p.hidden; const next = !p.hidden;` → оптимистично `p.hidden = next; syncProduct(p);` + переключить класс `card.classList.toggle("hidden", next)` и сменить глиф → `apiCall /save` с `type:"скрыт", value: next ? "1" : ""` → при ошибке откат к `prev`. БЕЗ подтверждения (D-06).

**Аналог 4 — стиль «тусклой» карточки + чип** — образцы из существующего CSS:
- `.badge-attn` (чип-индикатор в углу, `admin.py:631` секция `.pcard-badges`) — образец для текстового чипа «скрыт» (D-02).
- Для класса `.pcard.hidden` (D-01, opacity ~0.45) аналога точно нет — добавить новое правило `.pcard.hidden { opacity: 0.45; }` (карточка остаётся интерактивной — НЕ `pointer-events:none`).

**Аналог 5 — клиентский фильтр видимости** (D-08/D-09) — `filteredProducts` (`admin.py:1018-1031`):
```javascript
function filteredProducts() {
  const query = document.getElementById("search-input").value.trim().toLowerCase();
  return allProducts.filter(p => {
    let matchFilter;
    if (activeFilter === "attention")     matchFilter = needsAttention(p);
    else if (activeFilter === "new")      matchFilter = (p.badge === "новинка");
    else if (activeFilter === "nogroup")  matchFilter = !p.group;
    else if (activeFilter === "nophoto")  matchFilter = !p.image_url;
    else                                  matchFilter = true;
    const matchSearch = (query === "" || (p.name || "").toLowerCase().includes(query));
    return matchFilter && matchSearch;
  });
}
```
→ добавить ветки фильтра видимости. Образец вкладок — `filter-tabs` HTML (`admin.py:872-877`):
```html
<div class="filter-tabs" id="filter-tabs">
  <button class="filter-tab" data-filter="attention">Требуют внимания</button>
  ...
  <button class="filter-tab active" data-filter="all">Все</button>
</div>
```
→ добавить вкладку(и) видимости (например `data-filter="hidden"` → только скрытые). Фильтр клиентский, совместно с поиском (`matchFilter && matchSearch` уже это даёт — D-09). Обработчик переключения вкладок — `admin.py:1877-1882` (без изменений в механике). **Важно:** по умолчанию (`activeFilter="all"`, `admin.py:945`) показывать ВСЕ товары, скрытые — тусклыми (D-08), поэтому ветка `all` НЕ должна отфильтровывать скрытые.

**Вспомогательные helpers (переиспользовать как есть):**
- `apiCall` (`admin.py:1001-1008`) — POST + JSON + graceful null.
- `syncProduct` (`admin.py:1278-1281`) — синхронизация изменённого товара в `allProducts`.
- `esc` (`admin.py:976`), `toast` (`admin.py:984`), `saveScrollPos` (`admin.py:1800`).

---

## No Analog Found

| Артефакт | Роль | Причина |
|----------|------|---------|
| CSS `.pcard.hidden { opacity: 0.45 }` | стиль состояния | В панели нет «выключенного» состояния карточки — новое правило (D-01), значение opacity на усмотрение исполнителя. |
| Глифы глаза 👁/🙈/🚫 | иконка | Конкретный глиф не задан (D-Discretion); метафора задана D-03. |

Всё остальное имеет точный аналог в типе `подгруппа`/`badge` (этап 7) — повторять один-в-один.

---

## Metadata

**Analog search scope:** `scripts/upload.py`, `scripts/sheet_helper.py`, `uploader/admin.py`, `lib/sheets.ts`, `lib/types.ts`, `.planning/milestones/v1.1-phases/07-1/07-01-SUMMARY.md`
**Files scanned:** 6
**Pattern extraction date:** 2026-06-10
