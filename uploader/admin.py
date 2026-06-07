"""
admin.py — Flask-модуль панели администратора каталога «Вкусный Дом».

Назначение: владелец открывает панель по секретному URL /<ADMIN_SECRET>/,
видит товары, требующие внимания, меняет группу и нажимает «Применить сейчас».

Маршруты (всё под /<admin_token>/):
  GET  /<token>/               — одностраничная HTML-панель
  GET  /<token>/products       — JSON-список товаров из Google Sheets
  POST /<token>/save           — записать правку в «Правки»
  POST /<token>/apply          — пересобрать каталог из последней партии

Авторизация: отдельная переменная ADMIN_SECRET (не APP_SECRET!) — D-02.
Интеграция: shell-out в scripts/sheet_helper.py через _run_py из app.py.
"""

import os
import sys
import hmac
import json
import logging
import threading
import subprocess
from pathlib import Path

from flask import Blueprint, request, jsonify, abort

# --- Настройка логирования ---
log = logging.getLogger("admin")

# --- Пути к вспомогательным скриптам ---
# SCRIPT_DIR — директория этого модуля (uploader/)
SCRIPT_DIR = Path(__file__).resolve().parent
# sheet_helper.py живёт в ../scripts/ относительно uploader/
SHEET_HELPER = SCRIPT_DIR.parent / "scripts" / "sheet_helper.py"


def load_env() -> None:
    """Загрузить переменные из .env в директории uploader/ (как в app.py)."""
    env_path = SCRIPT_DIR / ".env"
    if not env_path.exists():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


# Загрузить переменные при импорте модуля
load_env()

# --- Отдельный секрет панели администратора (независимо от APP_SECRET — D-02) ---
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "")

# --- Переиспользуем настройки Python и таймаута из app.py ---
PYTHON_BIN = os.environ.get("PYTHON_BIN", sys.executable)
UPLOAD_TIMEOUT = int(os.environ.get("UPLOAD_TIMEOUT", "600"))

# --- Blueprint: изолируем маршруты панели от загрузчика ---
admin_bp = Blueprint("admin", __name__)

# --- Допустимые типы правок в этом плане (расширится в 02/03) ---
# В плане 01: только 'group'; name/photo добавятся в планах 02/03
PLAN_01_ALLOWED_TYPES = {"group"}

# ── Строки групп для выпадающего списка (11 базовых + служебные) ──
GROUPS = [
    "Напитки",
    "Энергетики",
    "Батончики и шоколад",
    "Чай и кофе",
    "Снэки",
    "Детское",
    "Лапша и каши",
    "Стоевъ и Сэнсой",
    "Соусы и специи",
    "Консервация",
    "Конфеты и печенье",
    "Прикассовое",
    "Коробочные конфеты",
    "Крупы и бакалея",
    "Новинки",
    "Другое",
]


def check_admin(token: str) -> None:
    """Проверить секрет панели администратора.

    Использует hmac.compare_digest — защита от timing-атаки (T-04-01).
    При пустом ADMIN_SECRET или неверном токене → 404 (не 403 — скрываем факт существования).
    Отдельный ADMIN_SECRET — независимо от APP_SECRET загрузчика (D-02).
    """
    if not ADMIN_SECRET or not hmac.compare_digest(token, ADMIN_SECRET):
        abort(404)


def _run_py(script: Path, *args) -> tuple:
    """Запустить python-скрипт, вернуть (код возврата, объединённый вывод).

    Переиспользует тот же паттерн что _run_py из app.py (строки 286–295).
    cwd=script.parent гарантирует доступ к category_map.json и .env скрипта.
    """
    proc = subprocess.run(
        [PYTHON_BIN, str(script), *args],
        cwd=str(script.parent),   # чтобы нашлись category_map.json, .env и т.п.
        capture_output=True,
        text=False,               # бинарный вывод — обрабатываем как UTF-8
        timeout=UPLOAD_TIMEOUT,
    )
    stdout = (proc.stdout or b"").decode("utf-8", errors="replace")
    stderr = (proc.stderr or b"").decode("utf-8", errors="replace")
    return proc.returncode, stdout + stderr


# ── Маршруты панели ──

@admin_bp.get("/<token>/")
def admin_index(token: str):
    """Главная страница панели — отдать одностраничный HTML."""
    check_admin(token)
    return PAGE.replace("__TOKEN__", token)


@admin_bp.get("/<token>/products")
def admin_products(token: str):
    """Список товаров из Google Sheets → JSON.

    Вызывает sheet_helper.py list через shell-out.
    При ошибке (нет credentials / сеть недоступна) → пустой список.
    """
    check_admin(token)
    try:
        rc, output = _run_py(SHEET_HELPER, "list")
    except subprocess.TimeoutExpired:
        log.warning("sheet_helper list: таймаут")
        return jsonify(products=[])
    except Exception as e:
        log.warning("sheet_helper list: ошибка запуска: %s", e)
        return jsonify(products=[])

    if rc != 0:
        log.warning("sheet_helper list rc=%d: %s", rc, output.strip()[-200:])
        return jsonify(products=[])

    # Парсим JSON из stdout (stderr уже отфильтрован в output при rc=0)
    try:
        # stdout может содержать строки лога (stderr) + JSON — берём последнюю строку
        lines = [l.strip() for l in output.strip().splitlines() if l.strip().startswith("[")]
        json_line = lines[-1] if lines else "[]"
        products = json.loads(json_line)
    except (json.JSONDecodeError, IndexError) as e:
        log.warning("sheet_helper list: не удалось распарсить JSON: %s", e)
        products = []

    return jsonify(products=products)


@admin_bp.post("/<token>/save")
def admin_save(token: str):
    """Сохранить правку товара во вкладку «Правки».

    Принимает JSON: {key: str, type: str, value: str}
    В плане 01: принимает только type="group" (белый список PLAN_01_ALLOWED_TYPES).
    rc=0 → 200 + {ok: true}; rc!=0 → 500 + {ok: false}.
    Технические детали — только в log, клиенту нейтральное сообщение (T-04-04).
    """
    check_admin(token)

    data = request.get_json(silent=True) or {}
    key = str(data.get("key", "")).strip()
    edit_type = str(data.get("type", "")).strip()
    value = str(data.get("value", "")).strip()

    # --- Валидация входных данных ---
    if not key:
        return jsonify(ok=False, message="Не удалось сохранить правку. Ключ товара не указан."), 400

    # Белый список типов правок — в этом плане только group (T-04-02)
    if edit_type not in PLAN_01_ALLOWED_TYPES:
        return jsonify(
            ok=False,
            message="Не удалось сохранить правку. Неподдерживаемый тип правки.",
        ), 400

    if not value:
        return jsonify(ok=False, message="Не удалось сохранить правку. Значение не указано."), 400

    # --- Запись через sheet_helper append_edit ---
    try:
        rc, output = _run_py(
            SHEET_HELPER,
            "append_edit",
            "--key", key,
            "--type", edit_type,
            "--value", value,
        )
    except subprocess.TimeoutExpired:
        log.warning("admin /save: таймаут shell-out в sheet_helper")
        return jsonify(
            ok=False,
            message="Не удалось сохранить правку. Проверьте соединение и попробуйте ещё раз.",
        ), 500
    except Exception as e:
        log.warning("admin /save: ошибка запуска sheet_helper: %s", e)
        return jsonify(
            ok=False,
            message="Не удалось сохранить правку. Проверьте соединение и попробуйте ещё раз.",
        ), 500

    if rc != 0:
        # Технические детали — только в log
        log.warning("sheet_helper append_edit rc=%d: %s", rc, output.strip()[-300:])
        return jsonify(
            ok=False,
            message="Не удалось сохранить правку. Проверьте соединение и попробуйте ещё раз.",
        ), 500

    return jsonify(
        ok=True,
        message="Правка сохранена. Она применится автоматически при следующем обновлении прайса или нажмите «Применить сейчас».",
    )


@admin_bp.post("/<token>/apply")
def admin_apply(token: str):
    """Пересобрать каталог из последней загруженной партии.

    Переиспользует PROCESS_LOCK и LAST_BATCH_DIR из app.py — те же объекты.
    Защита от двойного запуска через PROCESS_LOCK.acquire(blocking=False) (T-04-03).
    При отсутствии последней партии — понятное сообщение без запуска обработки.
    """
    check_admin(token)

    # --- Импортируем общие объекты из app.py (избегаем дублирования замка) ---
    try:
        from app import PROCESS_LOCK, LAST_BATCH_DIR, run_upload
    except ImportError as e:
        log.error("admin /apply: не удалось импортировать из app.py: %s", e)
        return jsonify(
            ok=False,
            message="Не удалось запустить обновление. Ошибка конфигурации сервера.",
        ), 500

    # --- Проверяем наличие последней партии прайсов ---
    import glob as _glob
    last_batch_files = _glob.glob(str(LAST_BATCH_DIR / "*.xlsx"))
    if not last_batch_files:
        return jsonify(
            ok=False,
            message="Прайсы ещё не загружались. Загрузите файлы через страницу загрузчика.",
        )

    # --- Защита от двойного запуска (T-04-03) ---
    if not PROCESS_LOCK.acquire(blocking=False):
        return jsonify(
            ok=False,
            message="Обновление уже идёт...",
        )

    # Замок захвачен — запускаем пересборку в фоновом потоке
    def _apply_async():
        """Фоновая пересборка каталога. Замок освобождается в finally."""
        try:
            ok, err, count = run_upload()
            if ok:
                log.info("admin /apply: каталог успешно пересобран, %s товаров", count)
            else:
                log.warning("admin /apply: пересборка не удалась: %s", err)
        except Exception as exc:
            log.exception("admin /apply: необработанное исключение: %s", exc)
        finally:
            # Замок освобождается всегда — даже при исключении
            PROCESS_LOCK.release()

    try:
        thread = threading.Thread(target=_apply_async, daemon=True)
        thread.start()
    except Exception as exc:
        # Поток не стартовал — освобождаем замок сами
        PROCESS_LOCK.release()
        log.exception("admin /apply: не удалось запустить фоновый поток: %s", exc)
        return jsonify(
            ok=False,
            message="Не удалось запустить обновление. Попробуйте ещё раз.",
        ), 500

    # Немедленный ответ — владелец не ждёт выполнения
    return jsonify(
        ok=True,
        message="Запущено обновление каталога. Сайт обновится через 3–5 минут.",
    )


# ── Одностраничный HTML (PAGE) ──
# Структура: Tabler CSS из CDN (только стили, без JS), mobile-first, container-sm 640px.
# Экран 1: список товаров с фильтрами и поиском.
# Экран 2: правка товара (группа).
# Тексты строго из копирайтинг-контракта UI-SPEC.
PAGE = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Вкусный Дом — Панель управления</title>
<!-- Tabler CSS подключается только как стили (без JS-рисков из CDN) — D-03 -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/core@1.0.0-beta21/dist/css/tabler.min.css">
<style>
  /* Базовые переопределения, совместимые с загрузчиком */
  body { background: #f3f4f6; }
  /* Статусный баннер — наследуем из загрузчика (uploader/app.py) */
  .status { margin-top: 16px; padding: 14px; border-radius: 12px; font-size: 14px;
            white-space: pre-wrap; display: none; }
  .status.ok   { background: #ecfdf5; color: #065f46; display: block; }
  .status.err  { background: #fef2f2; color: #991b1b; display: block; }
  .status.info { background: #eff6ff; color: #1e40af; display: block; }
  /* Карточка товара — кликабельна для перехода к экрану правки */
  .product-card { cursor: pointer; transition: box-shadow 0.15s; }
  .product-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.10); }
  /* Кнопка «Применить сейчас» — min-height 48px для удобного нажатия с телефона */
  .btn-apply { min-height: 48px; font-size: 16px; font-weight: 600; }
  /* Вкладки-фильтры */
  .filter-tabs { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
  .filter-tab  { padding: 6px 12px; border-radius: 8px; border: 1px solid #d1d5db;
                 background: #fff; cursor: pointer; font-size: 14px; color: #374151; }
  .filter-tab.active { background: #2563eb; color: #fff; border-color: #2563eb; }
  /* Пустое состояние */
  .empty-state { text-align: center; padding: 48px 16px; color: #6b7280; }
  .empty-state h3 { margin: 0 0 8px; color: #374151; font-size: 16px; }
  /* Экран 2 (правка) — скрыт по умолчанию */
  #screen-edit { display: none; }
</style>
</head>
<body>
<div class="container-sm py-3">

  <!-- ── Экран 1: Список товаров ── -->
  <div id="screen-list">
    <div class="mb-3">
      <h1 class="h3 mb-0">Вкусный Дом — Панель управления</h1>
      <p class="text-muted mb-0" style="font-size:14px">Товары и правки</p>
    </div>

    <!-- Поиск по названию -->
    <div class="mb-3">
      <input id="search-input" class="form-control" type="search"
             placeholder="Поиск по названию..." autocomplete="off">
    </div>

    <!-- Вкладки-фильтры -->
    <div class="filter-tabs" id="filter-tabs">
      <button class="filter-tab active" data-filter="attention">Требуют внимания</button>
      <button class="filter-tab" data-filter="new">Новинки</button>
      <button class="filter-tab" data-filter="nogroup">Без группы</button>
      <button class="filter-tab" data-filter="nophoto">Без фото</button>
      <button class="filter-tab" data-filter="all">Все</button>
    </div>

    <!-- Список карточек товаров -->
    <div id="products-list"></div>

    <!-- Статусный баннер -->
    <div id="status" class="status"></div>

    <!-- Кнопка «Применить сейчас» — фиксирована внизу -->
    <div class="mt-4">
      <button id="btn-apply" class="btn btn-primary w-100 btn-apply"
              onclick="applyNow()">
        Применить сейчас
      </button>
    </div>
  </div>

  <!-- ── Экран 2: Правка товара ── -->
  <div id="screen-edit">
    <div class="mb-3">
      <button class="btn btn-ghost" onclick="showList()">← Назад к списку</button>
    </div>

    <div class="card">
      <div class="card-body">
        <div class="mb-3">
          <label class="form-label text-muted" style="font-size:14px">Название (из прайса):</label>
          <div id="edit-name-display" class="fw-semibold" style="font-size:16px"></div>
        </div>

        <div class="mb-3">
          <label class="form-label" for="edit-group">Группа</label>
          <select id="edit-group" class="form-select">
            <option value="">Выберите группу...</option>
            <option>Напитки</option>
            <option>Энергетики</option>
            <option>Батончики и шоколад</option>
            <option>Чай и кофе</option>
            <option>Снэки</option>
            <option>Детское</option>
            <option>Лапша и каши</option>
            <option>Стоевъ и Сэнсой</option>
            <option>Соусы и специи</option>
            <option>Консервация</option>
            <option>Конфеты и печенье</option>
            <option>Прикассовое</option>
            <option>Коробочные конфеты</option>
            <option>Крупы и бакалея</option>
            <option>Новинки</option>
            <option>Другое</option>
          </select>
        </div>

        <div id="status-edit" class="status"></div>

        <button id="btn-save" class="btn btn-primary w-100" style="min-height:48px;font-size:16px"
                onclick="saveEdit()" disabled>
          Сохранить правку
        </button>
      </div>
    </div>
  </div>

</div><!-- /container-sm -->

<script>
/* ── Константы и состояние ── */
const TOKEN = "__TOKEN__";
// Текущий выбранный товар (для экрана правки)
let currentProduct = null;
// Полный список товаров (загружается один раз)
let allProducts = [];
// Текущий активный фильтр
let activeFilter = "attention";
// Таймер живого поиска (debounce 300ms)
let searchTimer = null;

/* ── Утилиты ── */

// Экранирование для безопасной вставки в innerHTML — защита от XSS (T-04-05)
function esc(s) {
  return String(s).replace(/[&<>"']/g, c => (
    { '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]
  ));
}

// Показать статусный баннер; kind = "ok" | "err" | "info"
function show(kind, text) {
  const el = document.getElementById("status");
  el.className = "status " + kind;
  el.textContent = text;
}

function showEdit(kind, text) {
  const el = document.getElementById("status-edit");
  el.className = "status " + kind;
  el.textContent = text;
}

// Обёртка fetch с JSON — возвращает данные или null при ошибке сети
async function apiCall(url, opts) {
  try {
    const r = await fetch(url, { method: "POST", ...opts });
    const d = await r.json();
    return d;
  } catch (e) {
    return null;
  }
}

/* ── Навигация между экранами ── */

function showList() {
  document.getElementById("screen-list").style.display = "";
  document.getElementById("screen-edit").style.display = "none";
  currentProduct = null;
}

function showEditScreen(product) {
  currentProduct = product;
  // Заполняем поля экрана правки
  document.getElementById("edit-name-display").textContent = product.name;
  const sel = document.getElementById("edit-group");
  // Предвыбрать текущую группу из каталога (если есть)
  sel.value = product.group || "";
  // Сброс статуса и кнопки
  document.getElementById("status-edit").className = "status";
  document.getElementById("status-edit").textContent = "";
  document.getElementById("btn-save").disabled = true;
  // Переключить экран
  document.getElementById("screen-list").style.display = "none";
  document.getElementById("screen-edit").style.display = "";
  // Слушатель изменения группы — активирует кнопку «Сохранить правку»
  sel.onchange = () => {
    document.getElementById("btn-save").disabled = (sel.value === "");
  };
}

/* ── Фильтрация и поиск ── */

// Карточка «требует внимания» если: новинка ИЛИ нет группы ИЛИ нет фото
function needsAttention(p) {
  return p.is_new || !p.group || !p.image_url;
}

// Применить фильтр вкладки и поисковый запрос к списку карточек
function applyFilters() {
  const query = document.getElementById("search-input").value.trim().toLowerCase();
  const cards = document.querySelectorAll(".product-card");
  let visibleCount = 0;

  cards.forEach(card => {
    const name = (card.dataset.name || "").toLowerCase();
    const group = (card.dataset.group || "");
    const image = (card.dataset.image || "");
    const isNew = card.dataset.isnew === "true";

    // Фильтр по вкладке
    let matchFilter = false;
    if (activeFilter === "attention") matchFilter = (isNew || !group || !image);
    else if (activeFilter === "new")  matchFilter = isNew;
    else if (activeFilter === "nogroup") matchFilter = !group;
    else if (activeFilter === "nophoto") matchFilter = !image;
    else matchFilter = true; // "all"

    // Фильтр по поиску
    const matchSearch = (query === "" || name.includes(query));

    const visible = matchFilter && matchSearch;
    card.style.display = visible ? "" : "none";
    if (visible) visibleCount++;
  });

  // Показать пустое состояние если нет видимых карточек
  renderEmptyState(visibleCount);
}

function renderEmptyState(visibleCount) {
  const container = document.getElementById("products-list");
  let emptyEl = document.getElementById("empty-state");
  if (visibleCount === 0) {
    if (!emptyEl) {
      emptyEl = document.createElement("div");
      emptyEl.id = "empty-state";
      emptyEl.className = "empty-state";
      container.appendChild(emptyEl);
    }
    if (activeFilter === "attention") {
      emptyEl.innerHTML = '<h3>Все товары в порядке</h3>' +
        '<p>Новых товаров без группы или фото нет. Можно применить правки или подождать следующего прайса.</p>';
    } else {
      emptyEl.innerHTML = '<h3>Товары не найдены по этому фильтру</h3>';
    }
    emptyEl.style.display = "";
  } else {
    if (emptyEl) emptyEl.style.display = "none";
  }
}

/* ── Рендер списка товаров ── */

function renderProducts(products) {
  const container = document.getElementById("products-list");
  container.innerHTML = "";

  if (!products || products.length === 0) {
    container.innerHTML = '<div class="empty-state"><h3>Все товары в порядке</h3>' +
      '<p>Новых товаров без группы или фото нет. Можно применить правки или подождать следующего прайса.</p></div>';
    return;
  }

  products.forEach(p => {
    const card = document.createElement("div");
    card.className = "card mb-2 product-card";
    // data-атрибуты для фильтрации (esc защищает от XSS в data-атрибутах тоже)
    card.dataset.name = (p.name || "").toLowerCase();
    card.dataset.group = p.group || "";
    card.dataset.image = p.image_url || "";
    card.dataset.isnew = p.is_new ? "true" : "false";
    card.dataset.productJson = JSON.stringify(p); // для передачи в showEditScreen

    // Бейджи статуса товара
    let badges = "";
    if (p.is_new || !p.group || !p.image_url) {
      // Бейдж «!» оранжевый — требует внимания (T-04-05: esc для имён)
      badges += '<span class="badge bg-warning-lt me-1">!</span>';
    }
    if (p.is_new && p.group && p.image_url) {
      // Только новинка, всё остальное в порядке — синий бейдж «Н»
      badges += '<span class="badge bg-blue-lt me-1">Н</span>';
    }

    // Подписи статуса
    let hints = [];
    if (!p.group) hints.push("Без группы");
    if (!p.image_url) hints.push("Без фото");
    if (p.is_new) hints.push("Новинка");
    const hintsHtml = hints.length
      ? `<small class="text-muted">${esc(hints.join(' · '))}</small>`
      : "";

    card.innerHTML = `
      <div class="card-body py-2">
        <div class="d-flex align-items-start gap-2">
          <div class="flex-grow-1">
            ${badges}
            <span style="font-size:14px;font-weight:600">${esc(p.name)}</span>
            <div>${hintsHtml}</div>
          </div>
          <span class="text-muted" style="font-size:18px">›</span>
        </div>
      </div>`;

    // Клик по карточке → экран правки
    card.addEventListener("click", () => {
      try {
        showEditScreen(JSON.parse(card.dataset.productJson));
      } catch (e) {
        show("err", "Ошибка открытия товара. Обновите страницу.");
      }
    });

    container.appendChild(card);
  });

  // Применить текущий фильтр к только что отрисованным карточкам
  applyFilters();
}

/* ── Загрузка товаров ── */

async function loadProducts() {
  show("info", "Загружаем список товаров...");
  try {
    const r = await fetch(`/${TOKEN}/products`);
    const d = await r.json();
    allProducts = d.products || [];
    renderProducts(allProducts);
    // Убрать баннер «загрузка»
    document.getElementById("status").className = "status";
    document.getElementById("status").textContent = "";
  } catch (e) {
    show("err", "Не удалось загрузить товары. Проверьте соединение.");
  }
}

/* ── Сохранить правку ── */

async function saveEdit() {
  if (!currentProduct) return;
  const group = document.getElementById("edit-group").value;
  if (!group) return;

  document.getElementById("btn-save").disabled = true;
  showEdit("info", "Сохраняем правку...");

  // Нормализованный ключ вычисляем на сервере при записи — передаём сырое имя
  // На стороне sheet_helper normalize_name будет применён к --key
  // Здесь передаём нормализованный ключ: упрощённая нормализация в JS
  // (точное соответствие normalize_name из upload.py необязательно в UI —
  //  нормализация происходит в sheet_helper при записи; здесь просто ID карточки)
  const key = currentProduct.name;

  const d = await apiCall(`/${TOKEN}/save`, {
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key: key, type: "group", value: group }),
  });

  document.getElementById("btn-save").disabled = false;

  if (!d) {
    showEdit("err", "Ошибка соединения. Попробуйте ещё раз.");
    return;
  }

  showEdit(d.ok ? "ok" : "err", d.message);

  if (d.ok) {
    // Обновить карточку в памяти (чтобы фильтр отразил изменение)
    currentProduct.group = group;
    // Через 1.5 с вернуться к списку
    setTimeout(() => {
      // Обновить данные в allProducts
      const idx = allProducts.findIndex(p => p.name === currentProduct.name);
      if (idx >= 0) allProducts[idx].group = group;
      showList();
      renderProducts(allProducts);
    }, 1500);
  }
}

/* ── «Применить сейчас» ── */

async function applyNow() {
  const btn = document.getElementById("btn-apply");
  btn.disabled = true;
  show("info", "Запускаем обновление каталога...");

  const d = await apiCall(`/${TOKEN}/apply`, {});

  if (!d) {
    show("err", "Ошибка соединения. Попробуйте ещё раз.");
    btn.disabled = false;
    return;
  }

  show(d.ok ? "info" : "err", d.message);
  // Разблокировать кнопку через 30 с
  setTimeout(() => { btn.disabled = false; }, 30000);
  if (!d.ok) btn.disabled = false;
}

/* ── Вкладки-фильтры ── */

document.getElementById("filter-tabs").addEventListener("click", e => {
  const tab = e.target.closest(".filter-tab");
  if (!tab) return;
  document.querySelectorAll(".filter-tab").forEach(t => t.classList.remove("active"));
  tab.classList.add("active");
  activeFilter = tab.dataset.filter;
  applyFilters();
});

/* ── Живой поиск с debounce 300ms ── */

document.getElementById("search-input").addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => applyFilters(), 300);
});

/* ── Инициализация ── */
loadProducts();
</script>
</body>
</html>"""
