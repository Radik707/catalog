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

# ── Строки групп для выпадающего списка (только настоящие категории) ──
# «Новинки» сюда НЕ входит: это МЕТКА (badge), а не группа — управляется кнопками на карточке.
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

    # Белый список типов правок: group + name + photo + badge (метка «новинка»/«хит», T-04-02)
    SAVE_ALLOWED_TYPES = {"group", "name", "photo", "badge"}
    if edit_type not in SAVE_ALLOWED_TYPES:
        return jsonify(
            ok=False,
            message="Не удалось сохранить правку. Неподдерживаемый тип правки.",
        ), 400

    # Значение обязательно для group и name; для photo и badge допустимо пустое
    # (photo — сброс привязки; badge — снятие метки «без метки»)
    if not value and edit_type not in ("photo", "badge"):
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
        # Пишем ПОЛНЫЙ URL Cloudinary (а не короткую ссылку presenter/<имя>): при
        # пересборке он уходит в каталог как есть. Короткие ссылки от старых загрузок
        # upload.py всё равно развернёт (реконструкция в _resolve_photo_override).
        try:
            rc2, output2 = _run_py(
                SHEET_HELPER,
                "append_edit",
                "--key", key,
                "--type", "photo",
                "--value", url,
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
            # Пересборка из АРХИВА последней партии (LAST_BATCH_DIR), а не из очереди
            # оператора (она пустеет после загрузки) — иначе сборка падает на пустой папке.
            ok, err, count = run_upload(LAST_BATCH_DIR)
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
# Структура: Tabler CSS из CDN (только стили, без JS), mobile-first, адаптивный контейнер.
# Один экран: сетка/список фото-карточек с инлайн-правкой группы, названия и фото.
# Правка происходит прямо на карточке — без отдельного экрана (D-03: без сторонних JS из CDN).
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
  /* ── Базовые стили ── */
  body { background: #f3f4f6; }

  /* Общий плавающий тост статуса (низ экрана) */
  #toast {
    position: fixed; left: 50%; bottom: 20px; transform: translateX(-50%);
    max-width: 92%; padding: 12px 18px; border-radius: 12px; font-size: 14px;
    box-shadow: 0 6px 24px rgba(0,0,0,0.18); z-index: 1000; display: none;
    white-space: pre-wrap; text-align: center;
  }
  #toast.ok   { background: #ecfdf5; color: #065f46; display: block; }
  #toast.err  { background: #fef2f2; color: #991b1b; display: block; }
  #toast.info { background: #eff6ff; color: #1e40af; display: block; }

  /* Статусный баннер «Применить сейчас» */
  .status { margin-top: 16px; padding: 14px; border-radius: 12px; font-size: 14px;
            white-space: pre-wrap; display: none; }
  .status.ok   { background: #ecfdf5; color: #065f46; display: block; }
  .status.err  { background: #fef2f2; color: #991b1b; display: block; }
  .status.info { background: #eff6ff; color: #1e40af; display: block; }

  /* Вкладки-фильтры */
  .filter-tabs { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
  .filter-tab  { padding: 8px 14px; border-radius: 8px; border: 1px solid #d1d5db;
                 background: #fff; cursor: pointer; font-size: 14px; color: #374151;
                 min-height: 44px; }
  .filter-tab.active { background: #2563eb; color: #fff; border-color: #2563eb; }

  /* Переключатель вида (Сетка / Список) и регулятор плотности — одинаковый стиль */
  .view-toggle, .density-toggle {
    display: inline-flex; border: 1px solid #d1d5db; border-radius: 8px;
    overflow: hidden;
  }
  .view-toggle button, .density-toggle button {
    border: 0; background: #fff; padding: 8px 16px; cursor: pointer;
    font-size: 14px; color: #374151; min-height: 44px;
  }
  .view-toggle button.active, .density-toggle button.active {
    background: #2563eb; color: #fff;
  }
  /* Разделитель между кнопками плотности */
  .density-toggle button + button { border-left: 1px solid #d1d5db; }
  /* Регулятор плотности скрыт в режиме «Список» (управляется JS-классом) */
  .density-toggle.hidden { display: none; }

  /* Пустое состояние */
  .empty-state { text-align: center; padding: 48px 16px; color: #6b7280; }
  .empty-state h3 { margin: 0 0 8px; color: #374151; font-size: 16px; }

  /* ── Контейнер карточек: режим «Сетка» ── */
  /* Число колонок подстраивается под ширину экрана через auto-fill + minmax.
     Минимальная ширина карточки задаётся уровнем плотности (density-l/m/s):
     чем мельче — тем больше карточек в ряд. На узком экране (телефон) колонок
     становится меньше автоматически. --ui-scale пропорционально ужимает всё
     внутри карточки (фото, шрифты, кнопки, отступы). */
  #products.view-grid {
    display: grid;
    gap: var(--grid-gap, 12px);
    grid-template-columns: repeat(auto-fill, minmax(var(--card-min, 230px), 1fr));
  }

  /* Крупно (по умолчанию): большие карточки, ≈3–4 в ряд на мониторе */
  #products.view-grid.density-l { --card-min: 230px; --grid-gap: 12px; --ui-scale: 1;    }
  /* Средне: ≈4–5 в ряд */
  #products.view-grid.density-m { --card-min: 175px; --grid-gap: 10px; --ui-scale: 0.86; }
  /* Мелко: ≈6–7 в ряд, всё компактное */
  #products.view-grid.density-s { --card-min: 130px; --grid-gap: 8px;  --ui-scale: 0.72; }

  /* ── Контейнер карточек: режим «Список» ── */
  #products.view-list { display: flex; flex-direction: column; gap: 10px; }

  /* Карточка */
  .pcard { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px;
           overflow: hidden; }

  /* Фото — белый фон. Рамка КВАДРАТНАЯ (1:1), фото заполняет её (cover).
     Так фото показывается «крупно» без белых полей; точную видимую область
     задаёт квадратная трансформация Cloudinary (см. редактор подгонки). */
  .pcard-photo { width: 100%; background: #fff; display: flex; align-items: center;
                 justify-content: center; overflow: hidden; }
  /* Фото показываем ЦЕЛИКОМ (contain), не обрезаем; квадратная рамка остаётся,
     пустое место заполняет белый фон рамки. */
  .pcard-photo img { width: 100%; height: 100%; object-fit: contain; }
  .pcard-photo .ph-empty { color: #d1d5db; }

  /* Сетка: фото — квадрат во всю ширину колонки.
     Размер задаётся шириной карточки (плотность Крупно/Средне/Мелко уже
     управляет --card-min), поэтому фикс. высоты больше не нужны. */
  .view-grid .pcard-photo { aspect-ratio: 1 / 1; height: auto; }
  /* Список: мини-квадрат слева */
  .view-list .pcard { display: flex; align-items: stretch; }
  .view-list .pcard-photo { width: 72px; min-width: 72px; height: 72px; aspect-ratio: 1 / 1; }
  .view-list .pcard-body { flex: 1; min-width: 0; }

  .pcard-body { padding: 10px; display: flex; flex-direction: column; gap: 8px; }

  /* Бейджи */
  .pcard-badges { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
  .badge-attn { background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa;
                font-weight: 600; padding: 2px 8px; border-radius: 6px; font-size: 13px; }
  .badge-new  { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe;
                font-weight: 600; padding: 2px 8px; border-radius: 6px; font-size: 13px; }
  .pcard-hints { font-size: 12px; color: #6b7280; }

  /* Название + карандаш правки */
  .pcard-name-row { display: flex; align-items: flex-start; gap: 6px; }
  /* Название НИКОГДА не обрезается: переносится полностью на любое число строк.
     overflow-wrap/word-break — чтобы и длинные слова не вылезали за карточку.
     Высоту не фиксируем — пусть карточка растёт по тексту (grid auto-fill держит). */
  .pcard-name { font-size: 14px; font-weight: 600; color: #111827; line-height: 1.25;
                flex: 1; white-space: normal;
                overflow-wrap: break-word; word-break: break-word; }
  .pcard-edit-name { cursor: pointer; background: none; border: 0; font-size: 16px;
                     line-height: 1; padding: 2px; color: #6b7280; }
  .pcard-name-input { width: 100%; font-size: 14px; }

  /* Select группы — крупный, удобный для пальца.
     padding-right оставляет место под стрелку списка, чтобы длинные значения
     (напр. «Конфеты и печенье») не налезали на стрелку. */
  .pcard-group { width: 100%; font-size: 14px; min-height: 44px; padding-right: 26px; }

  /* ── Кнопки-переключатели меток «NEW» / «Хит» ── */
  .pcard-badges-toggle { display: flex; gap: 6px; }
  .badge-toggle {
    flex: 1; min-height: 38px; font-size: 13px; font-weight: 600;
    border-radius: 8px; cursor: pointer; border: 1px solid #d1d5db;
    background: #f3f4f6; color: #6b7280; transition: background .12s, color .12s;
  }
  /* Активная метка — зелёная (загорается) */
  .badge-toggle.active {
    background: #16a34a; color: #fff; border-color: #16a34a;
  }
  .badge-toggle:disabled { opacity: .6; cursor: default; }

  /* Кнопка фото */
  .pcard-photo-btn { width: 100%; min-height: 44px; font-size: 14px; }
  .pcard input[type="file"] { display: none; }

  /* Короткая пометка статуса на карточке */
  .pcard-status { font-size: 12px; min-height: 16px; }
  .pcard-status.ok  { color: #065f46; }
  .pcard-status.err { color: #991b1b; }

  /* Кнопка «Применить сейчас» */
  .btn-apply { min-height: 48px; font-size: 16px; font-weight: 600; }

  /* ──────────────────────────────────────────────────────────────────
     ПРОПОРЦИОНАЛЬНОЕ МАСШТАБИРОВАНИЕ КАРТОЧЕК ПО УРОВНЯМ ПЛОТНОСТИ
     Все правила ниже действуют ТОЛЬКО в режиме «Сетка» (.view-grid).
     Режим «Список» не затрагивается. Тач-цели кнопок не опускаем ниже ~28–30px,
     чтобы по ним можно было попасть даже на «Мелко».
     ────────────────────────────────────────────────────────────────── */

  /* Отступы и зазоры тела карточки */
  .view-grid.density-l .pcard-body { padding: 10px; gap: 8px; }
  .view-grid.density-m .pcard-body { padding: 8px;  gap: 6px; }
  .view-grid.density-s .pcard-body { padding: 6px;  gap: 5px; }

  /* Название — только уменьшаем шрифт по плотности, БЕЗ обрезки.
     Текст переносится полностью, высота карточки растёт по содержимому. */
  .view-grid.density-l .pcard-name { font-size: 14px; }
  .view-grid.density-m .pcard-name { font-size: 12.5px; line-height: 1.2; }
  .view-grid.density-s .pcard-name { font-size: 11.5px; line-height: 1.2; }

  /* Карандаш правки названия */
  .view-grid.density-m .pcard-edit-name { font-size: 15px; }
  .view-grid.density-s .pcard-edit-name { font-size: 14px; padding: 1px; }

  /* Бейджи (⚠ / Новинка) и подписи-подсказки */
  .view-grid.density-m .badge-attn,
  .view-grid.density-m .badge-new { font-size: 12px; padding: 1px 6px; }
  .view-grid.density-s .badge-attn,
  .view-grid.density-s .badge-new { font-size: 11px; padding: 1px 5px; }
  .view-grid.density-m .pcard-hints { font-size: 11px; }
  .view-grid.density-s .pcard-hints { font-size: 10.5px; }

  /* Кнопки-метки NEW / Хит — компактнее, чтобы освободить место под полное название.
     Остаются нажимаемыми и читаемыми (тач-цель не ниже ~26px). */
  .view-grid.density-l .badge-toggle { min-height: 34px; font-size: 12.5px; }
  .view-grid.density-m .badge-toggle { min-height: 28px; font-size: 11px; padding: 0 4px; }
  .view-grid.density-s .badge-toggle { min-height: 26px; font-size: 10.5px; padding: 0 3px; }

  /* Выпадающий список группы — остаётся кликабельным на всех уровнях.
     padding-right под стрелку увеличен, чтобы текст значения не перекрывался стрелкой. */
  .view-grid.density-l .pcard-group { font-size: 14px; min-height: 44px; padding-right: 26px; }
  .view-grid.density-m .pcard-group { font-size: 11.5px; min-height: 32px; padding: 3px 22px 3px 6px; }
  .view-grid.density-s .pcard-group { font-size: 11px;   min-height: 28px; padding: 2px 20px 2px 5px; }

  /* Кнопка фото — высота не ниже 30px (тач-цель сохраняется) */
  .view-grid.density-l .pcard-photo-btn { min-height: 44px; font-size: 14px; }
  .view-grid.density-m .pcard-photo-btn { min-height: 34px; font-size: 12px; padding: 4px 6px; }
  .view-grid.density-s .pcard-photo-btn { min-height: 30px; font-size: 11px; padding: 2px 4px; }

  /* Статус-строка карточки */
  .view-grid.density-m .pcard-status,
  .view-grid.density-s .pcard-status { font-size: 11px; }

  /* ──────────────────────────────────────────────────────────────────
     РЕДАКТОР ФОТО → «ПОДГОНКА ПОД КАРТОЧКУ» (зум / поворот)
     Маленькая кнопка-карандаш поверх фото открывает модалку.
     Редактор НЕ меняет исходный файл: он подбирает трансформацию URL
     Cloudinary (кроп + поворот) и сохраняет готовый URL. Превью —
     обычный <img> с живым применением трансформации.
     Только ванильный JS — без сторонних библиотек (D-03).
     ────────────────────────────────────────────────────────────────── */

  /* Контейнер фото — относительное позиционирование для кнопки-карандаша */
  .pcard-photo { position: relative; }
  /* Кнопка «✏️» в углу фото — тач-цель не меньше 40px */
  .pcard-edit-photo {
    position: absolute; top: 4px; right: 4px;
    width: 40px; height: 40px; min-width: 40px;
    display: flex; align-items: center; justify-content: center;
    border: 0; border-radius: 8px; cursor: pointer;
    background: rgba(255,255,255,0.85); color: #374151; font-size: 18px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.18); padding: 0; line-height: 1;
  }
  .pcard-edit-photo:hover { background: #fff; }
  /* На мелкой сетке кнопка чуть компактнее, но остаётся нажимаемой */
  .view-grid.density-s .pcard-edit-photo { width: 34px; height: 34px; min-width: 34px; font-size: 15px; }

  /* Затемнение-фон модалки редактора */
  #photo-editor {
    position: fixed; inset: 0; z-index: 2000; display: none;
    background: rgba(0,0,0,0.6);
    align-items: center; justify-content: center; padding: 12px;
  }
  #photo-editor.open { display: flex; }

  /* Карточка модалки — не вылезает за экран, скроллится при нехватке высоты */
  .pe-dialog {
    background: #fff; border-radius: 14px; width: 100%; max-width: 460px;
    max-height: 96vh; overflow-y: auto; padding: 16px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.3);
  }
  .pe-title { font-size: 16px; font-weight: 600; color: #111827; margin: 0 0 4px; }
  .pe-sub   { font-size: 13px; color: #6b7280; margin: 0 0 12px;
              overflow-wrap: break-word; word-break: break-word; }

  /* Квадратная рамка-превью 1:1 — точная копия рамки карточки.
     Внутри обычный <img> с трансформацией Cloudinary (object-fit: cover). */
  .pe-frame {
    position: relative; width: 100%; aspect-ratio: 1 / 1;
    background: #fff; border: 2px solid #2563eb; border-radius: 10px;
    overflow: hidden;
  }
  /* Превью — точная копия карточки: фото целиком (contain) на белом фоне. */
  .pe-frame img { display: block; width: 100%; height: 100%; object-fit: contain; }

  /* Контролы редактора */
  .pe-controls { display: flex; flex-direction: column; gap: 10px; margin-top: 14px; }
  .pe-row { display: flex; align-items: center; gap: 8px; }
  /* Тач-дружественные кнопки ≥40px */
  .pe-btn {
    min-height: 44px; min-width: 44px; font-size: 16px; font-weight: 600;
    border: 1px solid #d1d5db; border-radius: 8px; background: #fff;
    color: #374151; cursor: pointer; padding: 0 12px;
    display: inline-flex; align-items: center; justify-content: center;
  }
  .pe-btn:hover { background: #f3f4f6; }
  .pe-label { font-size: 13px; color: #6b7280; min-width: 56px; }
  .pe-zoom { flex: 1; height: 36px; }
  /* Кнопки «Сохранить» / «Отмена» — на всю ширину строки */
  .pe-actions { display: flex; gap: 10px; margin-top: 6px; }
  .pe-actions .pe-btn { flex: 1; min-height: 48px; }
  .pe-save   { background: #2563eb; color: #fff; border-color: #2563eb; }
  .pe-save:hover { background: #1d4ed8; }
  .pe-save:disabled { opacity: .6; cursor: default; }
</style>
</head>
<body>
<div class="container py-3" style="max-width:1200px">

  <!-- ── Шапка ── -->
  <div class="mb-3">
    <h1 class="h3 mb-0">Вкусный Дом — Панель управления</h1>
    <p class="text-muted mb-0" style="font-size:14px">Товары и правки</p>
  </div>

  <!-- Поиск по названию -->
  <div class="mb-3">
    <input id="search-input" class="form-control" type="search"
           placeholder="Поиск по названию..." autocomplete="off">
  </div>

  <!-- Вкладки-фильтры + переключатель вида -->
  <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
    <div class="filter-tabs" id="filter-tabs">
      <button class="filter-tab" data-filter="attention">Требуют внимания</button>
      <button class="filter-tab" data-filter="new">Новинки</button>
      <button class="filter-tab" data-filter="nogroup">Без группы</button>
      <button class="filter-tab" data-filter="nophoto">Без фото</button>
      <button class="filter-tab active" data-filter="all">Все</button>
    </div>
    <div class="d-flex align-items-center flex-wrap gap-2">
      <!-- Регулятор плотности сетки (виден только в режиме «Сетка») -->
      <div class="density-toggle" id="density-toggle">
        <button data-density="l">Крупно</button>
        <button data-density="m">Средне</button>
        <button data-density="s">Мелко</button>
      </div>
      <div class="view-toggle" id="view-toggle">
        <button data-view="grid">Сетка</button>
        <button data-view="list">Список</button>
      </div>
    </div>
  </div>

  <!-- Сетка/список карточек товаров -->
  <div id="products" class="view-grid"></div>

  <!-- Статусный баннер «Применить сейчас» -->
  <div id="status" class="status"></div>

  <!-- Кнопка «Применить сейчас» -->
  <div class="mt-4 mb-5">
    <button id="btn-apply" class="btn btn-primary w-100 btn-apply" onclick="applyNow()">
      Применить сейчас
    </button>
  </div>

</div><!-- /container -->

<!-- Общий плавающий тост -->
<div id="toast"></div>

<!-- ── Модальное окно «подгонка фото под карточку» (зум / поворот) ── -->
<div id="photo-editor" aria-hidden="true">
  <div class="pe-dialog" role="dialog" aria-modal="true">
    <h2 class="pe-title">Подгонка фото под карточку</h2>
    <p class="pe-sub" id="pe-name"></p>

    <!-- Квадратная рамка-превью: ровно как фото в карточке -->
    <div class="pe-frame" id="pe-frame">
      <img id="pe-preview" alt="Превью">
    </div>

    <div class="pe-controls">
      <!-- Поворот -->
      <div class="pe-row">
        <span class="pe-label">Поворот</span>
        <button type="button" class="pe-btn" id="pe-rot-left" title="Повернуть влево">↺</button>
        <button type="button" class="pe-btn" id="pe-rot-right" title="Повернуть вправо">↻</button>
      </div>
      <!-- Зум: центрированный ползунок (центр=0 — оригинал; вправо приближает,
           влево отдаляет). Кнопки − / + сдвигают на ∓8. -->
      <div class="pe-row">
        <span class="pe-label">Зум</span>
        <button type="button" class="pe-btn" id="pe-zoom-out" title="Отдалить">−</button>
        <input type="range" class="pe-zoom" id="pe-zoom" min="-100" max="100" step="1" value="0">
        <button type="button" class="pe-btn" id="pe-zoom-in" title="Приблизить">+</button>
      </div>
      <!-- Действия -->
      <div class="pe-actions">
        <button type="button" class="pe-btn" id="pe-cancel">Отмена</button>
        <button type="button" class="pe-btn pe-save" id="pe-save">Сохранить</button>
      </div>
    </div>
  </div>
</div>

<script>
/* ── Константы и состояние ── */
const TOKEN = "__TOKEN__";
// Полный список товаров (загружается один раз)
let allProducts = [];
// Текущий активный фильтр
let activeFilter = "all";
// Текущий вид: "grid" | "list" (сохраняется в localStorage)
let activeView = localStorage.getItem("admin_view") || "grid";
// Текущая плотность сетки: "l" | "m" | "s" (Крупно/Средне/Мелко), по умолчанию Крупно
let activeDensity = localStorage.getItem("admin_density") || "l";
// Таймер живого поиска (debounce 300ms)
let searchTimer = null;
// Список групп для выпадающего списка — точно как массив GROUPS в admin.py.
// «Новинки» здесь НЕТ: это метка (badge), управляется кнопками NEW/Хит на карточке.
const GROUPS = [
  "Напитки", "Энергетики", "Батончики и шоколад", "Чай и кофе", "Снэки",
  "Детское", "Лапша и каши", "Стоевъ и Сэнсой", "Соусы и специи", "Консервация",
  "Конфеты и печенье", "Прикассовое", "Коробочные конфеты", "Крупы и бакалея",
  "Другое"
];

/* ── Утилиты ── */

// Экранирование для безопасной вставки в innerHTML — защита от XSS (T-04-05)
function esc(s) {
  return String(s).replace(/[&<>"']/g, c => (
    { '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]
  ));
}

// Плавающий тост; kind = "ok" | "err" | "info"
let toastTimer = null;
function toast(kind, text) {
  const el = document.getElementById("toast");
  el.className = kind;
  el.textContent = text;
  el.style.display = "block";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.style.display = "none"; }, 3500);
}

// Статусный баннер «Применить сейчас»
function show(kind, text) {
  const el = document.getElementById("status");
  el.className = "status " + kind;
  el.textContent = text;
}

// Обёртка fetch с JSON — возвращает данные или null при ошибке сети
async function apiCall(url, opts) {
  try {
    const r = await fetch(url, { method: "POST", ...opts });
    return await r.json();
  } catch (e) {
    return null;
  }
}

/* ── Фильтрация и поиск ── */

// Карточка «требует внимания» если: нет группы ИЛИ нет фото (is_new НЕ учитываем)
function needsAttention(p) {
  return !p.group || !p.image_url;
}

// Вернуть подмножество товаров под текущий фильтр и поиск
function filteredProducts() {
  const query = document.getElementById("search-input").value.trim().toLowerCase();
  return allProducts.filter(p => {
    let matchFilter;
    if (activeFilter === "attention")     matchFilter = needsAttention(p);
    else if (activeFilter === "new")      matchFilter = (p.badge === "новинка");
    else if (activeFilter === "nogroup")  matchFilter = !p.group;
    else if (activeFilter === "nophoto")  matchFilter = !p.image_url;
    else                                  matchFilter = true; // "all"

    const matchSearch = (query === "" || (p.name || "").toLowerCase().includes(query));
    return matchFilter && matchSearch;
  });
}

/* ── Рендер карточек ──
   Рендерим ТОЛЬКО отфильтрованные товары (а не show/hide всех ~870),
   чтобы на телефоне не тормозило. Перерисовываем при смене фильтра/поиска/вида. */

function render() {
  const container = document.getElementById("products");
  // Класс контейнера под выбранный вид; в сетке добавляем класс плотности.
  if (activeView === "list") {
    container.className = "view-list";
  } else {
    container.className = "view-grid density-" + activeDensity;
  }

  const list = filteredProducts();
  container.innerHTML = "";

  if (list.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.style.gridColumn = "1 / -1";
    if (activeFilter === "attention") {
      empty.innerHTML = '<h3>Все товары в порядке</h3>' +
        '<p>Новых товаров без группы или фото нет. Можно применить правки или подождать следующего прайса.</p>';
    } else {
      empty.innerHTML = '<h3>Товары не найдены по этому фильтру</h3>';
    }
    container.appendChild(empty);
    return;
  }

  list.forEach((p, i) => {
    container.appendChild(buildCard(p, i));
  });
}

// Построить одну карточку товара
function buildCard(p, i) {
  const card = document.createElement("div");
  card.className = "pcard";
  card.dataset.idx = i;

  // Уникальный id input файла — чтобы карточки не путались
  const fileId = "file-" + i;

  // ── Фото ──
  const photoHtml = p.image_url
    ? `<img src="${esc(p.image_url)}" alt="${esc(p.name)}" loading="lazy" decoding="async">`
    : `<svg class="ph-empty" width="40" height="40" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v13.5a1.5 1.5 0 001.5 1.5z"/></svg>`;

  // Кнопка «✏️» для кадрирования — показываем только если у товара уже есть фото
  const editPhotoBtn = p.image_url
    ? `<button class="pcard-edit-photo" type="button" title="Кадрировать фото">&#9998;</button>` : "";

  // ── Бейджи и подписи ──
  // Метку «новинка»/«хит» показывает ТОЛЬКО кнопка NEW/Хит своим зелёным
  // состоянием (по p.badge). Текстовый бейдж метки на карточке НЕ рисуем,
  // чтобы не было дублирования. Здесь — только индикатор «требует внимания».
  let badges = "";
  if (!p.group || !p.image_url) badges += '<span class="badge-attn">&#9888;</span>';

  const hints = [];
  if (!p.group)     hints.push("Без группы");
  if (!p.image_url) hints.push("Без фото");
  const hintsHtml = hints.length
    ? `<div class="pcard-hints">${esc(hints.join(" · "))}</div>` : "";

  // ── Отображаемое имя ──
  const shownName = p.display_name || p.name;

  // ── Выпадающий список группы ──
  let groupOpts = '<option value="">Выберите группу...</option>';
  GROUPS.forEach(g => {
    const sel = (p.group === g) ? " selected" : "";
    groupOpts += `<option${sel}>${esc(g)}</option>`;
  });

  // ── Кнопка фото ──
  // Текст зависит от уровня плотности: на «Мелко» — короткая иконка/«Фото»,
  // на «Средне» — «Фото», на «Крупно» — полный «Заменить/Добавить фото».
  const photoBtnLabel = photoButtonLabel(!!p.image_url);

  // ── Кнопки-переключатели меток: активная (зелёная) если совпадает с p.badge ──
  const newActive = (p.badge === "новинка") ? " active" : "";
  const hitActive = (p.badge === "хит") ? " active" : "";

  card.innerHTML = `
    <div class="pcard-photo">${photoHtml}${editPhotoBtn}</div>
    <div class="pcard-body">
      <div class="pcard-badges">${badges}</div>
      ${hintsHtml}
      <div class="pcard-name-row">
        <span class="pcard-name">${esc(shownName)}</span>
        <button class="pcard-edit-name" title="Изменить название">&#9998;</button>
      </div>
      <div class="pcard-badges-toggle">
        <button class="badge-toggle badge-toggle-new${newActive}" type="button"
                data-badge="новинка">NEW</button>
        <button class="badge-toggle badge-toggle-hit${hitActive}" type="button"
                data-badge="хит">Хит</button>
      </div>
      <select class="form-select pcard-group">${groupOpts}</select>
      <button class="btn btn-outline-secondary pcard-photo-btn" type="button">${photoBtnLabel}</button>
      <input type="file" id="${fileId}" accept="image/*">
      <div class="pcard-status"></div>
    </div>`;

  // ── Привязка событий ──
  const statusEl = card.querySelector(".pcard-status");

  // Короткая пометка статуса на карточке
  function cardStatus(kind, text) {
    statusEl.className = "pcard-status " + kind;
    statusEl.textContent = text;
  }

  // Правка названия по карандашу — превращаем в input
  card.querySelector(".pcard-edit-name").addEventListener("click", () => {
    startNameEdit(card, p, cardStatus);
  });

  // Автосохранение группы при изменении (без кнопки, без перехода)
  const groupSel = card.querySelector(".pcard-group");
  groupSel.addEventListener("change", async () => {
    const value = groupSel.value;
    if (!value) return; // «Выберите группу...» — ничего не делаем
    saveScrollPos();    // место = эта карточка
    cardStatus("", "Сохраняем...");
    const d = await apiCall(`/${TOKEN}/save`, {
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: p.name, type: "group", value: value }),
    });
    if (d && d.ok) {
      p.group = value;
      syncProduct(p);
      cardStatus("ok", "Сохранено ✓");
      toast("ok", "Группа сохранена ✓");
    } else {
      cardStatus("err", "Не сохранено");
      toast("err", (d && d.message) || "Не удалось сохранить. Попробуйте ещё раз.");
    }
  });

  // ── Кнопки-переключатели меток «NEW» / «Хит» (взаимоисключающие, метка одна) ──
  const btnNew = card.querySelector(".badge-toggle-new");
  const btnHit = card.querySelector(".badge-toggle-hit");

  // Перекрасить кнопки под текущее значение p.badge
  function paintBadges() {
    btnNew.classList.toggle("active", p.badge === "новинка");
    btnHit.classList.toggle("active", p.badge === "хит");
  }

  // Обработчик нажатия: вычисляем новую метку, оптимистично перекрашиваем, сохраняем
  async function toggleBadge(targetBadge) {
    const prev = p.badge;                          // запомнить для отката при ошибке
    // Тап по активной снимает метку (""), по неактивной — ставит её
    const newBadge = (p.badge === targetBadge) ? "" : targetBadge;

    saveScrollPos();   // место = эта карточка
    // Оптимистично: сразу обновить состояние и перекрасить
    p.badge = newBadge;
    syncProduct(p);
    paintBadges();
    btnNew.disabled = true; btnHit.disabled = true;
    cardStatus("", "Сохраняем...");

    const d = await apiCall(`/${TOKEN}/save`, {
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: p.name, type: "badge", value: newBadge }),
    });

    btnNew.disabled = false; btnHit.disabled = false;
    if (d && d.ok) {
      cardStatus("ok", "Метка обновлена ✓");
      toast("ok", "Метка обновлена ✓");
    } else {
      // Откат к прежнему состоянию
      p.badge = prev;
      syncProduct(p);
      paintBadges();
      cardStatus("err", "Не сохранено");
      toast("err", (d && d.message) || "Не удалось обновить метку. Попробуйте ещё раз.");
    }
  }

  btnNew.addEventListener("click", () => toggleBadge("новинка"));
  btnHit.addEventListener("click", () => toggleBadge("хит"));

  // Кнопка фото → клик по скрытому input
  const fileInput = card.querySelector('input[type="file"]');
  card.querySelector(".pcard-photo-btn").addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", e => {
    const f = e.target.files && e.target.files[0];
    if (f) uploadPhoto(f, p, card, cardStatus);
    e.target.value = ""; // сброс — чтобы можно было выбрать тот же файл повторно
  });

  // Кнопка «✏️» кадрирования (есть только если у товара есть фото)
  const editPhotoEl = card.querySelector(".pcard-edit-photo");
  if (editPhotoEl) {
    editPhotoEl.addEventListener("click", () => {
      saveScrollPos();               // запомнить место = последняя активная карточка
      openPhotoEditor(p, card, cardStatus);
    });
  }

  return card;
}

// Синхронизировать изменённый товар в allProducts
function syncProduct(p) {
  const idx = allProducts.findIndex(x => x.name === p.name);
  if (idx >= 0) allProducts[idx] = p;
}

/* ── Инлайн-правка названия ── */
function startNameEdit(card, p, cardStatus) {
  const row = card.querySelector(".pcard-name-row");
  const input = document.createElement("input");
  input.type = "text";
  input.className = "form-control pcard-name-input";
  input.value = p.display_name || p.name;
  input.placeholder = "Название для каталога";
  row.style.display = "none";
  row.insertAdjacentElement("afterend", input);
  input.focus();
  input.select();

  let done = false;
  async function commit() {
    if (done) return;
    done = true;
    const value = input.value.trim();
    // Пустое значение = вернуть имя из прайса (на сервер уходит пустая правка name)
    cardStatus("", "Сохраняем...");
    const d = await apiCall(`/${TOKEN}/save`, {
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: p.name, type: "name", value: value }),
    });
    input.remove();
    if (d && d.ok) {
      p.display_name = value;
      syncProduct(p);
      card.querySelector(".pcard-name").textContent = value || p.name;
      cardStatus("ok", "Сохранено ✓");
      toast("ok", "Название сохранено ✓");
    } else {
      cardStatus("err", "Не сохранено");
      toast("err", (d && d.message) || "Не удалось сохранить название.");
    }
    row.style.display = "";
  }

  input.addEventListener("blur", commit);
  input.addEventListener("keydown", e => {
    if (e.key === "Enter") { e.preventDefault(); input.blur(); }
    else if (e.key === "Escape") { done = true; input.remove(); row.style.display = ""; }
  });
}

/* ── Загрузка фото ── */
async function uploadPhoto(file, p, card, cardStatus) {
  // Клиентская валидация (дублирует серверную T-04-09)
  const ext = (file.name.split(".").pop() || "").toLowerCase();
  const allowedExts = ["jpg", "jpeg", "png", "webp"];
  const errMsg = "Не удалось загрузить фото. Проверьте формат файла (JPG, PNG, WebP) и размер (до 10 МБ).";
  if (!allowedExts.includes(ext)) { cardStatus("err", "Неверный формат"); toast("err", errMsg); return; }
  if (file.size > 10 * 1024 * 1024) { cardStatus("err", "Файл слишком большой"); toast("err", errMsg); return; }

  cardStatus("", "Загружаем фото...");

  const fd = new FormData();
  fd.append("photo", file, file.name);
  fd.append("key", p.name); // нормализация на сервере (D-05)

  try {
    const r = await fetch(`/${TOKEN}/photo`, { method: "POST", body: fd });
    const d = await r.json();
    if (d && d.ok) {
      p.image_url = d.url || p.image_url;
      syncProduct(p);
      // Обновить превью на карточке
      const photoBox = card.querySelector(".pcard-photo");
      photoBox.innerHTML = `<img src="${esc(p.image_url)}" alt="${esc(p.name)}">`;
      // После загрузки кнопка превращается в «Заменить» (с учётом плотности)
      card.querySelector(".pcard-photo-btn").textContent = photoButtonLabel(true);
      cardStatus("ok", "Фото сохранено ✓");
      toast("ok", "Фото сохранено ✓");
    } else {
      cardStatus("err", "Ошибка загрузки");
      toast("err", (d && d.message) || errMsg);
    }
  } catch (e) {
    cardStatus("err", "Ошибка соединения");
    toast("err", "Ошибка соединения. Попробуйте ещё раз.");
  }
}

/* ──────────────────────────────────────────────────────────────────
   ПОДГОНКА ФОТО ПОД КАРТОЧКУ (зум / поворот → сохранить URL)
   НЕразрушающая правка: исходный файл не трогаем. Подбираем параметры
   трансформации Cloudinary (квадратный кроп + поворот) и сохраняем
   готовый URL через /save (type=photo). Превью — обычный <img>, src
   которого пересобирается при каждом изменении зума/поворота.
   Только ванильный JS, без библиотек (D-03).
   ────────────────────────────────────────────────────────────────── */

// Ползунок зума центрирован: позиция -100..100, центр 0 = оригинал (zoom 1.0).
// Маппинг позиции v в фактический zoom: zoom = 3^(v/100)
//   v=0   → 1.0   (центр, оригинал)
//   v=100 → 3.0   (максимальное приближение)
//   v=-100→ ~0.333 (максимальное отдаление)
const PE_POS_MIN = -100;     // крайнее левое положение ползунка (отдалить)
const PE_POS_MAX = 100;      // крайнее правое положение ползунка (приблизить)
const PE_POS_STEP = 8;       // шаг кнопок − / + по позиции ползунка
// Размер итогового квадрата для c_fill / c_pad (px)
const PE_FILL = 800;

// Позиция ползунка (-100..100) → фактический зум
function pePosToZoom(pos) {
  return Math.pow(3, pos / 100);
}

// Текущее состояние редактора подгонки
const peState = {
  product: null,    // товар, который редактируем
  card: null,       // DOM-карточка (для обновления превью)
  cardStatus: null, // функция статуса на карточке
  baseUrl: "",      // чистый базовый URL Cloudinary (без наших трансформаций)
  rotation: 0,      // поворот в градусах: 0 / 90 / 180 / 270
  zoom: 1,          // фактический зум (3^(zoomPos/100)); 1.0 = оригинал
  zoomPos: 0,       // позиция ползунка -100..100 (0 = центр = оригинал)
};

/* Убрать ранее добавленную НАМИ трансформацию из URL.
   Вырезаем сразу после `/upload/` ведущие сегменты-маркеры
   (a_<число>/, c_crop,.../, c_fill,.../), повторно пока они идут подряд.
   Возвращаем чистый базовый URL (с версией v123 и путём — не трогаем). */
function peStripTransform(url) {
  const marker = "/upload/";
  const at = url.indexOf(marker);
  if (at < 0) return url;                       // не Cloudinary upload-URL — отдаём как есть
  const head = url.slice(0, at + marker.length); // ".../image/upload/"
  let rest = url.slice(at + marker.length);
  // Наши маркеры трансформаций (в начале строки rest), снимаем по одному
  const peMarkers = [
    /^a_\d+\//,                 // поворот a_<число>/
    /^c_crop,[^/]*\//,          // кроп c_crop,.../
    /^c_fill,[^/]*\//,          // заполнение c_fill,.../
    /^c_fit,[^/]*\//,           // вписывание c_fit,.../  (зум-аут)
    /^c_pad,[^/]*\//,           // паддинг c_pad,.../      (зум-аут / поворот)
  ];
  let changed = true;
  while (changed) {
    changed = false;
    for (const re of peMarkers) {
      if (re.test(rest)) { rest = rest.replace(re, ""); changed = true; }
    }
  }
  return head + rest;
}

/* Собрать трансформированный URL из чистого базового + текущего зума/поворота.
   deg ∈ {0,90,180,270}; zoom — фактический зум (1.0 = оригинал).
   Три режима:
   - зум-ин (zoom > 1.02): вырезаем центральную часть c_crop (доля f=1/zoom),
     затем растягиваем до 800×800 — фото «приближается».
   - зум-аут (zoom < 0.98): вписываем фото целиком (c_fit) в меньший квадрат,
     затем добиваем белым паддингом до 800×800 — фото «отдаляется».
   - нейтраль (0.98..1.02): без зума. Если есть поворот — квадратим c_pad на белом;
     если поворота нет — трансформации НЕТ вовсе (вернём базовый URL = реальная картинка).
   Это чинит баг «цветной квадрат»: при zoom≈1 мы больше НЕ пишем c_crop,w_1. */
function peBuildUrl(baseUrl, deg, zoom) {
  const marker = "/upload/";
  const at = baseUrl.indexOf(marker);
  if (at < 0) return baseUrl;

  let t = "";
  if (deg > 0) t += "a_" + deg + "/";

  if (zoom > 1.02) {
    // Зум-ин: вырезаем центральную долю и растягиваем до квадрата.
    let f = Math.round((1 / zoom) * 1000) / 1000;   // доля 0..1, 3 знака
    if (f > 0.95) f = 0.95;
    if (f < 0.2) f = 0.2;
    t += "c_crop,g_center,w_" + String(f) + ",h_" + String(f) + "/";
    t += "c_fill,g_center,w_" + PE_FILL + ",h_" + PE_FILL + "/";
  } else if (zoom < 0.98) {
    // Зум-аут: фото целиком, уменьшенное, на белом паддинге.
    const s = Math.round(zoom * PE_FILL);           // сторона вписанного фото, px
    t += "c_fit,w_" + s + ",h_" + s + "/";
    t += "c_pad,g_center,w_" + PE_FILL + ",h_" + PE_FILL + ",b_white/";
  } else if (deg > 0) {
    // Нейтральный зум, но есть поворот — квадратим результат на белом фоне.
    t += "c_pad,g_center,w_" + PE_FILL + ",h_" + PE_FILL + ",b_white/";
  }

  // Ничего не накрутили (zoom≈1, deg==0) — отдаём оригинальный URL как есть.
  if (t === "") return baseUrl;
  return baseUrl.slice(0, at + marker.length) + t + baseUrl.slice(at + marker.length);
}

// Текущий URL превью (по состоянию редактора)
function peCurrentUrl() {
  return peBuildUrl(peState.baseUrl, peState.rotation, peState.zoom);
}

// Перерисовать превью (живое применение трансформации)
function peRefreshPreview() {
  document.getElementById("pe-preview").src = peCurrentUrl();
}

// Открыть редактор для товара p
function openPhotoEditor(p, card, cardStatus) {
  if (!p.image_url) return;
  peState.product = p;
  peState.card = card;
  peState.cardStatus = cardStatus;
  // ВАЖНО: всегда стартуем с ЧИСТОГО базового URL, чтобы трансформации
  // не наслаивались при повторном открытии. Зум/поворот — с нуля.
  peState.baseUrl = peStripTransform(p.image_url);
  peState.rotation = 0;
  peState.zoomPos = 0;     // ползунок в центр
  peState.zoom = 1;        // фактический зум = оригинал

  document.getElementById("pe-name").textContent = p.display_name || p.name;
  document.getElementById("pe-zoom").value = 0;     // центр
  document.getElementById("pe-save").disabled = false;

  const modal = document.getElementById("photo-editor");
  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");

  peRefreshPreview();
}

function closePhotoEditor() {
  const modal = document.getElementById("photo-editor");
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
  peState.product = null;
}

// Поворот на ±90°
function peRotate(delta) {
  peState.rotation = (peState.rotation + delta + 360) % 360;
  peRefreshPreview();
}

// Установить зум по ПОЗИЦИИ ползунка (-100..100). 0 = центр = оригинал.
function peSetZoomPos(pos) {
  let p = Math.max(PE_POS_MIN, Math.min(PE_POS_MAX, Math.round(pos)));
  peState.zoomPos = p;
  peState.zoom = pePosToZoom(p);     // фактический зум 3^(p/100)
  document.getElementById("pe-zoom").value = p;
  peRefreshPreview();
}

// Сохранить подгонку: записать готовый URL через /save (type=photo)
async function peSaveAndUpload() {
  const p = peState.product;
  if (!p) return;
  const saveBtn = document.getElementById("pe-save");
  saveBtn.disabled = true;

  const url = peCurrentUrl();
  if (peState.cardStatus) peState.cardStatus("", "Сохраняем...");

  const d = await apiCall(`/${TOKEN}/save`, {
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key: p.name, type: "photo", value: url }),
  });

  if (d && d.ok) {
    p.image_url = url;
    syncProduct(p);
    // Обновить превью на карточке — URL новый, cache-buster не нужен
    const card = peState.card;
    if (card) {
      const photoBox = card.querySelector(".pcard-photo");
      const editBtn = photoBox.querySelector(".pcard-edit-photo");
      photoBox.innerHTML = `<img src="${esc(url)}" alt="${esc(p.name)}" loading="lazy" decoding="async">`;
      if (editBtn) photoBox.appendChild(editBtn);
    }
    if (peState.cardStatus) peState.cardStatus("ok", "Подгонка сохранена ✓");
    toast("ok", "Подгонка сохранена ✓");
    closePhotoEditor();
  } else {
    saveBtn.disabled = false;
    if (peState.cardStatus) peState.cardStatus("err", "Не сохранено");
    toast("err", (d && d.message) || "Не удалось сохранить подгонку. Попробуйте ещё раз.");
  }
}

/* ── Привязка контролов редактора (один раз при загрузке страницы) ── */
function initPhotoEditor() {
  document.getElementById("pe-rot-left").addEventListener("click", () => peRotate(-90));
  document.getElementById("pe-rot-right").addEventListener("click", () => peRotate(90));
  // − влево (отдалить): позиция −8; + вправо (приблизить): позиция +8
  document.getElementById("pe-zoom-out").addEventListener("click", () => peSetZoomPos(peState.zoomPos - PE_POS_STEP));
  document.getElementById("pe-zoom-in").addEventListener("click", () => peSetZoomPos(peState.zoomPos + PE_POS_STEP));
  document.getElementById("pe-zoom").addEventListener("input", e => peSetZoomPos(parseInt(e.target.value, 10)));
  document.getElementById("pe-cancel").addEventListener("click", closePhotoEditor);
  document.getElementById("pe-save").addEventListener("click", peSaveAndUpload);

  // Закрытие по тапу вне диалога (по фону)
  document.getElementById("photo-editor").addEventListener("click", e => {
    if (e.target.id === "photo-editor") closePhotoEditor();
  });

  // Закрытие по Esc
  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && document.getElementById("photo-editor").classList.contains("open")) {
      closePhotoEditor();
    }
  });
}

/* ──────────────────────────────────────────────────────────────────
   ВОЗВРАТ НА ТО ЖЕ МЕСТО (позиция прокрутки + фильтр)
   Сохраняем scrollY (debounce ~300мс) и активный фильтр в localStorage,
   восстанавливаем после первого render в loadProducts.
   ────────────────────────────────────────────────────────────────── */

// Сохранить текущую позицию прокрутки (вызывается и из debounce, и из действий)
function saveScrollPos() {
  try { localStorage.setItem("admin_scroll", String(window.scrollY)); } catch (e) {}
}

// Сохранить активный фильтр
function saveFilter() {
  try { localStorage.setItem("admin_last_filter", activeFilter); } catch (e) {}
}

// Восстановить фильтр из localStorage (переопределяет стартовый «Все», только если сохранён)
function restoreFilter() {
  let saved = null;
  try { saved = localStorage.getItem("admin_last_filter"); } catch (e) {}
  if (!saved) return;
  // Проверяем, что такая вкладка существует
  const tab = document.querySelector(`.filter-tab[data-filter="${saved}"]`);
  if (!tab) return;
  document.querySelectorAll(".filter-tab").forEach(t => t.classList.remove("active"));
  tab.classList.add("active");
  activeFilter = saved;
}

// Восстановить позицию прокрутки (после отрисовки карточек)
function restoreScrollPos() {
  let y = null;
  try { y = localStorage.getItem("admin_scroll"); } catch (e) {}
  if (y === null) return;
  const val = parseInt(y, 10);
  if (!isNaN(val)) window.scrollTo(0, val);
}

// Слушатель прокрутки с debounce ~300мс
let scrollTimer = null;
window.addEventListener("scroll", () => {
  clearTimeout(scrollTimer);
  scrollTimer = setTimeout(saveScrollPos, 300);
});

/* ── Загрузка товаров ── */
async function loadProducts() {
  toast("info", "Загружаем список товаров...");
  try {
    const r = await fetch(`/${TOKEN}/products`);
    const d = await r.json();
    allProducts = d.products || [];
    // Восстановить сохранённый фильтр ДО первого render (если сохранён)
    restoreFilter();
    render();
    document.getElementById("toast").style.display = "none";
    // Прокрутить к сохранённой позиции ПОСЛЕ отрисовки (когда высота уже верная).
    // requestAnimationFrame — дать браузеру применить layout перед scrollTo.
    requestAnimationFrame(() => requestAnimationFrame(restoreScrollPos));
  } catch (e) {
    toast("err", "Не удалось загрузить товары. Проверьте соединение.");
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
  saveFilter();        // запомнить выбранный фильтр для возврата на место
  saveScrollPos();
  render();
});

/* ── Переключатель вида (Сетка / Список) ── */
document.getElementById("view-toggle").addEventListener("click", e => {
  const btn = e.target.closest("button[data-view]");
  if (!btn) return;
  activeView = btn.dataset.view;
  localStorage.setItem("admin_view", activeView);
  updateViewButtons();
  updateDensityUI();
  render();
});

function updateViewButtons() {
  document.querySelectorAll("#view-toggle button").forEach(b => {
    b.classList.toggle("active", b.dataset.view === activeView);
  });
}

/* ── Регулятор плотности сетки (Крупно / Средне / Мелко) ── */
document.getElementById("density-toggle").addEventListener("click", e => {
  const btn = e.target.closest("button[data-density]");
  if (!btn) return;
  activeDensity = btn.dataset.density;
  localStorage.setItem("admin_density", activeDensity);
  updateDensityUI();
  render(); // перерисовка — чтобы текст кнопки фото обновился под уровень
});

// Обновить вид регулятора: подсветить активную кнопку и скрыть его в «Списке»
function updateDensityUI() {
  const toggle = document.getElementById("density-toggle");
  // Плотность нужна только в сетке — в списке прячем контрол
  toggle.classList.toggle("hidden", activeView !== "grid");
  toggle.querySelectorAll("button").forEach(b => {
    b.classList.toggle("active", b.dataset.density === activeDensity);
  });
}

// Текст кнопки фото в зависимости от уровня плотности.
// hasPhoto — true если у товара уже есть фото (тогда «Заменить»), иначе «Добавить».
function photoButtonLabel(hasPhoto) {
  if (activeDensity === "s") return "📷"; // Мелко — только иконка
  if (activeDensity === "m") return "📷 Фото"; // Средне — коротко
  return hasPhoto ? "📷 Заменить фото" : "📷 Добавить фото"; // Крупно — полностью
}

/* ── Живой поиск с debounce 300ms ── */
document.getElementById("search-input").addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => render(), 300);
});

/* ── Инициализация ── */
updateViewButtons();
updateDensityUI();
initPhotoEditor();   // привязать контролы редактора фото один раз
loadProducts();
</script>
</body>
</html>"""
