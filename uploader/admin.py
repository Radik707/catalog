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


def _load_structure() -> dict:
    """Загрузить карту структуры из scripts/structure_map.json → { "Раздел": ["Подгруппа", ...] }.

    В панели нужны только имена разделов и подгрупп (без списка категорий) и в порядке карты —
    они наполняют две зависимые выпадашки на карточке товара (этап 7).
    Graceful-fallback: при любой ошибке (нет файла / битый JSON) → пустой dict,
    карточка просто покажет пустые списки, панель не падает.
    """
    structure_path = SCRIPT_DIR.parent / "scripts" / "structure_map.json"
    try:
        with open(structure_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        # Оставляем только имена подгрупп (ключи), порядок сохраняется (dict упорядочен)
        return {section: list(subgroups.keys()) for section, subgroups in raw.items()}
    except Exception as e:  # noqa: BLE001
        log.warning("Не удалось загрузить structure_map.json: %s — выпадашки структуры будут пустыми", e)
        return {}


# Карта структуры Раздел→[Подгруппы] и её JSON для внедрения в страницу (этап 7)
STRUCTURE = _load_structure()
# ensure_ascii=False — кириллица читаемо ложится в JS-литерал (страница в UTF-8)
STRUCTURE_JSON = json.dumps(STRUCTURE, ensure_ascii=False)


def _load_structure_full() -> dict:
    """Полная 3-уровневая карта Раздел→Подгруппа→[Категории] для редактора порядка (Работа 2).

    В отличие от _load_structure (только имена подгрупп) сохраняет и список категорий —
    редактор порядка переставляет все три уровня. Порядок ключей сохраняется (dict упорядочен).
    Graceful-fallback: любая ошибка → пустой dict, редактор просто покажет пустое дерево.
    """
    structure_path = SCRIPT_DIR.parent / "scripts" / "structure_map.json"
    try:
        with open(structure_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        log.warning("Не удалось загрузить structure_map.json (полную): %s", e)
        return {}


# Полная карта с категориями и её JSON для редактора порядка (Работа 2)
STRUCTURE_FULL = _load_structure_full()
STRUCTURE_FULL_JSON = json.dumps(STRUCTURE_FULL, ensure_ascii=False)

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
    return (PAGE.replace("__TOKEN__", token)
                .replace("__STRUCTURE_FULL__", STRUCTURE_FULL_JSON)
                .replace("__STRUCTURE__", STRUCTURE_JSON))


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

    # Белый список типов правок: group + name + photo + badge + подгруппа (этап 7) + скрыт (этап 8, T-08-05)
    SAVE_ALLOWED_TYPES = {"group", "name", "photo", "badge", "подгруппа", "скрыт"}
    if edit_type not in SAVE_ALLOWED_TYPES:
        return jsonify(
            ok=False,
            message="Не удалось сохранить правку. Неподдерживаемый тип правки.",
        ), 400

    # Значение обязательно для group и name; для photo, badge и скрыт допустимо пустое
    # (photo — сброс привязки; badge — снятие метки; скрыт — снятие скрытия, value="")
    if not value and edit_type not in ("photo", "badge", "скрыт"):
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


# ── Настройки оформления сайта ──

# Белый список ключей цвета цены — синхронизирован с lib/priceColors.ts на фронте.
ALLOWED_PRICE_COLORS = {"black", "violet", "green", "blue", "red"}


@admin_bp.get("/<token>/settings")
def admin_get_settings(token: str):
    """Текущие настройки сайта (вкладка «Настройки») → JSON. Graceful: {} при ошибке."""
    check_admin(token)
    try:
        rc, output = _run_py(SHEET_HELPER, "get_settings")
    except Exception as e:  # noqa: BLE001
        log.warning("admin /settings: ошибка запуска sheet_helper: %s", e)
        return jsonify({})
    if rc != 0:
        log.warning("sheet_helper get_settings rc=%d: %s", rc, output.strip()[-200:])
        return jsonify({})
    try:
        lines = [l.strip() for l in output.strip().splitlines() if l.strip().startswith("{")]
        return jsonify(json.loads(lines[-1] if lines else "{}"))
    except (json.JSONDecodeError, IndexError):
        return jsonify({})


@admin_bp.post("/<token>/setting")
def admin_set_setting(token: str):
    """Записать настройку оформления. Сейчас поддержан только price_color.

    Принимает JSON: {key: "price_color", value: "violet"|...}.
    Значение цвета проверяется по белому списку ALLOWED_PRICE_COLORS.
    """
    check_admin(token)

    data = request.get_json(silent=True) or {}
    key = str(data.get("key", "")).strip()
    value = str(data.get("value", "")).strip()

    if key != "price_color":
        return jsonify(ok=False, message="Неизвестная настройка."), 400
    if value not in ALLOWED_PRICE_COLORS:
        return jsonify(ok=False, message="Недопустимый цвет."), 400

    try:
        rc, output = _run_py(SHEET_HELPER, "set_setting", "--key", key, "--value", value)
    except Exception as e:  # noqa: BLE001
        log.warning("admin /setting: ошибка запуска sheet_helper: %s", e)
        return jsonify(ok=False, message="Не удалось сохранить. Попробуйте ещё раз."), 500
    if rc != 0:
        log.warning("sheet_helper set_setting rc=%d: %s", rc, output.strip()[-200:])
        return jsonify(ok=False, message="Не удалось сохранить. Попробуйте ещё раз."), 500

    return jsonify(ok=True, message="Цвет цены сохранён. На сайте обновится в течение минуты.")


def _validate_catalog_order(data: dict) -> bool:
    """Проверить структуру порядка каталога перед записью (Работа 2).

    Ждём: {"sections": [str], "subgroups": {str: [str]}, "categories": {str: [str]}}.
    Любой уровень необязателен, но если есть — типы должны совпадать. Защита от мусора
    в ячейке настроек (её потом читает upload.py).
    """
    if not isinstance(data, dict):
        return False
    sections = data.get("sections", [])
    subgroups = data.get("subgroups", {})
    categories = data.get("categories", {})
    if not isinstance(sections, list) or not all(isinstance(s, str) for s in sections):
        return False
    for mapping in (subgroups, categories):
        if not isinstance(mapping, dict):
            return False
        for k, v in mapping.items():
            if not isinstance(k, str) or not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                return False
    return True


@admin_bp.post("/<token>/catalog-order")
def admin_set_catalog_order(token: str):
    """Сохранить пользовательский порядок витрины (Работа 2).

    Принимает JSON {sections, subgroups, categories}. Валидирует структуру, пишет её
    JSON-строкой в ячейку «catalog_order» вкладки «Настройки» через sheet_helper.
    upload.py применит порядок при ближайшем прогоне («Применить сейчас» / загрузка прайсов).
    """
    check_admin(token)

    data = request.get_json(silent=True) or {}
    if not _validate_catalog_order(data):
        return jsonify(ok=False, message="Неверный формат порядка."), 400

    # Компактный JSON (без пробелов) — экономим место в ячейке
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    # Предел ячейки Google Sheets — 50000 символов; наш JSON много меньше, но проверим
    if len(payload) > 45000:
        return jsonify(ok=False, message="Порядок слишком большой для сохранения."), 400

    try:
        rc, output = _run_py(SHEET_HELPER, "set_setting", "--key", "catalog_order", "--value", payload)
    except Exception as e:  # noqa: BLE001
        log.warning("admin /catalog-order: ошибка запуска sheet_helper: %s", e)
        return jsonify(ok=False, message="Не удалось сохранить порядок. Попробуйте ещё раз."), 500
    if rc != 0:
        log.warning("sheet_helper set_setting(catalog_order) rc=%d: %s", rc, output.strip()[-200:])
        return jsonify(ok=False, message="Не удалось сохранить порядок. Попробуйте ещё раз."), 500

    return jsonify(ok=True, message="Порядок сохранён. Нажмите «Применить сейчас», чтобы обновить сайт.")


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
  .pcard-group,
  .pcard-section,
  .pcard-subgroup { width: 100%; font-size: 14px; min-height: 44px; padding-right: 26px; }

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

  /* ── Липкая верхняя полоска ──
     Закреплена сверху (sticky) и всегда видна при прокрутке списка. */
  .sticky-bar {
    position: sticky;
    top: 0;
    z-index: 50;
    background: #fff;
    box-shadow: 0 2px 6px rgba(0,0,0,.06);
    /* растянуть на всю ширину контейнера, компенсируя его боковые padding */
    margin-left: -12px;
    margin-right: -12px;
    padding: 10px 12px;
  }
  .sticky-bar-inner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;          /* на телефоне переносится без поломки */
    gap: 10px;
  }
  .sticky-bar-title h1 { font-size: 18px; }

  /* Кнопка «Применить сейчас» — компактная, но тач-цель ≥40px */
  .btn-apply { min-height: 40px; font-size: 15px; font-weight: 600; padding: 6px 18px; flex-shrink: 0; }

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
  .view-grid.density-l .pcard-group,
  .view-grid.density-l .pcard-section,
  .view-grid.density-l .pcard-subgroup { font-size: 14px; min-height: 44px; padding-right: 26px; }
  .view-grid.density-m .pcard-group,
  .view-grid.density-m .pcard-section,
  .view-grid.density-m .pcard-subgroup { font-size: 11.5px; min-height: 32px; padding: 3px 22px 3px 6px; }
  .view-grid.density-s .pcard-group,
  .view-grid.density-s .pcard-section,
  .view-grid.density-s .pcard-subgroup { font-size: 11px;   min-height: 28px; padding: 2px 20px 2px 5px; }

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

  /* Кнопка-глазик «👁» в левом верхнем углу фото (этап 8, скрытие).
     Размещена слева — карандаш кадрирования занимает right:4px (D-04).
     Зона нажатия 44px — увеличена относительно карандаша (D-05). */
  .pcard-eye {
    position: absolute; top: 4px; left: 4px;
    width: 44px; height: 44px; min-width: 44px;
    display: flex; align-items: center; justify-content: center;
    border: 0; border-radius: 8px; cursor: pointer;
    background: rgba(255,255,255,0.85); color: #374151; font-size: 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.18); padding: 0; line-height: 1;
  }
  .pcard-eye:hover { background: #fff; }
  /* Компактный вариант для плотности «Мелко» — пропорционально образцу карандаша */
  .view-grid.density-s .pcard-eye { width: 36px; height: 36px; min-width: 36px; font-size: 16px; }

  /* Скрытая карточка тускнеет (D-01): остаётся интерактивной — NO pointer-events:none */
  .pcard.hidden { opacity: 0.45; }

  /* Чип «скрыт» — по образцу .badge-attn (D-02) */
  .badge-hidden { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1;
                  font-weight: 600; padding: 2px 8px; border-radius: 6px; font-size: 13px; }

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
     Внутри <img> с ЖИВЫМ CSS-transform (pan/zoom). Cloudinary-кроп
     собирается только при сохранении — превью плавное, без перезагрузок. */
  .pe-frame {
    position: relative; width: 100%; aspect-ratio: 1 / 1;
    background: #fff; border: 2px solid #2563eb; border-radius: 10px;
    overflow: hidden;
    touch-action: none;              /* свой drag пальцем, без скролла страницы */
    cursor: grab;
  }
  .pe-frame.pe-dragging { cursor: grabbing; }
  /* Превью позиционируется абсолютно; размеры/смещение задаёт JS.
     object-fit НЕ используем — масштаб «contain» считаем сами в пикселях. */
  .pe-frame img {
    position: absolute; left: 0; top: 0;
    transform-origin: center center;
    user-select: none; -webkit-user-drag: none; pointer-events: none;
    max-width: none; max-height: none;
  }

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

  /* ── Оформление: выбор цвета цены на карточках сайта ── */
  /* Кнопка-триггер «Оформление» в панели инструментов (рядом с видом) */
  .appearance-btn { min-height: 40px; padding: 6px 14px; border-radius: 8px;
                    border: 1px solid #d1d5db; background: #fff; cursor: pointer;
                    font-size: 14px; color: #374151; display: inline-flex;
                    align-items: center; gap: 6px; }
  .appearance-btn:hover { background: #f9fafb; }

  /* Полупрозрачная подложка за шторкой (перехватывает клик «мимо» → закрыть) */
  .drawer-overlay { position: fixed; inset: 0; background: rgba(17,24,39,.4);
                    z-index: 1100; opacity: 0; visibility: hidden;
                    transition: opacity .2s ease, visibility .2s ease; }
  .drawer-overlay.open { opacity: 1; visibility: visible; }

  /* Выезжающая справа шторка настроек оформления */
  .drawer { position: fixed; top: 0; right: 0; bottom: 0; width: 320px; max-width: 88vw;
            background: #fff; z-index: 1101; box-shadow: -8px 0 32px rgba(0,0,0,.18);
            transform: translateX(100%); transition: transform .24s ease;
            display: flex; flex-direction: column; }
  .drawer.open { transform: translateX(0); }
  .drawer-head { display: flex; align-items: center; justify-content: space-between;
                 padding: 16px; border-bottom: 1px solid #e5e7eb; }
  .drawer-title { font-size: 16px; font-weight: 600; color: #111827; margin: 0; }
  .drawer-close { border: none; background: #f3f4f6; border-radius: 8px; width: 36px;
                  height: 36px; font-size: 20px; line-height: 1; cursor: pointer;
                  color: #374151; }
  .drawer-close:hover { background: #e5e7eb; }
  .drawer-body { padding: 16px; overflow-y: auto; }
  .drawer-section-label { font-size: 13px; color: #6b7280; font-weight: 600;
                          margin: 0 0 10px; text-transform: uppercase;
                          letter-spacing: .02em; }

  .price-colors { display: flex; flex-direction: column; gap: 8px; }
  /* Кнопка-образец: цветной кружок + подпись, тач-цель ≥40px */
  .pcolor { display: inline-flex; align-items: center; gap: 8px; cursor: pointer;
            min-height: 44px; padding: 6px 14px 6px 10px; border-radius: 999px;
            border: 2px solid #e5e7eb; background: #fff; font-size: 14px; color: #374151;
            width: 100%; }
  .pcolor .dot { width: 20px; height: 20px; border-radius: 50%; flex-shrink: 0;
                 border: 1px solid rgba(0,0,0,.1); }
  /* Активный цвет — синяя обводка (как у других активных кнопок панели) */
  .pcolor.active { border-color: #2563eb; background: #eff6ff; color: #1e40af; font-weight: 600; }

  /* ── Редактор порядка каталога (Работа 2): полноэкранная модалка ── */
  .order-editor { position: fixed; inset: 0; z-index: 1200; background: #f3f4f6;
                  display: none; flex-direction: column; }
  .order-editor.open { display: flex; }
  .oe-head { display: flex; align-items: center; gap: 10px; padding: 12px 16px;
             background: #fff; border-bottom: 1px solid #e5e7eb; }
  .oe-title { font-size: 16px; font-weight: 600; color: #111827; margin: 0; flex: 1; }
  .oe-btn { min-height: 40px; padding: 8px 16px; border-radius: 8px; border: 1px solid #d1d5db;
            background: #fff; cursor: pointer; font-size: 14px; color: #374151; }
  .oe-save { background: #2563eb; color: #fff; border-color: #2563eb; font-weight: 600; }
  .oe-save:disabled { opacity: .6; cursor: default; }
  .oe-body { flex: 1; overflow-y: auto; padding: 12px 12px 40px; }
  .oe-hint { font-size: 13px; color: #6b7280; margin: 0 0 12px; padding: 0 4px; }

  /* Узел дерева (раздел/подгруппа/категория) */
  .ord-node { display: flex; align-items: center; gap: 8px; background: #fff;
              border: 1px solid #e5e7eb; border-radius: 10px; padding: 10px 10px;
              margin-bottom: 6px; touch-action: none; }
  .ord-node.ord-section  { border-left: 4px solid #2563eb; font-weight: 600; }
  .ord-node.ord-subgroup { border-left: 4px solid #16a34a; }
  .ord-node.ord-category { border-left: 4px solid #d1d5db; font-size: 14px; }
  /* Уровни-контейнеры детей — отступ слева */
  .ord-children { margin-left: 16px; }
  .ord-children.collapsed { display: none; }
  /* Ручка перетаскивания */
  .ord-handle { cursor: grab; color: #9ca3af; font-size: 18px; line-height: 1;
                padding: 4px 2px; touch-action: none; user-select: none; flex-shrink: 0; }
  .ord-name { flex: 1; color: #111827; line-height: 1.25; min-width: 0;
              overflow-wrap: anywhere; }
  /* Стрелки вверх/вниз и раскрытие */
  .ord-arrows { display: flex; gap: 2px; flex-shrink: 0; }
  .ord-arrow, .ord-toggle { border: 1px solid #e5e7eb; background: #f9fafb; border-radius: 6px;
               width: 34px; height: 34px; font-size: 16px; line-height: 1; cursor: pointer;
               color: #374151; display: inline-flex; align-items: center; justify-content: center;
               flex-shrink: 0; }
  .ord-arrow:disabled { opacity: .35; cursor: default; }
  .ord-toggle { width: 30px; }
  .ord-count { font-size: 12px; color: #9ca3af; flex-shrink: 0; }

  /* Плавающий «призрак» при перетаскивании (общий для Работ 2 и 3) */
  .drag-ghost { position: fixed; z-index: 1400; pointer-events: none; opacity: .95;
                box-shadow: 0 10px 30px rgba(0,0,0,.25); border-radius: 10px;
                transform: translate(-50%, -50%); }
  /* Место, откуда взяли элемент (полупрозрачная «дырка») */
  .drag-source { opacity: .35; }
</style>
</head>
<body>
<div class="container py-3" style="max-width:1200px">

  <!-- ── Липкая верхняя полоска: заголовок + «Применить сейчас» ──
       position: sticky → остаётся на виду при прокрутке списка товаров,
       чтобы кнопку «Применить сейчас» можно было нажать в любой момент. -->
  <div class="sticky-bar mb-3">
    <div class="sticky-bar-inner">
      <div class="sticky-bar-title">
        <h1 class="h5 mb-0">Вкусный Дом — Панель управления</h1>
        <p class="text-muted mb-0" style="font-size:13px">Товары и правки</p>
      </div>
      <!-- Кнопка «Применить сейчас» — компактная, тач-цель ≥40px,
           id и onclick сохранены (функция applyNow не менялась). -->
      <button id="btn-apply" class="btn btn-primary btn-apply" onclick="applyNow()">
        Применить сейчас
      </button>
    </div>
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
      <button class="filter-tab" data-filter="hidden">Скрытые</button>
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
      <!-- Триггер выезжающей шторки оформления сайта -->
      <button type="button" class="appearance-btn" id="appearance-btn"
              onclick="openDrawer()">🎨 Оформление</button>
    </div>
  </div>

  <!-- Сетка/список карточек товаров -->
  <div id="products" class="view-grid"></div>

  <!-- Статусный баннер «Применить сейчас» -->
  <div id="status" class="status mb-5"></div>

</div><!-- /container -->

<!-- ── Выезжающая шторка «Оформление сайта» ──
     Триггер — кнопка «🎨 Оформление» в панели инструментов. Внутри — общие
     настройки внешнего вида витрины (сейчас цвет цены; задел под будущие). -->
<div class="drawer-overlay" id="drawer-overlay" onclick="closeDrawer()"></div>
<aside class="drawer" id="appearance-drawer" aria-hidden="true"
       role="dialog" aria-modal="true" aria-label="Оформление сайта">
  <div class="drawer-head">
    <h2 class="drawer-title">Оформление сайта</h2>
    <button type="button" class="drawer-close" onclick="closeDrawer()"
            aria-label="Закрыть">×</button>
  </div>
  <div class="drawer-body">
    <p class="drawer-section-label">Цвет цены на карточках</p>
    <div id="price-colors" class="price-colors"></div>

    <hr style="margin:20px 0;border:none;border-top:1px solid #e5e7eb">

    <p class="drawer-section-label">Порядок каталога</p>
    <p style="font-size:13px;color:#6b7280;margin:0 0 10px">
      Перетащите разделы, подгруппы и категории в нужном порядке — так они и встанут на сайте.
    </p>
    <button type="button" class="btn btn-outline-primary w-100" onclick="openOrderEditor()">
      Изменить порядок
    </button>
  </div>
</aside>

<!-- ── Редактор порядка каталога (Работа 2) ──
     Полноэкранная модалка: дерево Раздел→Подгруппа→Категория. Каждый узел можно
     двигать среди соседей стрелками ▲▼ или перетаскиванием за ручку ≡. «Сохранить» —
     порядок пишется в «Настройки», применяется на сайте после «Применить сейчас». -->
<div class="order-editor" id="order-editor" aria-hidden="true" role="dialog" aria-modal="true">
  <div class="oe-head">
    <button type="button" class="oe-btn" onclick="closeOrderEditor()">Отмена</button>
    <h2 class="oe-title">Порядок каталога</h2>
    <button type="button" class="oe-btn oe-save" id="oe-save-btn" onclick="saveOrder()">Сохранить</button>
  </div>
  <div class="oe-body">
    <p class="oe-hint">Двигайте разделы, подгруппы и категории стрелками или перетаскиванием за ручку ≡. Нажмите ▸ чтобы раскрыть.</p>
    <div id="ord-tree"></div>
  </div>
</div>

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

// Карта двухуровневой структуры: { "Раздел": ["Подгруппа1", ...] } (этап 7).
// Внедряется сервером из scripts/structure_map.json (json.dumps, ensure_ascii=False).
// Наполняет две зависимые выпадашки «Раздел» / «Подгруппа» на карточке товара.
const STRUCTURE = __STRUCTURE__;
// Полная карта Раздел→Подгруппа→[Категории] для редактора порядка (Работа 2).
const STRUCTURE_FULL = __STRUCTURE_FULL__;
// Обратный индекс: подгруппа → раздел (для предвыбора раздела по сохранённой подгруппе).
const SUBGROUP_TO_SECTION = {};
Object.keys(STRUCTURE).forEach(sec => {
  (STRUCTURE[sec] || []).forEach(sg => {
    if (!(sg in SUBGROUP_TO_SECTION)) SUBGROUP_TO_SECTION[sg] = sec;
  });
});

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
    // Фильтр «Скрытые» (этап 8, D-08/D-09): только скрытые товары; совместно с поиском
    else if (activeFilter === "hidden")   matchFilter = !!p.hidden;
    // «Все» (по умолчанию): показываем ВСЕ товары, скрытые — тусклыми (D-08, class .pcard.hidden)
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
  // Скрытый товар получает класс hidden → тускнеет (D-01, .pcard.hidden)
  card.className = p.hidden ? "pcard hidden" : "pcard";
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

  // Кнопка-глазик (этап 8): открытый глаз → клик скрывает; закрытый → клик возвращает (D-03)
  // Размещена в левом верхнем углу фото, чтобы не перекрывать карандаш справа (D-04)
  const eyeGlyph = p.hidden ? "&#128584;" : "&#128065;";
  const eyeTitle = p.hidden ? "Вернуть товар в каталог" : "Скрыть товар из каталога";
  const eyeBtn = `<button class="pcard-eye" type="button" title="${eyeTitle}">${eyeGlyph}</button>`;

  // ── Бейджи и подписи ──
  // Метку «новинка»/«хит» показывает ТОЛЬКО кнопка NEW/Хит своим зелёным
  // состоянием (по p.badge). Текстовый бейдж метки на карточке НЕ рисуем,
  // чтобы не было дублирования. Здесь — индикатор «требует внимания» + чип «скрыт».
  let badges = "";
  if (!p.group || !p.image_url) badges += '<span class="badge-attn">&#9888;</span>';
  // Чип «скрыт» — виден пока товар скрыт, во всех режимах плотности и видов (D-02)
  if (p.hidden) badges += '<span class="badge-hidden">скрыт</span>';

  const hints = [];
  if (!p.group)     hints.push("Без группы");
  if (!p.image_url) hints.push("Без фото");
  const hintsHtml = hints.length
    ? `<div class="pcard-hints">${esc(hints.join(" · "))}</div>` : "";

  // ── Отображаемое имя ──
  const shownName = p.display_name || p.name;

  // ── Зависимые выпадашки «Раздел» → «Подгруппа» (этап 7) ──
  // Раздел предвыбираем по p.section; если он пуст, но подгруппа известна —
  // восстанавливаем раздел по обратному индексу SUBGROUP_TO_SECTION.
  const sections = Object.keys(STRUCTURE);
  let curSection = p.section || (p.subgroup ? SUBGROUP_TO_SECTION[p.subgroup] : "") || "";

  // Опции раздела
  let sectionOpts = '<option value="">Выберите раздел...</option>';
  sections.forEach(s => {
    const sel = (curSection === s) ? " selected" : "";
    sectionOpts += `<option${sel}>${esc(s)}</option>`;
  });

  // Опции подгруппы текущего раздела (если раздел выбран)
  let subgroupOpts = '<option value="">Выберите подгруппу...</option>';
  (STRUCTURE[curSection] || []).forEach(sg => {
    const sel = (p.subgroup === sg) ? " selected" : "";
    subgroupOpts += `<option${sel}>${esc(sg)}</option>`;
  });

  // ── Кнопка фото ──
  // Текст зависит от уровня плотности: на «Мелко» — короткая иконка/«Фото»,
  // на «Средне» — «Фото», на «Крупно» — полный «Заменить/Добавить фото».
  const photoBtnLabel = photoButtonLabel(!!p.image_url);

  // ── Кнопки-переключатели меток: активная (зелёная) если совпадает с p.badge ──
  const newActive = (p.badge === "новинка") ? " active" : "";
  const hitActive = (p.badge === "хит") ? " active" : "";

  card.innerHTML = `
    <div class="pcard-photo">${photoHtml}${editPhotoBtn}${eyeBtn}</div>
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
      <select class="form-select pcard-section">${sectionOpts}</select>
      <select class="form-select pcard-subgroup">${subgroupOpts}</select>
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

  // ── Зависимые выпадашки «Раздел» → «Подгруппа» (этап 7) ──
  const sectionSel = card.querySelector(".pcard-section");
  const subgroupSel = card.querySelector(".pcard-subgroup");

  // Перезаполнить список подгрупп под выбранный раздел.
  // selected — какую подгруппу предвыбрать (или "" чтобы сбросить на плейсхолдер).
  function fillSubgroups(section, selected) {
    let opts = '<option value="">Выберите подгруппу...</option>';
    (STRUCTURE[section] || []).forEach(sg => {
      const sel = (selected === sg) ? " selected" : "";
      opts += `<option${sel}>${esc(sg)}</option>`;
    });
    subgroupSel.innerHTML = opts;
  }

  // Смена РАЗДЕЛА: только пересобираем список подгрупп (подгруппа сбрасывается).
  // Правка НЕ отправляется — товар переносится лишь при выборе конкретной подгруппы.
  sectionSel.addEventListener("change", () => {
    fillSubgroups(sectionSel.value, "");
  });

  // Смена ПОДГРУППЫ: отправляем правку type="подгруппа", оптимистично обновляем товар.
  subgroupSel.addEventListener("change", async () => {
    const value = subgroupSel.value;
    if (!value) return; // «Выберите подгруппу...» — ничего не делаем
    saveScrollPos();    // место = эта карточка
    cardStatus("", "Сохраняем...");
    const d = await apiCall(`/${TOKEN}/save`, {
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: p.name, type: "подгруппа", value: value }),
    });
    if (d && d.ok) {
      p.subgroup = value;
      p.section = sectionSel.value;   // раздел = текущий выбранный
      syncProduct(p);
      cardStatus("ok", "Сохранено ✓");
      toast("ok", "Подгруппа сохранена ✓");
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

  // ── Кнопка-глазик: оптимистичное скрытие/возврат товара (этап 8, SP-4) ──
  // Строго по образцу toggleBadge: сохранить prev → применить → apiCall → откат при ошибке.
  const eyeEl = card.querySelector(".pcard-eye");
  if (eyeEl) {
    eyeEl.addEventListener("click", async () => {
      await toggleHidden();
    });
  }

  // Оптимистичный переключатель скрытия (D-06: БЕЗ диалога подтверждения)
  async function toggleHidden() {
    const prev = p.hidden;                      // запомнить для отката при ошибке
    const next = !p.hidden;

    saveScrollPos();
    // Оптимистично: сразу применить изменение
    p.hidden = next;
    syncProduct(p);
    // Переключить класс карточки, глиф и title кнопки
    card.classList.toggle("hidden", next);
    eyeEl.innerHTML = next ? "&#128584;" : "&#128065;";
    eyeEl.title     = next ? "Вернуть товар в каталог" : "Скрыть товар из каталога";
    // Показать/скрыть чип «скрыт» в .pcard-badges
    const badgesEl = card.querySelector(".pcard-badges");
    const hiddenChip = badgesEl ? badgesEl.querySelector(".badge-hidden") : null;
    if (next) {
      if (badgesEl && !hiddenChip) {
        const chip = document.createElement("span");
        chip.className = "badge-hidden";
        chip.textContent = "скрыт";
        badgesEl.appendChild(chip);
      }
    } else {
      if (hiddenChip) hiddenChip.remove();
    }
    eyeEl.disabled = true;
    cardStatus("", "Сохраняем...");

    const d = await apiCall(`/${TOKEN}/save`, {
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: p.name, type: "скрыт", value: next ? "1" : "" }),
    });

    eyeEl.disabled = false;
    if (d && d.ok) {
      cardStatus("ok", next ? "Товар скрыт ✓" : "Товар возвращён ✓");
      toast("ok",  next ? "Товар скрыт из каталога ✓" : "Товар возвращён в каталог ✓");
    } else {
      // Откат к прежнему состоянию
      p.hidden = prev;
      syncProduct(p);
      card.classList.toggle("hidden", prev);
      eyeEl.innerHTML = prev ? "&#128584;" : "&#128065;";
      eyeEl.title     = prev ? "Вернуть товар в каталог" : "Скрыть товар из каталога";
      // Откат чипа
      const badgesEl2 = card.querySelector(".pcard-badges");
      const chip2 = badgesEl2 ? badgesEl2.querySelector(".badge-hidden") : null;
      if (prev) {
        if (badgesEl2 && !chip2) {
          const c = document.createElement("span");
          c.className = "badge-hidden"; c.textContent = "скрыт";
          badgesEl2.appendChild(c);
        }
      } else {
        if (chip2) chip2.remove();
      }
      cardStatus("err", "Не сохранено");
      toast("err", (d && d.message) || "Не удалось изменить видимость. Попробуйте ещё раз.");
    }
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
      // Перерисовываем ТОЛЬКО эту карточку (не весь список — чтобы не сбить
      // прокрутку и состояние). Новая карточка строится через buildCard, поэтому
      // у неё сразу появляется кнопка ✎ «Кадрировать» и обновлённое фото,
      // а также рабочие обработчики (фото/название/метки/редактор).
      const idx = Number(card.dataset.idx);
      const newCard = buildCard(p, idx);
      card.replaceWith(newCard);
      // Статус показываем уже на новой карточке (у неё свой замкнутый cardStatus).
      const newStatusEl = newCard.querySelector(".pcard-status");
      if (newStatusEl) { newStatusEl.className = "pcard-status ok"; newStatusEl.textContent = "Фото сохранено ✓"; }
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

// Ползунок зума: позиция -100..100, ЦЕНТР 0 = «заполнение» (фото закрывает квадрат).
// Маппинг позиции v в фактический zoom: zoom = 3^(v/100)
//   v=0   → 1.0   (фото заполняет рамку — чистый кроп без белых полей; стартовая позиция)
//   v=100 → 3.0   (максимальное приближение — обрезка плотнее)
//   v=-100→ ~0.333 (отдаление — показать фото целиком, при необходимости с белыми полями)
const PE_POS_MIN = -100;     // крайнее левое = отдалить (показать фото целиком)
const PE_POS_MAX = 100;      // крайнее правое = приблизить (плотная обрезка)
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
  // ── Геометрия живого превью ──
  F: 0,             // сторона квадратной рамки (px, clientWidth при открытии)
  W: 0,             // naturalWidth ПОВЁРНУТОЙ картинки превью (px)
  H: 0,             // naturalHeight ПОВЁРНУТОЙ картинки превью (px)
  c: 1,             // базовый масштаб «contain» = min(F/W, F/H)
  panX: 0,          // сдвиг кадра по X (px экрана)
  panY: 0,          // сдвиг кадра по Y (px экрана)
  // ── Состояние перетаскивания ──
  dragging: false,  // идёт ли drag прямо сейчас
  dragId: null,     // pointerId активного пальца/мыши
  dragStartX: 0,    // экранные координаты старта drag
  dragStartY: 0,
  panStartX: 0,     // pan на момент старта drag
  panStartY: 0,
  // ── Состояние мультитач/пинча ──
  pointers: new Map(), // активные указатели: pointerId -> {x, y}
  pinching: false,     // идёт ли сейчас жест пинча (2 пальца)
  pinchD0: 0,          // стартовая дистанция между двумя пальцами (px)
  pinchZ0: 1,          // зум на момент начала пинча
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

/* Вставить готовую строку трансформаций сразу после `/upload/` в чистый base. */
function peInsertTransform(baseUrl, t) {
  const marker = "/upload/";
  const at = baseUrl.indexOf(marker);
  if (at < 0 || t === "") return baseUrl;
  return baseUrl.slice(0, at + marker.length) + t + baseUrl.slice(at + marker.length);
}

/* «Повёрнутый базовый» URL — для ЖИВОГО превью (только поворот, без кропа).
   deg=0 → чистый base. Загруженная картинка уже имеет повёрнутые W/H,
   поэтому контейн-масштаб считаем по её naturalWidth/Height. */
function peRotatedBaseUrl(baseUrl, deg) {
  if (deg > 0) return peInsertTransform(baseUrl, "a_" + deg + "/");
  return baseUrl;
}

/* Собрать ТОЧНЫЙ кроп Cloudinary при сохранении.
   Координаты x0,y0 и сторона S — целые ПИКСЕЛИ повёрнутой картинки
   (W,H), чтобы Cloudinary не принял их за доли.
   Геометрия совпадает с живым превью: F,c,z,panX,panY.
   - z≥1 и квадрат помещается → c_crop,x_,y_,w_,h_ + c_fill до 800.
   - z<1 (отдаление) ИЛИ S больше картинки → c_fit + c_pad на белом.
   - нейтраль (deg=0, z≈1, pan≈0) → чистый base (без трансформаций). */
function peBuildSaveUrl() {
  const base = peState.baseUrl;
  const deg  = peState.rotation;
  const z    = peState.zoom;
  const F = peState.F, c = peState.c, W = peState.W, H = peState.H;
  const panX = peState.panX, panY = peState.panY;
  const rot = deg > 0 ? ("a_" + deg + "/") : "";

  // Нейтраль: у КВАДРАТНОГО фото «заполнение» при зуме 1 = картинка целиком,
  // поэтому если ничего не трогали — отдаём пристинный оригинал (без перекодирования).
  // У несимметричного фото зум 1 = уже кроп по центру (заполнение рамки),
  // поэтому нейтраль к нему НЕ применяем — сохраняем именно то, что видно в превью.
  const isSquare = Math.abs(W - H) <= 0.01 * Math.max(W, H);
  if (deg === 0 && isSquare &&
      Math.abs(z - 1) < 0.02 &&
      Math.abs(panX) < 0.5 && Math.abs(panY) < 0.5) {
    return base;
  }

  // Геометрия защищена: если рамку не успели измерить — отдаём поворот.
  if (!(F > 0 && c > 0 && W > 0 && H > 0)) {
    return peInsertTransform(base, rot);
  }

  if (z >= 1) {
    // Сторона квадрата кропа в пикселях повёрнутой картинки.
    let S = Math.round(F / (c * z));
    if (S < 1) S = 1;
    if (S <= Math.min(W, H)) {
      // x0,y0 — левый/верхний угол кропа в пикселях; pan сдвигает кадр.
      let x0 = Math.round(W / 2 - F / (2 * c * z) - panX / (c * z));
      let y0 = Math.round(H / 2 - F / (2 * c * z) - panY / (c * z));
      x0 = Math.max(0, Math.min(x0, W - S));
      y0 = Math.max(0, Math.min(y0, H - S));
      const t = rot
        + "c_crop,x_" + x0 + ",y_" + y0 + ",w_" + S + ",h_" + S + "/"
        + "c_fill,g_center,w_" + PE_FILL + ",h_" + PE_FILL + "/";
      return peInsertTransform(base, t);
    }
    // S больше картинки — падаем в ветку «целиком на белом» ниже.
  }

  // Зум-аут / кроп не помещается: фото целиком, уменьшенное, на белом паддинге.
  const s = Math.max(1, Math.round(z * PE_FILL));
  const t = rot
    + "c_fit,w_" + s + ",h_" + s + "/"
    + "c_pad,g_center,w_" + PE_FILL + ",h_" + PE_FILL + ",b_white/";
  return peInsertTransform(base, t);
}

/* «Чистый кроп»: ограничить сдвиг (pan) так, чтобы фото ВСЕГДА полностью
   закрывало квадратную рамку — уехать за край нельзя, белых полей по краям
   не возникает. Границы сдвига совпадают с кропом при сохранении
   (peBuildSaveUrl), поэтому «что видно в превью — то и сохранится».
   Если при текущем зуме фото у́же/ниже рамки (ещё не закрывает её) —
   соответствующая ось фиксируется по центру (maxX/maxY = 0). */
function peClampPan() {
  const F = peState.F, c = peState.c, z = peState.zoom, W = peState.W, H = peState.H;
  if (!(F > 0 && c > 0 && W > 0 && H > 0)) return;
  // Макс. сдвиг по оси = насколько увеличенное фото шире/выше рамки, делённое на 2.
  const maxX = Math.max(0, (c * z * W - F) / 2);
  const maxY = Math.max(0, (c * z * H - F) / 2);
  peState.panX = Math.max(-maxX, Math.min(maxX, peState.panX));
  peState.panY = Math.max(-maxY, Math.min(maxY, peState.panY));
}

/* Применить геометрию (размер/смещение/трансформ) к <img> превью.
   width/height/left/top задают базовый «contain», а translate+scale —
   живой pan/zoom поверх него. */
function peApplyPreviewTransform() {
  const img = document.getElementById("pe-preview");
  const F = peState.F, c = peState.c, W = peState.W, H = peState.H;
  if (!(F > 0 && c > 0 && W > 0 && H > 0)) return;
  const w = W * c, h = H * c;
  img.style.width  = w + "px";
  img.style.height = h + "px";
  img.style.left = (F - w) / 2 + "px";
  img.style.top  = (F - h) / 2 + "px";
  peClampPan();                       // согласовать сдвиг с границами кропа (чистый кроп)
  img.style.transform =
    "translate(" + peState.panX + "px," + peState.panY + "px) scale(" + peState.zoom + ")";
}

/* Только трансформ (быстрый путь для drag/zoom — без пересчёта размеров). */
function peUpdateTransformOnly() {
  const img = document.getElementById("pe-preview");
  peClampPan();                       // не выпускать фото за край рамки (чистый кроп)
  img.style.transform =
    "translate(" + peState.panX + "px," + peState.panY + "px) scale(" + peState.zoom + ")";
}

/* Загрузить «повёрнутый базовый» src и после load пересчитать геометрию.
   Вызывается при открытии и при смене поворота. resetPan — обнулить сдвиг. */
function peLoadPreview(resetPan) {
  const img = document.getElementById("pe-preview");
  const frame = document.getElementById("pe-frame");
  peState.F = frame.clientWidth;            // сторона рамки (квадрат F×F)
  if (resetPan) { peState.panX = 0; peState.panY = 0; }
  img.onload = () => {
    // naturalWidth/Height уже учитывают поворот a_<deg>.
    peState.W = img.naturalWidth;
    peState.H = img.naturalHeight;
    // «Чистый кроп»: базовый масштаб = «cover» (max), чтобы фото уже при зуме 1
    // полностью закрывало квадрат даже у несимметричных снимков. Иначе кроп
    // не применялся до порога пропорций и сохранялась картинка целиком —
    // на карточке это выглядело как «вернулось к прошлой версии».
    peState.c = Math.max(peState.F / peState.W, peState.F / peState.H);
    peApplyPreviewTransform();
  };
  img.src = peRotatedBaseUrl(peState.baseUrl, peState.rotation);
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
  peState.panX = 0;        // сдвиг кадра — с нуля
  peState.panY = 0;

  document.getElementById("pe-name").textContent = p.display_name || p.name;
  document.getElementById("pe-zoom").value = 0;     // центр
  document.getElementById("pe-save").disabled = false;

  const modal = document.getElementById("photo-editor");
  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");

  // Загружаем живое превью (рамку уже видно → clientWidth корректный).
  peLoadPreview(true);
}

function closePhotoEditor() {
  const modal = document.getElementById("photo-editor");
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
  peState.product = null;
}

// Поворот на ±90°: меняем src на «повёрнутый базовый», сбрасываем pan,
// зум сохраняем; после load пересчитаем W,H,c и размеры.
function peRotate(delta) {
  peState.rotation = (peState.rotation + delta + 360) % 360;
  peLoadPreview(true);
}

// Установить зум по ПОЗИЦИИ ползунка (-100..100). 0 = центр = оригинал.
// Меняет scale(z) в живом transform — без перезагрузки картинки.
function peSetZoomPos(pos) {
  let p = Math.max(PE_POS_MIN, Math.min(PE_POS_MAX, Math.round(pos)));
  peState.zoomPos = p;
  peState.zoom = pePosToZoom(p);     // фактический зум 3^(p/100)
  document.getElementById("pe-zoom").value = p;
  peUpdateTransformOnly();
}

// Установить зум по ФАКТИЧЕСКОМУ значению (для пинча двумя пальцами).
// Зажимаем зум в [0.34, 3], синхронизируем позицию ползунка (-100..100)
// и значение слайдера, обновляем живой transform. Пишем в peState.zoom,
// чтобы сохранение (peBuildSaveUrl) учло пинч-зум.
function peSetZoom(z) {
  const zc = Math.max(0.34, Math.min(3, z));      // зажать зум: отдаление до 0.34×, приближение до 3×
  peState.zoom = zc;
  // Обратное преобразование zoom → позиция ползунка: pos = 100*log3(z)
  let pos = Math.round(100 * Math.log(zc) / Math.log(3));
  pos = Math.max(PE_POS_MIN, Math.min(PE_POS_MAX, pos));
  peState.zoomPos = pos;
  document.getElementById("pe-zoom").value = pos;
  peUpdateTransformOnly();
}

// Дистанция между двумя точками указателей (px экрана).
function pePointerDist(a, b) {
  const dx = a.x - b.x, dy = a.y - b.y;
  return Math.hypot(dx, dy);
}

// Сохранить подгонку: записать готовый URL через /save (type=photo)
async function peSaveAndUpload() {
  const p = peState.product;
  if (!p) return;
  const saveBtn = document.getElementById("pe-save");
  saveBtn.disabled = true;

  const url = peBuildSaveUrl();      // живой pan/zoom → точный кроп Cloudinary
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

  // ── Перетаскивание (pan) и пинч-зум через Pointer Events ──
  // Ведём реестр активных указателей (peState.pointers): один палец = pan,
  // два пальца = пинч-зум (приближать/отдалять щипком). touch-action:none
  // на .pe-frame не даёт жесту скроллить страницу.
  const frame = document.getElementById("pe-frame");

  // Начать pan по ОДНОМУ оставшемуся/первому указателю с текущей позиции
  // (без рывка). Используется на pointerdown и при выходе из пинча.
  function peStartPanFrom(id) {
    const pt = peState.pointers.get(id);
    if (!pt) return;
    peState.dragging = true;
    peState.dragId = id;
    peState.dragStartX = pt.x;
    peState.dragStartY = pt.y;
    peState.panStartX = peState.panX;
    peState.panStartY = peState.panY;
  }

  // Начать пинч: запомнить стартовую дистанцию между двумя пальцами и зум.
  function peStartPinch() {
    const ids = Array.from(peState.pointers.keys());
    const a = peState.pointers.get(ids[0]);
    const b = peState.pointers.get(ids[1]);
    peState.pinching = true;
    peState.dragging = false;        // pan на время пинча приостановлен
    peState.dragId = null;
    peState.pinchD0 = Math.max(1, pePointerDist(a, b));
    peState.pinchZ0 = peState.zoom;
  }

  frame.addEventListener("pointerdown", e => {
    // Регистрируем указатель и захватываем его на рамке.
    peState.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    try { frame.setPointerCapture(e.pointerId); } catch (_) {}
    frame.classList.add("pe-dragging");

    const n = peState.pointers.size;
    if (n === 1) {
      // Один палец/мышь — обычный pan.
      peStartPanFrom(e.pointerId);
    } else if (n === 2) {
      // Появился второй палец — переходим в режим пинча.
      peStartPinch();
    }
    // 3+ указателей игнорируем (продолжаем текущий жест).
    e.preventDefault();
  });

  frame.addEventListener("pointermove", e => {
    const pt = peState.pointers.get(e.pointerId);
    if (!pt) return;                 // не наш указатель
    pt.x = e.clientX;                // обновляем позицию в реестре
    pt.y = e.clientY;

    if (peState.pinching && peState.pointers.size >= 2) {
      // ── Пинч: новый зум = z0 * (текущая дистанция / стартовая) ──
      const ids = Array.from(peState.pointers.keys());
      const a = peState.pointers.get(ids[0]);
      const b = peState.pointers.get(ids[1]);
      const d = pePointerDist(a, b);
      peSetZoom(peState.pinchZ0 * (d / peState.pinchD0));
      e.preventDefault();
      return;
    }

    if (peState.dragging && e.pointerId === peState.dragId) {
      // ── Pan: сдвиг кадра на дельту указателя (px экрана) ──
      peState.panX = peState.panStartX + (e.clientX - peState.dragStartX);
      peState.panY = peState.panStartY + (e.clientY - peState.dragStartY);
      peUpdateTransformOnly();
      e.preventDefault();
    }
  });

  const peEndPointer = e => {
    if (!peState.pointers.has(e.pointerId)) return;
    peState.pointers.delete(e.pointerId);   // убрать из реестра (не «залипает»)
    try { frame.releasePointerCapture(e.pointerId); } catch (_) {}

    const n = peState.pointers.size;
    if (n >= 2) {
      // Всё ещё мультитач — перезапускаем пинч с оставшихся двух пальцев.
      peStartPinch();
    } else if (n === 1) {
      // Вышли из пинча в pan: продолжаем сдвиг с оставшегося пальца без рывка.
      peState.pinching = false;
      peStartPanFrom(Array.from(peState.pointers.keys())[0]);
    } else {
      // Указателей не осталось — полный сброс жеста.
      peState.pinching = false;
      peState.dragging = false;
      peState.dragId = null;
      frame.classList.remove("pe-dragging");
    }
  };
  frame.addEventListener("pointerup", peEndPointer);
  frame.addEventListener("pointercancel", peEndPointer);

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

/* ── Выезжающая шторка «Оформление сайта» ──
   Открытие/закрытие переключает класс .open у шторки и подложки. Закрытие —
   по крестику, клику мимо (по подложке) и клавише Escape. */
function openDrawer() {
  document.getElementById("appearance-drawer").classList.add("open");
  document.getElementById("drawer-overlay").classList.add("open");
  document.getElementById("appearance-drawer").setAttribute("aria-hidden", "false");
}
function closeDrawer() {
  document.getElementById("appearance-drawer").classList.remove("open");
  document.getElementById("drawer-overlay").classList.remove("open");
  document.getElementById("appearance-drawer").setAttribute("aria-hidden", "true");
}
document.addEventListener("keydown", e => {
  if (e.key === "Escape") closeDrawer();
});

/* ── Переиспользуемый движок перетаскивания списка (Работы 2 и 3) ──
   Перетаскивание среди соседей внутри одного контейнера, на указателях (pointer
   events) — работает и мышью, и пальцем на планшете. Без сторонних библиотек (D-03).

   enableDragReorder(container, opts):
     container      — DOM-элемент, чьи прямые дети itemSelector переставляются
     opts.itemSelector   — селектор перетаскиваемого элемента (прямой ребёнок container)
     opts.handleSelector — селектор «ручки» внутри элемента (за неё начинается перенос)
     opts.onDrop(orderedIds) — колбэк с новым порядком (значения data-id элементов)
   Каждый перетаскиваемый элемент должен иметь атрибут data-id. */
function enableDragReorder(container, opts) {
  const itemSel = opts.itemSelector, handleSel = opts.handleSelector;
  let dragEl = null, ghost = null, startY = 0, scrollTimer = null;

  container.addEventListener("pointerdown", e => {
    const handle = e.target.closest(handleSel);
    if (!handle || !container.contains(handle)) return;
    const item = handle.closest(itemSel);
    if (!item || item.parentNode !== container) return;
    e.preventDefault();
    dragEl = item;
    // «Призрак» — визуальная копия, следующая за пальцем
    const r = item.getBoundingClientRect();
    ghost = item.cloneNode(true);
    ghost.classList.add("drag-ghost");
    ghost.style.width = r.width + "px";
    ghost.style.left = (r.left + r.width / 2) + "px";
    ghost.style.top = e.clientY + "px";
    document.body.appendChild(ghost);
    item.classList.add("drag-source");
    startY = e.clientY;
    // Перехватываем указатель, чтобы получать move/up даже вне элемента
    try { handle.setPointerCapture(e.pointerId); } catch (_) {}
    handle.addEventListener("pointermove", onMove);
    handle.addEventListener("pointerup", onUp, { once: true });
    handle.addEventListener("pointercancel", onUp, { once: true });
  });

  function onMove(e) {
    if (!dragEl || !ghost) return;
    ghost.style.top = e.clientY + "px";
    // Автопрокрутка у краёв экрана
    autoScroll(e.clientY);
    // Найти соседа под указателем и переставить перед/после него
    const siblings = [...container.querySelectorAll(":scope > " + itemSel)]
      .filter(s => s !== dragEl);
    for (const s of siblings) {
      const rect = s.getBoundingClientRect();
      if (e.clientY >= rect.top && e.clientY <= rect.bottom) {
        const before = e.clientY < rect.top + rect.height / 2;
        container.insertBefore(dragEl, before ? s : s.nextSibling);
        break;
      }
    }
  }

  function autoScroll(y) {
    const scroller = container.closest(".oe-body, #products, .drawer-body") || document.scrollingElement;
    const M = 70; // зона у края
    let dy = 0;
    if (y < M) dy = -(M - y) / 4;
    else if (y > window.innerHeight - M) dy = (y - (window.innerHeight - M)) / 4;
    clearInterval(scrollTimer);
    if (dy !== 0) scrollTimer = setInterval(() => scroller.scrollBy(0, dy), 16);
  }

  function onUp() {
    clearInterval(scrollTimer);
    if (ghost) { ghost.remove(); ghost = null; }
    if (dragEl) dragEl.classList.remove("drag-source");
    dragEl = null;
    const ids = [...container.querySelectorAll(":scope > " + itemSel)].map(el => el.dataset.id);
    if (opts.onDrop) opts.onDrop(ids);
  }
}

/* ── Редактор порядка каталога (Работа 2) ──
   Модель — массив разделов, у каждого подгруппы, у каждой категории. Строим из
   STRUCTURE_FULL, применяя сохранённый порядок (catalog_order). Перестановка —
   стрелками ▲▼ и перетаскиванием; сохранение пишет JSON в «Настройки». */
let orderModel = null;        // [{name, open, subs:[{name, open, cats:[str]}]}]
let orderSaving = false;

// Порт _reorder_by из upload.py: names по desired, остальное — в конце в исходном порядке
function reorderBy(names, desired) {
  const dset = new Set(desired || []), nset = new Set(names);
  const ordered = (desired || []).filter(n => nset.has(n));
  const rest = names.filter(n => !dset.has(n));
  return ordered.concat(rest);
}

// Собрать модель из STRUCTURE_FULL, наложив сохранённый порядок (savedOrder может быть null)
function buildOrderModel(savedOrder) {
  const so = savedOrder || {};
  const secOrder = so.sections || [];
  const subOrder = so.subgroups || {};
  const catOrder = so.categories || {};
  const sections = reorderBy(Object.keys(STRUCTURE_FULL), secOrder);
  return sections.map(sec => {
    const subs = reorderBy(Object.keys(STRUCTURE_FULL[sec] || {}), subOrder[sec] || []);
    return {
      name: sec, open: false,
      subs: subs.map(sub => ({
        name: sub, open: false,
        cats: reorderBy((STRUCTURE_FULL[sec][sub] || []).slice(), catOrder[sub] || []),
      })),
    };
  });
}

// Сериализовать модель → {sections, subgroups, categories} для сохранения
function serializeOrder() {
  const out = { sections: [], subgroups: {}, categories: {} };
  orderModel.forEach(sec => {
    out.sections.push(sec.name);
    out.subgroups[sec.name] = sec.subs.map(s => s.name);
    sec.subs.forEach(sub => { out.categories[sub.name] = sub.cats.slice(); });
  });
  return out;
}

// Переместить элемент массива с i на i+dir (dir = -1 вверх / +1 вниз)
function moveInArray(arr, i, dir) {
  const j = i + dir;
  if (j < 0 || j >= arr.length) return;
  const [x] = arr.splice(i, 1);
  arr.splice(j, 0, x);
}

function renderOrderTree() {
  const tree = document.getElementById("ord-tree");
  tree.innerHTML = "";
  orderModel.forEach((sec, si) => {
    tree.appendChild(orderNode("section", sec.name, si, orderModel.length,
      sec.open, sec.subs.length + " подгр.", () => { sec.open = !sec.open; renderOrderTree(); }));
    if (sec.open) {
      const subBox = childBox("sec:" + si);
      sec.subs.forEach((sub, ui) => {
        subBox.appendChild(orderNode("subgroup", sub.name, ui, sec.subs.length,
          sub.open, sub.cats.length + " кат.", () => { sub.open = !sub.open; renderOrderTree(); }, "sub", si, ui));
        if (sub.open) {
          const catBox = childBox("sub:" + si + ":" + ui);
          sub.cats.forEach((cat, ci) => {
            catBox.appendChild(orderNode("category", cat, ci, sub.cats.length,
              null, "", null, "cat", si, ui, ci));
          });
          // Drag категорий внутри подгруппы
          enableDragReorder(catBox, {
            itemSelector: ".ord-node", handleSelector: ".ord-handle",
            onDrop: ids => { sub.cats = ids.slice(); renderOrderTree(); },
          });
          subBox.appendChild(catBox);
        }
      });
      // Drag подгрупп внутри раздела
      enableDragReorder(subBox, {
        itemSelector: ".ord-node.ord-subgroup", handleSelector: ".ord-handle",
        onDrop: ids => {
          const byName = {}; sec.subs.forEach(s => byName[s.name] = s);
          sec.subs = ids.map(n => byName[n]).filter(Boolean);
          renderOrderTree();
        },
      });
      tree.appendChild(subBox);
    }
  });
  // Drag разделов на верхнем уровне
  enableDragReorder(tree, {
    itemSelector: ".ord-node.ord-section", handleSelector: ".ord-handle",
    onDrop: ids => {
      const byName = {}; orderModel.forEach(s => byName[s.name] = s);
      orderModel = ids.map(n => byName[n]).filter(Boolean);
      renderOrderTree();
    },
  });
}

function childBox(key) {
  const box = document.createElement("div");
  box.className = "ord-children";
  box.dataset.box = key;
  return box;
}

// Собрать один узел дерева. level: section|subgroup|category. onToggle — раскрытие (или null).
function orderNode(level, name, idx, total, open, countText, onToggle, moveKind, si, ui, ci) {
  const node = document.createElement("div");
  node.className = "ord-node ord-" + level;
  node.dataset.id = name;

  const handle = document.createElement("span");
  handle.className = "ord-handle"; handle.textContent = "≡"; handle.title = "Перетащить";
  node.appendChild(handle);

  if (onToggle) {
    const tog = document.createElement("button");
    tog.type = "button"; tog.className = "ord-toggle";
    tog.textContent = open ? "▾" : "▸";
    tog.onclick = onToggle;
    node.appendChild(tog);
  }

  const nm = document.createElement("span");
  nm.className = "ord-name"; nm.textContent = name;
  node.appendChild(nm);

  if (countText) {
    const cnt = document.createElement("span");
    cnt.className = "ord-count"; cnt.textContent = countText;
    node.appendChild(cnt);
  }

  const arrows = document.createElement("div");
  arrows.className = "ord-arrows";
  const up = document.createElement("button");
  up.type = "button"; up.className = "ord-arrow"; up.textContent = "▲";
  up.disabled = idx === 0;
  up.onclick = () => doMove(moveKind || level, si, ui, ci, idx, -1);
  const down = document.createElement("button");
  down.type = "button"; down.className = "ord-arrow"; down.textContent = "▼";
  down.disabled = idx === total - 1;
  down.onclick = () => doMove(moveKind || level, si, ui, ci, idx, +1);
  arrows.appendChild(up); arrows.appendChild(down);
  node.appendChild(arrows);
  return node;
}

// Перемещение стрелкой: определяем массив по уровню и двигаем
function doMove(kind, si, ui, ci, idx, dir) {
  if (kind === "section") moveInArray(orderModel, idx, dir);
  else if (kind === "sub" || kind === "subgroup") moveInArray(orderModel[si].subs, idx, dir);
  else if (kind === "cat" || kind === "category") moveInArray(orderModel[si].subs[ui].cats, idx, dir);
  renderOrderTree();
}

async function openOrderEditor() {
  closeDrawer();
  // Тянем текущий сохранённый порядок, чтобы редактор открылся в актуальном виде
  let saved = null;
  try {
    const r = await fetch("/" + TOKEN + "/settings");
    const s = await r.json();
    if (s && typeof s.catalog_order === "string" && s.catalog_order) {
      saved = JSON.parse(s.catalog_order);
    }
  } catch (e) { /* нет порядка / офлайн — открываем из structure_map */ }
  orderModel = buildOrderModel(saved);
  renderOrderTree();
  document.getElementById("order-editor").classList.add("open");
  document.getElementById("order-editor").setAttribute("aria-hidden", "false");
}

function closeOrderEditor() {
  document.getElementById("order-editor").classList.remove("open");
  document.getElementById("order-editor").setAttribute("aria-hidden", "true");
}

async function saveOrder() {
  if (orderSaving) return;
  orderSaving = true;
  const btn = document.getElementById("oe-save-btn");
  btn.disabled = true;
  const payload = serializeOrder();
  const res = await apiCall("/" + TOKEN + "/catalog-order", {
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  orderSaving = false; btn.disabled = false;
  if (res && res.ok) {
    toast("ok", res.message || "Порядок сохранён.");
    closeOrderEditor();
  } else {
    toast("err", (res && res.message) || "Не удалось сохранить порядок.");
  }
}

/* ── Оформление: выбор цвета цены на карточках сайта ──
   Палитра синхронизирована с lib/priceColors.ts на фронте. Текущее значение
   тянем с сервера (вкладка «Настройки», ключ price_color), по клику сохраняем. */
const PRICE_COLORS = [
  { key: "violet", label: "Фиолетовый", hex: "#7c3aed" },
  { key: "green",  label: "Зелёный",    hex: "#16a34a" },
  { key: "blue",   label: "Синий",      hex: "#2563eb" },
  { key: "red",    label: "Красный",    hex: "#dc2626" },
  { key: "black",  label: "Чёрный",     hex: "#111827" },
];
let activePriceColor = "violet";  // дефолт совпадает с фронтом (DEFAULT_PRICE_COLOR)

function renderPriceColors() {
  const box = document.getElementById("price-colors");
  box.innerHTML = "";
  PRICE_COLORS.forEach(c => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pcolor" + (c.key === activePriceColor ? " active" : "");
    btn.innerHTML = '<span class="dot" style="background:' + c.hex + '"></span>' + esc(c.label);
    btn.onclick = () => savePriceColor(c.key);
    box.appendChild(btn);
  });
}

async function savePriceColor(color) {
  const prev = activePriceColor;
  activePriceColor = color;           // оптимистично подсвечиваем
  renderPriceColors();
  const res = await apiCall("/" + TOKEN + "/setting", {
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key: "price_color", value: color }),
  });
  if (res && res.ok) {
    toast("ok", res.message || "Цвет цены сохранён.");
  } else {
    activePriceColor = prev;          // откат при ошибке
    renderPriceColors();
    toast("err", (res && res.message) || "Не удалось сохранить цвет.");
  }
}

async function loadPriceColor() {
  try {
    const r = await fetch("/" + TOKEN + "/settings");
    const s = await r.json();
    if (s && typeof s.price_color === "string" && s.price_color) {
      activePriceColor = s.price_color;
    }
  } catch (e) { /* офлайн/ошибка — остаёмся на дефолте */ }
  renderPriceColors();
}

/* ── Инициализация ── */
updateViewButtons();
updateDensityUI();
initPhotoEditor();   // привязать контролы редактора фото один раз
renderPriceColors(); // мгновенно показать палитру (дефолт), затем уточнить с сервера
loadPriceColor();
loadProducts();
</script>
</body>
</html>"""
