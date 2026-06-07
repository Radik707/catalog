"""
sheet_helper.py — Утилита чтения/записи данных каталога из Google Sheets.

Назначение: data-слой для Flask-панели администратора (uploader/admin.py).
Читает лист «Товары», вкладку «Правки»; добавляет строки правок.

Вызывается через shell-out из admin.py:
    python sheet_helper.py list
    python sheet_helper.py append_edit --key <норм_имя> --type group --value <значение>
    python sheet_helper.py normalize --name <исходное_имя>

Авторизация gspread: GOOGLE_CREDENTIALS_PATH или поиск credentials.json
в SCRIPT_DIR и PROJECT_ROOT. GOOGLE_SHEETS_ID — обязательный параметр.

Graceful-fallback: при отсутствии credentials/gspread/ошибке сети →
list печатает "[]" и завершается с кодом 0.
"""

import os
import re
import sys
import json
import logging
import argparse
from pathlib import Path

# --- Настройка логирования ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("sheet_helper")

# --- Пути (для поиска credentials.json и .env) ---
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# --- Допустимые типы правок (белый список — защита памяти правок от мусора) ---
ALLOWED_TYPES = {"group", "photo", "description", "name"}


def load_env() -> None:
    """Загрузить переменные из .env (как в upload.py и upload_photos.py)."""
    for search_dir in [PROJECT_ROOT, SCRIPT_DIR]:
        env_path = search_dir / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip().strip("'\""))
            return


def normalize_name(name: str) -> str:
    """Нормализовать название для сопоставления: убрать хвостовую единицу, нижний регистр.

    Скопировано из upload.py (строки 213–215) — без зависимостей, 2 строки логики.
    Используется как ключ сопоставления при записи/чтении правок.
    """
    return re.sub(r"\s+", " ", re.sub(r",\s*[А-Яа-яA-Za-z.]+\s*$", "", name)).strip().lower()


def _get_spreadsheet():
    """Авторизоваться в Google Sheets и вернуть объект Spreadsheet.

    Порядок поиска credentials:
    1. Переменная окружения GOOGLE_CREDENTIALS_PATH
    2. SCRIPT_DIR/credentials.json
    3. PROJECT_ROOT/credentials.json

    Исключение пробрасывается вверх — вызывающий сам решает как обработать.
    """
    import gspread
    from google.oauth2.service_account import Credentials

    # --- Путь к credentials ---
    creds_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "")
    if not creds_path:
        for d in (SCRIPT_DIR, PROJECT_ROOT):
            c = d / "credentials.json"
            if c.exists():
                creds_path = str(c)
                break

    sheets_id = os.environ.get("GOOGLE_SHEETS_ID", "")

    if not creds_path:
        raise FileNotFoundError("credentials.json не найден и GOOGLE_CREDENTIALS_PATH не задан")
    if not sheets_id:
        raise ValueError("GOOGLE_SHEETS_ID не задан")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    return gspread.authorize(creds).open_by_key(sheets_id)


def load_edit_keys() -> set:
    """Загрузить множество нормализованных ключей из вкладки «Правки».

    Используется для определения is_new: товар отсутствует в памяти правок
    (т.е. владелец ещё не касался этого товара через панель) — MEM-03.
    Graceful-fallback: при любой ошибке → пустое множество.
    """
    try:
        ss = _get_spreadsheet()
        try:
            values = ss.worksheet("Правки").get_all_values()
        except Exception:
            # Вкладка «Правки» не найдена — память правок пуста, это нормально
            log.info("Вкладка «Правки» не найдена — память правок пуста")
            return set()
    except Exception as e:
        log.warning("Не удалось прочитать вкладку «Правки»: %s", e)
        return set()

    if not values:
        return set()

    # --- Найти индекс колонки «Товар» ---
    header = values[0]
    try:
        товар_i = header.index("Товар")
    except ValueError:
        log.warning("Вкладка «Правки»: нет колонки «Товар» — пропускаем")
        return set()

    # Собираем множество нормализованных ключей
    keys = set()
    for row in values[1:]:
        if len(row) > товар_i and row[товар_i]:
            keys.add(normalize_name(str(row[товар_i]).strip()))
    return keys


def load_products() -> list:
    """Прочитать лист «Товары» → список товаров с полями {name, group, image_url, is_new}.

    is_new=True если нормализованное имя товара ОТСУТСТВУЕТ в памяти «Правки» (MEM-03):
    владелец ещё не «касался» этого товара через панель.
    Graceful-fallback: при любой ошибке → пустой список [].
    """
    try:
        ss = _get_spreadsheet()
        values = ss.worksheet("Товары").get_all_values()
    except Exception as e:
        log.warning("Не удалось прочитать лист «Товары»: %s", e)
        return []

    if not values:
        return []

    # --- Найти индексы колонок по заголовкам ---
    header = values[0]
    try:
        name_i = header.index("Наименование")
    except ValueError:
        log.warning("Лист «Товары»: нет колонки «Наименование»")
        return []

    # Группа и ImageUrl опциональны — берём по индексу или None
    grp_i = header.index("Группа") if "Группа" in header else None
    img_i = header.index("ImageUrl") if "ImageUrl" in header else None

    # --- Загрузить ключи «Правки» для определения is_new ---
    edit_keys = load_edit_keys()

    products = []
    for row in values[1:]:
        if not row or len(row) <= name_i:
            continue
        raw_name = str(row[name_i]).strip()
        if not raw_name:
            continue

        # Значение группы (пустая строка если нет)
        group = str(row[grp_i]).strip() if grp_i is not None and len(row) > grp_i else ""

        # URL фото (пустая строка если нет)
        image_url = str(row[img_i]).strip() if img_i is not None and len(row) > img_i else ""

        # Товар «новинка для панели» — если его нет в памяти «Правки»
        is_new = normalize_name(raw_name) not in edit_keys

        products.append({
            "name": raw_name,
            "group": group,
            "image_url": image_url,
            "is_new": is_new,
        })

    log.info("Загружено товаров: %d", len(products))
    return products


def append_edit(product_key: str, edit_type: str, value: str) -> None:
    """Добавить строку в вкладку «Правки» (Товар | Тип | Значение).

    Создаёт вкладку с заголовком при WorksheetNotFound.
    При ошибке записи пробрасывает исключение — вызывающий (admin.py) вернёт HTTP 500.

    :param product_key: нормализованное имя товара (ключ сопоставления)
    :param edit_type: тип правки, одно из ALLOWED_TYPES
    :param value: новое значение поля
    """
    # --- Защита белого списка (T-04-02) ---
    if edit_type not in ALLOWED_TYPES:
        raise ValueError(f"Недопустимый тип правки: {edit_type!r}. Допустимые: {ALLOWED_TYPES}")

    import gspread

    ss = _get_spreadsheet()
    try:
        ws = ss.worksheet("Правки")
    except gspread.exceptions.WorksheetNotFound:
        # Вкладка ещё не существует — создаём с заголовком
        log.info("Вкладка «Правки» не найдена — создаём с заголовком")
        ws = ss.add_worksheet(title="Правки", rows=1000, cols=3)
        ws.append_row(["Товар", "Тип", "Значение"])

    # Значения трактуются как строки-данные (USER_ENTERED не используется — T-04-02)
    ws.append_row([product_key, edit_type, value])
    log.info("Правка записана: %s | %s | %s", product_key, edit_type, value[:40])


# ── Интерфейс командной строки (CLI) ──

def main() -> None:
    """Точка входа CLI: list / append_edit / normalize."""
    # Загрузить переменные окружения из .env
    load_env()

    parser = argparse.ArgumentParser(
        description="Утилита управления данными каталога в Google Sheets",
    )
    parser.add_argument(
        "action",
        choices=["list", "append_edit", "normalize"],
        help="Действие: list — список товаров, append_edit — записать правку, normalize — нормализовать имя",
    )
    # Аргументы для append_edit
    parser.add_argument("--key", help="Нормализованный ключ товара (для append_edit)")
    parser.add_argument(
        "--type",
        dest="edit_type",
        choices=list(ALLOWED_TYPES),
        help="Тип правки: group | photo | description | name",
    )
    parser.add_argument("--value", help="Новое значение правки")
    # Аргумент для normalize
    parser.add_argument("--name", help="Исходное имя товара (для normalize)")

    args = parser.parse_args()

    if args.action == "list":
        # Список товаров → JSON в stdout; graceful: пустой [] при любой ошибке
        # ensure_ascii=True — безопасно для cp1252/UTF-8 Windows-консоли
        products = load_products()
        sys.stdout.buffer.write(json.dumps(products, ensure_ascii=False).encode("utf-8") + b"\n")

    elif args.action == "append_edit":
        # Записать правку во вкладку «Правки»
        if not args.key:
            print("Ошибка: --key обязателен для append_edit", file=sys.stderr)
            sys.exit(1)
        if not args.edit_type:
            print("Ошибка: --type обязателен для append_edit", file=sys.stderr)
            sys.exit(1)
        if args.value is None:
            print("Ошибка: --value обязателен для append_edit", file=sys.stderr)
            sys.exit(1)
        try:
            append_edit(args.key, args.edit_type, args.value)
        except Exception as e:
            print(f"Ошибка записи правки: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.action == "normalize":
        # Нормализовать имя и вывести в stdout
        if not args.name:
            print("Ошибка: --name обязателен для normalize", file=sys.stderr)
            sys.exit(1)
        print(normalize_name(args.name))


if __name__ == "__main__":
    main()
