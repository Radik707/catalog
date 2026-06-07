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
import tempfile
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
# cloudinary_helper.py — рядом с sheet_helper.py в scripts/
CLOUDINARY_HELPER = SCRIPT_DIR.parent / "scripts" / "cloudinary_helper.py"


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

# --- Допустимые типы правок: план 02 добавил 'name' к 'group' (D-05, D-07); план 03 photo ---
# D-07: цена сознательно НЕ редактируется в панели
PLAN_02_ALLOWED_TYPES = {"group", "name"}

# Допустимые расширения и MIME-типы для загрузки фото (T-04-09)
ALLOWED_PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_PHOTO_MIMES = {"image/jpeg", "image/png", "image/webp"}
# Максимальный размер фото — 10 МБ (T-04-09, T-04-10)
MAX_PHOTO_BYTES = 10 * 1024 * 1024


def normalize_name(name: str) -> str:
    """Нормализовать название — ключ сопоставления (копия из upload.py, без зависимостей).

    Убирает хвостовую единицу (шт/кг/упак), переводит в нижний регистр, сжимает пробелы.
    Используется в /save для вычисления ключа правки на сервере (D-05).
    """
    import re as _re
    clean = _re.sub(r",\s*[А-Яа-яA-Za-z.]+\s*$", "", name).strip()
    return _re.sub(r"\s+", " ", clean).strip().lower()

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
    Планы 01-03: принимает type="group", "name", "photo" (план 03 — сброс фото пустым значением).
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

    # Белый список типов правок: group + name + photo (план 03: photo-сброс, T-04-02, T-04-07)
    SAVE_ALLOWED_TYPES = {"group", "name", "photo"}
    if edit_type not in SAVE_ALLOWED_TYPES:
        return jsonify(
            ok=False,
            message="Не удалось сохранить правку. Неподдерживаемый тип правки.",
        ), 400

    # Значение обязательно для group и name; для photo допустимо пустое (сброс привязки)
    if not value and edit_type != "photo":
        return jsonify(ok=False, message="Не удалось сохранить правку. Значение не указано."), 400

    # --- Нормализация ключа на сервере (D-05) ---
    # Ключ правки всегда = normalize_name(имя из прайса) — независимо от типа правки.
    # Это гарантирует, что правка name не «уведёт» товар на другой ключ.
    key = normalize_name(key)

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


@admin_bp.post("/<token>/photo")
def admin_photo(token: str):
    """Загрузить фото товара в Cloudinary presenter/ и записать привязку в «Правки».

    Принимает multipart/form-data: файл photo + поле key (имя товара из прайса).
    Валидация ДО загрузки: расширение, mimetype, размер ≤ 10 МБ (T-04-09, T-04-10).
    Временный файл удаляется в finally — защита от переполнения диска (T-04-10).
    Ключи Cloudinary не попадают в ответ — только в лог (T-04-11).
    """
    check_admin(token)

    # --- Получить файл и ключ товара ---
    photo_file = request.files.get("photo")
    key = str(request.form.get("key", "")).strip()

    if not photo_file or not photo_file.filename:
        return jsonify(
            ok=False,
            message="Не удалось загрузить фото. Файл не выбран.",
        ), 400

    if not key:
        return jsonify(
            ok=False,
            message="Не удалось загрузить фото. Ключ товара не указан.",
        ), 400

    # Нормализовать ключ для записи в «Правки» (D-05)
    key = normalize_name(key)

    # Оригинальное имя файла для public_id и ref
    orig_name = photo_file.filename

    # --- Валидация расширения (T-04-09) ---
    ext = Path(orig_name).suffix.lower()
    if ext not in ALLOWED_PHOTO_EXTS:
        return jsonify(
            ok=False,
            message="Не удалось загрузить фото. Проверьте формат файла (JPG, PNG, WebP) и размер (до 10 МБ).",
        ), 400

    # --- Валидация MIME-типа (T-04-09) ---
    mime = (photo_file.mimetype or "").lower()
    if mime not in ALLOWED_PHOTO_MIMES:
        return jsonify(
            ok=False,
            message="Не удалось загрузить фото. Проверьте формат файла (JPG, PNG, WebP) и размер (до 10 МБ).",
        ), 400

    # --- Читаем файл и проверяем размер ДО сохранения на диск (T-04-09, T-04-10) ---
    file_bytes = photo_file.read()
    if len(file_bytes) > MAX_PHOTO_BYTES:
        return jsonify(
            ok=False,
            message="Не удалось загрузить фото. Проверьте формат файла (JPG, PNG, WebP) и размер (до 10 МБ).",
        ), 400

    # --- Сохранить во временный файл с безопасным суффиксом ---
    tmp_path = None
    try:
        # Суффикс берётся из проверенного расширения (только .jpg/.jpeg/.png/.webp)
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        log.info("admin /photo: временный файл %s (%d байт)", tmp_path, len(file_bytes))

        # --- Загрузить в Cloudinary через shell-out в cloudinary_helper.py ---
        try:
            rc, output = _run_py(
                CLOUDINARY_HELPER,
                "upload",
                "--path", tmp_path,
                "--name", orig_name,
            )
        except subprocess.TimeoutExpired:
            log.warning("admin /photo: таймаут загрузки в Cloudinary")
            return jsonify(
                ok=False,
                message="Не удалось загрузить фото. Проверьте соединение и попробуйте ещё раз.",
            ), 500
        except Exception as e:
            log.warning("admin /photo: ошибка запуска cloudinary_helper: %s", e)
            return jsonify(
                ok=False,
                message="Не удалось загрузить фото. Проверьте соединение и попробуйте ещё раз.",
            ), 500

        if rc != 0:
            log.warning("cloudinary_helper rc=%d: %s", rc, output.strip()[-300:])
            return jsonify(
                ok=False,
                message="Не удалось загрузить фото. Проверьте соединение и попробуйте ещё раз.",
            ), 500

        # Разобрать JSON-результат из stdout cloudinary_helper
        try:
            lines = [l.strip() for l in output.strip().splitlines() if l.strip().startswith("{")]
            json_line = lines[-1] if lines else "{}"
            cld_result = json.loads(json_line)
        except (json.JSONDecodeError, IndexError) as e:
            log.warning("admin /photo: не удалось распарсить ответ cloudinary_helper: %s", e)
            return jsonify(
                ok=False,
                message="Не удалось загрузить фото. Попробуйте ещё раз.",
            ), 500

        if not cld_result.get("ok"):
            # cloudinary_helper вернул ошибку — пробрасываем нейтральное сообщение
            log.warning("admin /photo: cloudinary_helper вернул ошибку: %s", cld_result)
            return jsonify(
                ok=False,
                message="Не удалось загрузить фото. Проверьте формат файла (JPG, PNG, WebP) и размер (до 10 МБ).",
            ), 500

        ref = cld_result["ref"]
        url = cld_result["url"]

        # --- Записать привязку photo в «Правки» через sheet_helper ---
        try:
            rc2, output2 = _run_py(
                SHEET_HELPER,
                "append_edit",
                "--key", key,
                "--type", "photo",
                "--value", ref,
            )
        except subprocess.TimeoutExpired:
            log.warning("admin /photo: таймаут записи привязки в «Правки»")
            return jsonify(
                ok=False,
                message="Фото загружено, но не удалось сохранить привязку. Попробуйте ещё раз.",
            ), 500
        except Exception as e:
            log.warning("admin /photo: ошибка sheet_helper при записи photo: %s", e)
            return jsonify(
                ok=False,
                message="Фото загружено, но не удалось сохранить привязку. Попробуйте ещё раз.",
            ), 500

        if rc2 != 0:
            log.warning("sheet_helper append_edit photo rc=%d: %s", rc2, output2.strip()[-300:])
            return jsonify(
                ok=False,
                message="Фото загружено, но не удалось сохранить привязку. Попробуйте ещё раз.",
            ), 500

        log.info("admin /photo: фото привязано key=%s ref=%s", key, ref)
        return jsonify(
            ok=True,
            ref=ref,
            url=url,
            message="Правка сохранена. Фото появится в каталоге при следующем обновлении или нажмите «Применить сейчас».",
        )

    finally:
        # Временный файл удаляется всегда — защита от переполнения диска (T-04-10)
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


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
# Экран 2: правка товара (отображаемое название + группа).
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
  /* Зона загрузки фото (Dropzone) — мобильная, min-height 80px */
  .photo-drop {
    border: 2px dashed #d1d5db; border-radius: 12px; padding: 24px;
    text-align: center; cursor: pointer; background: #f9fafb;
    transition: border-color 0.15s, background 0.15s;
  }
  .photo-drop:hover, .photo-drop.drag-over {
    border-color: #2563eb; background: #eff6ff;
  }
  .photo-drop input[type="file"] { display: none; }
  /* Превью текущего/выбранного фото */
  .photo-preview { max-height: 160px; max-width: 100%; border-radius: 8px;
                   object-fit: contain; margin-top: 12px; display: none; }
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

        <!-- Поле отображаемого названия (план 02, D-05) — пустое = использовать из прайса -->
        <div class="mb-3">
          <label class="form-label" for="edit-display-name">Отображаемое название</label>
          <input id="edit-display-name" class="form-control" type="text"
                 placeholder="Введите название для каталога..."
                 autocomplete="off">
          <div class="form-text text-muted">Оставьте пустым, чтобы использовать название из прайса</div>
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

        <!-- Зона загрузки фото (D-06): выбор с камеры или галереи на телефоне -->
        <div class="mb-3">
          <label class="form-label">Фото товара</label>
          <!-- capture="environment" — открыть заднюю камеру на телефоне по умолчанию -->
          <div class="photo-drop" id="photo-drop" onclick="document.getElementById('photo-input').click()">
            <input type="file" id="photo-input" accept="image/*" capture="environment">
            <div id="photo-drop-text">
              <div style="font-size:28px; color:#9ca3af; margin-bottom:8px">&#128247;</div>
              <div style="font-weight:600; color:#374151">Нажмите или перетащите фото</div>
              <div class="text-muted" style="font-size:13px; margin-top:4px">JPG, PNG, WebP — до 10 МБ</div>
            </div>
            <img id="photo-preview" class="photo-preview" alt="Превью фото">
          </div>
          <!-- Статус загрузки фото (прогресс/ошибка) -->
          <div id="status-photo" class="status" style="margin-top:8px"></div>
          <!-- Кнопка «Сбросить фото» — видна если уже есть привязка -->
          <button id="btn-reset-photo" class="btn btn-danger btn-ghost btn-sm mt-2"
                  style="display:none" onclick="resetPhoto()">
            Сбросить фото
          </button>
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

  // Предзаполнить поле «Отображаемое название» — текущей правкой или пустым (D-05)
  const nameInput = document.getElementById("edit-display-name");
  nameInput.value = product.display_name || "";

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

  // Активировать кнопку «Сохранить правку» при любом изменении полей (план 02, UI-SPEC)
  function checkChanged() {
    const nameChanged = nameInput.value !== (product.display_name || "");
    const groupChanged = sel.value !== "" && sel.value !== (product.group || "");
    document.getElementById("btn-save").disabled = !(nameChanged || groupChanged);
  }
  nameInput.oninput = checkChanged;
  sel.onchange = checkChanged;
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

  const group       = document.getElementById("edit-group").value;
  const displayName = document.getElementById("edit-display-name").value.trim();

  // Проверяем наличие хотя бы одного изменения
  const nameChanged  = displayName !== (currentProduct.display_name || "");
  const groupChanged = group !== "" && group !== (currentProduct.group || "");
  if (!nameChanged && !groupChanged) return;

  document.getElementById("btn-save").disabled = true;
  showEdit("info", "Сохраняем правку...");

  // Ключ правки = сырое имя из прайса; normalize_name применяется на сервере в /save (D-05)
  const key = currentProduct.name;

  // Сохраняем правки последовательно (может быть 1 или 2 типа)
  let lastResult = null;
  let anyOk = false;

  // Правка отображаемого названия (план 02, D-05)
  if (nameChanged) {
    const d = await apiCall(`/${TOKEN}/save`, {
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: key, type: "name", value: displayName }),
    });
    lastResult = d;
    if (d && d.ok) {
      anyOk = true;
      // Обновить локальный объект товара
      currentProduct.display_name = displayName;
      const idx = allProducts.findIndex(p => p.name === currentProduct.name);
      if (idx >= 0) allProducts[idx].display_name = displayName;
    }
  }

  // Правка группы (план 01)
  if (groupChanged) {
    const d = await apiCall(`/${TOKEN}/save`, {
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: key, type: "group", value: group }),
    });
    lastResult = d;
    if (d && d.ok) {
      anyOk = true;
      // Обновить локальный объект товара
      currentProduct.group = group;
      const idx = allProducts.findIndex(p => p.name === currentProduct.name);
      if (idx >= 0) allProducts[idx].group = group;
    }
  }

  document.getElementById("btn-save").disabled = false;

  if (!lastResult) {
    showEdit("err", "Ошибка соединения. Попробуйте ещё раз.");
    return;
  }

  // Показать последний статус; при успехе — вернуться к списку через 1.5 с
  showEdit(anyOk ? "ok" : "err",
    anyOk
      ? "Правка сохранена. Она применится автоматически при следующем обновлении прайса или нажмите «Применить сейчас»."
      : (lastResult.message || "Не удалось сохранить правку."));

  if (anyOk) {
    setTimeout(() => {
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

/* ── Зона загрузки фото (план 03, D-06) ── */

// Показать статус в баннере загрузки фото
function showPhoto(kind, text) {
  const el = document.getElementById("status-photo");
  el.className = "status " + kind;
  el.textContent = text;
}

// Обработка перетаскивания файла в зону загрузки
(function initDropZone() {
  const drop = document.getElementById("photo-drop");
  if (!drop) return;
  drop.addEventListener("dragover", e => {
    e.preventDefault();
    drop.classList.add("drag-over");
  });
  drop.addEventListener("dragleave", () => drop.classList.remove("drag-over"));
  drop.addEventListener("drop", e => {
    e.preventDefault();
    drop.classList.remove("drag-over");
    const files = e.dataTransfer && e.dataTransfer.files;
    if (files && files.length > 0) handlePhotoFile(files[0]);
  });
})();

// При выборе файла через input — обработать и загрузить
document.getElementById("photo-input").addEventListener("change", e => {
  const f = e.target.files && e.target.files[0];
  if (f) handlePhotoFile(f);
  // Сбросить input, чтобы можно было выбрать тот же файл повторно
  e.target.value = "";
});

// Обработать выбранный файл: показать превью и загрузить в Cloudinary
async function handlePhotoFile(file) {
  // Клиентская валидация расширения и размера (дублирует серверную проверку T-04-09)
  const ext = file.name.split(".").pop().toLowerCase();
  const allowedExts = ["jpg", "jpeg", "png", "webp"];
  if (!allowedExts.includes(ext)) {
    showPhoto("err", "Не удалось загрузить фото. Проверьте формат файла (JPG, PNG, WebP) и размер (до 10 МБ).");
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    showPhoto("err", "Не удалось загрузить фото. Проверьте формат файла (JPG, PNG, WebP) и размер (до 10 МБ).");
    return;
  }

  // Показать локальное превью сразу при выборе (до загрузки)
  const reader = new FileReader();
  reader.onload = ev => {
    const preview = document.getElementById("photo-preview");
    preview.src = ev.target.result;
    preview.style.display = "block";
    document.getElementById("photo-drop-text").style.display = "none";
  };
  reader.readAsDataURL(file);

  if (!currentProduct) {
    showPhoto("err", "Ошибка: товар не выбран.");
    return;
  }

  showPhoto("info", "Загружаем фото...");

  // Отправить файл на сервер через FormData → /photo
  const fd = new FormData();
  fd.append("photo", file, file.name);
  fd.append("key", currentProduct.name); // нормализация на сервере (D-05)

  try {
    const r = await fetch(`/${TOKEN}/photo`, { method: "POST", body: fd });
    const d = await r.json();
    if (d && d.ok) {
      showPhoto("ok", d.message || "Фото сохранено.");
      // Обновить превью по URL из Cloudinary (окончательный URL)
      if (d.url) {
        const preview = document.getElementById("photo-preview");
        preview.src = d.url;
        preview.style.display = "block";
      }
      // Обновить image_url товара в локальном состоянии
      currentProduct.image_url = d.url || currentProduct.image_url;
      const idx = allProducts.findIndex(p => p.name === currentProduct.name);
      if (idx >= 0) allProducts[idx].image_url = currentProduct.image_url;
      // Показать кнопку «Сбросить фото»
      document.getElementById("btn-reset-photo").style.display = "";
    } else {
      showPhoto("err", (d && d.message) || "Не удалось загрузить фото. Проверьте формат файла (JPG, PNG, WebP) и размер (до 10 МБ).");
      // Убрать превью при ошибке загрузки
      document.getElementById("photo-preview").style.display = "none";
      document.getElementById("photo-drop-text").style.display = "";
    }
  } catch (e) {
    showPhoto("err", "Ошибка соединения. Попробуйте ещё раз.");
    document.getElementById("photo-preview").style.display = "none";
    document.getElementById("photo-drop-text").style.display = "";
  }
}

// Сброс фото — пишет пустую photo-правку (привязка удаляется при следующем обновлении)
async function resetPhoto() {
  if (!currentProduct) return;
  showPhoto("info", "Сбрасываем привязку фото...");
  const fd = new FormData();
  // Отправляем специальный файл-заглушку — серверная валидация не пройдёт,
  // поэтому сброс выполняется через /save с пустым значением
  const d = await apiCall(`/${TOKEN}/save`, {
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key: currentProduct.name, type: "photo", value: "" }),
  });
  if (d && d.ok) {
    showPhoto("ok", "Привязка фото сброшена.");
    document.getElementById("photo-preview").style.display = "none";
    document.getElementById("photo-drop-text").style.display = "";
    document.getElementById("btn-reset-photo").style.display = "none";
    currentProduct.image_url = "";
  } else {
    showPhoto("err", (d && d.message) || "Не удалось сбросить фото.");
  }
}

/* ── Расширение showEditScreen: заполнять зону фото ── */
// Переопределяем после объявления оригинальной функции — обёртка не нужна,
// просто патчим вызов: при открытии экрана правки показываем текущее фото.
const _origShowEditScreen = showEditScreen;
// eslint-disable-next-line no-global-assign
window.showEditScreen = function(product) {
  _origShowEditScreen(product);

  // Сбросить состояние зоны загрузки фото
  const preview = document.getElementById("photo-preview");
  const dropText = document.getElementById("photo-drop-text");
  const statusPhoto = document.getElementById("status-photo");
  const btnReset = document.getElementById("btn-reset-photo");

  statusPhoto.className = "status";
  statusPhoto.textContent = "";

  if (product.image_url) {
    // Показать текущее фото товара
    preview.src = product.image_url;
    preview.style.display = "block";
    dropText.style.display = "none";
    btnReset.style.display = "";
  } else {
    // Нет фото — показать приглашение загрузить
    preview.src = "";
    preview.style.display = "none";
    dropText.style.display = "";
    btnReset.style.display = "none";
  }
};
// Восстановить привязку к кнопке после переопределения
showEditScreen = window.showEditScreen;

/* ── Инициализация ── */
loadProducts();
</script>
</body>
</html>"""
