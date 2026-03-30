r"""
upload.py — Скрипт-конвертер Excel → Google Sheet
Этап 0, Задачи 0.2 + 0.3: парсинг Excel и запись в Google Sheet

Использование:
    python upload.py                            # парсинг + запись в Google Sheet
    python upload.py --path /путь/к/папке       # указать папку с файлами
    python upload.py --dry-run                  # только парсинг, без записи

Настройка (.env в корне проекта):
    EXCEL_DIR=C:\price                          # папка с Excel-файлами (необязательно)
    GOOGLE_SHEETS_ID=ваш_id_таблицы             # ID Google Sheet
    GOOGLE_CREDENTIALS_PATH=credentials.json    # путь к ключу Service Account
"""

import os
import sys
import json
import glob
import logging
import argparse
from pathlib import Path

import openpyxl

# --- Настройка логирования ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# --- Путь к папке скрипта (для category_map.json, .env) ---
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# --- Путь к Excel-файлам по умолчанию ---
DEFAULT_EXCEL_DIR = r"C:\price"


def load_badges() -> dict:
    """Загрузить метки из badges.json. При отсутствии файла возвращает пустую структуру."""
    badges_path = SCRIPT_DIR / "badges.json"
    if not badges_path.exists():
        log.warning("Файл badges.json не найден: %s — метки не будут проставлены", badges_path)
        return {"исключения": [], "новинка": [], "хит": [], "акция": []}
    with open(badges_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_badge(name: str, badges: dict) -> str:
    """Определить метку для товара по его названию.

    Приоритет: исключения → новинка → хит → акция.
    Поиск по частичному совпадению, регистронезависимый.
    """
    name_lower = name.lower()

    for exclusion in badges.get("исключения", []):
        if exclusion.lower() in name_lower:
            return ""

    for badge_key in ("новинка", "хит", "акция"):
        for substring in badges.get(badge_key, []):
            if substring.lower() in name_lower:
                return badge_key

    return ""


def load_category_map() -> dict:
    """Загрузить маппинг категорий из category_map.json."""
    map_path = SCRIPT_DIR / "category_map.json"
    if not map_path.exists():
        log.warning("Файл category_map.json не найден: %s", map_path)
        return {}
    with open(map_path, "r", encoding="utf-8") as f:
        return json.load(f)


def strip_category_prefix(name: str) -> str:
    """Убрать префикс 'а' у категорий вида 'аКока-Кола' → 'Кока-Кола'.

    Префикс удаляется только если:
    - строка начинается с 'а' (маленькая)
    - следующий символ — заглавная буква
    """
    if len(name) >= 2 and name[0] == "а" and name[1].isupper():
        return name[1:]
    return name


def is_header_row(a, b, c) -> bool:
    """Проверить, является ли строка заголовком (Цена/Остаток)."""
    b_str = str(b).strip().lower() if b else ""
    c_str = str(c).strip().lower() if c else ""
    return b_str in ("цена",) or c_str in ("остаток",)


def is_category_row(a, b, c) -> bool:
    """Категория = колонка A заполнена, B и C пустые."""
    return a is not None and str(a).strip() != "" and b is None and c is None


def parse_excel_file(filepath: str) -> list[dict]:
    """Распарсить один Excel-файл поставщика.

    Возвращает список словарей:
    [{name, price, stock, source_category, supplier_file}]
    """
    filename = Path(filepath).name
    log.info("Парсинг файла: %s", filename)

    wb = openpyxl.load_workbook(filepath, data_only=True, read_only=True)
    ws = wb.active
    products = []
    current_category = "Без категории"

    for row in ws.iter_rows(min_row=1, values_only=True):
        # Извлекаем первые 3 колонки
        a = row[0] if len(row) > 0 else None
        b = row[1] if len(row) > 1 else None
        c = row[2] if len(row) > 2 else None

        # Пропускаем пустые строки
        if a is None and b is None and c is None:
            continue

        # Пропускаем строку-заголовок
        if is_header_row(a, b, c):
            continue

        # Строка-категория
        if is_category_row(a, b, c):
            raw_name = str(a).strip()
            current_category = strip_category_prefix(raw_name)
            continue

        # Строка-товар: A заполнена и B (цена) заполнена
        if a is not None and b is not None:
            name = str(a).strip()
            if not name:
                continue
            try:
                price = float(b)
            except (ValueError, TypeError):
                log.warning("  Не удалось прочитать цену: '%s' (строка: %s)", b, name)
                continue

            try:
                stock = int(float(c)) if c is not None else 0
            except (ValueError, TypeError):
                stock = 0

            products.append({
                "name": name,
                "price": round(price, 2),
                "stock": stock,
                "source_category": current_category,
                "supplier_file": filename,
            })

    wb.close()
    log.info("  Найдено товаров: %d", len(products))
    return products


# Переопределение категории по началу названия товара (регистронезависимо).
# Порядок важен: более длинные/специфичные префиксы должны идти первыми.
PRODUCT_OVERRIDES = {
    "Набор конфет ЛЮСИ": "Коробочные конфеты",
    "Набор конфет МВН": "Коробочные конфеты",
    "Набор конфет Сонуар": "Коробочные конфеты",
    "Фас. кор. конфеты": "Коробочные конфеты",
    "Вес. драже Арахис": "Детское",
    "Драже Скитлс": "Батончики и шоколад",
    "Драже М&М": "Батончики и шоколад",
    "Соус POMATO": "Соусы и специи",
    "POMATO": "Соусы и специи",
    "Соус": "Соусы и специи",
    "Ж/р Ментос": "Прикассовое",
    "Аджика АМЦА": "Соусы и специи",
    "Нап.кофейный": "Напитки",
    "Let's Be": "Напитки",
    "Киндер": "Батончики и шоколад",
    "Цикорий": "Прикассовое",
    "Холс": "Прикассовое",
}

# Переопределение по подстроке в названии (регистронезависимо).
PRODUCT_CONTAINS_OVERRIDES = [
    ("паста шок", "Батончики и шоколад"),
    ("шок. паста", "Батончики и шоколад"),
]


def apply_product_override(name: str) -> str | None:
    """Вернуть переопределённую группу по регистронезависимому совпадению в названии товара.

    Сначала проверяется начало строки (PRODUCT_OVERRIDES),
    затем вхождение подстроки (PRODUCT_CONTAINS_OVERRIDES).
    """
    name_lower = name.lower()
    for prefix, group in PRODUCT_OVERRIDES.items():
        if name_lower.startswith(prefix.lower()):
            return group
    for substring, group in PRODUCT_CONTAINS_OVERRIDES:
        if substring.lower() in name_lower:
            return group
    return None


def apply_group_mapping(products: list[dict], category_map: dict) -> list[dict]:
    """Добавить поле display_group на основе маппинга категорий и переопределений по товару."""
    unmapped = set()
    overridden = 0
    for product in products:
        cat = product["source_category"]
        group = category_map.get(cat)
        if group is None:
            unmapped.add(cat)
            group = "Другое"

        override = apply_product_override(product["name"])
        if override is not None and override != group:
            group = override
            overridden += 1

        product["display_group"] = group

    if unmapped:
        log.warning("Категории без маппинга (попадут в 'Другое'):")
        for cat in sorted(unmapped):
            log.warning("  - %s", cat)

    if overridden:
        log.info("Переопределено категорий по названию товара: %d", overridden)

    return products


def products_to_rows(products: list[dict], badges: dict | None = None) -> list[list]:
    """Преобразовать список товаров в строки для Google Sheet.

    Формат: [Наименование, Цена, Остаток, Категория, Группа, Поставщик, Badge]
    """
    if badges is None:
        badges = {"исключения": [], "новинка": [], "хит": [], "акция": []}
    header = ["Наименование", "Цена", "Остаток", "Категория", "Группа", "Поставщик", "Badge"]
    rows = [header]
    for p in products:
        rows.append([
            p["name"],
            p["price"],
            p["stock"],
            p["source_category"],
            p["display_group"],
            p["supplier_file"],
            get_badge(p["name"], badges),
        ])
    return rows


def load_env() -> dict:
    """Загрузить переменные из .env файла (без python-dotenv).

    Ищет .env сначала в корне проекта, потом в папке скрипта.
    """
    env_vars = {}
    for search_dir in [PROJECT_ROOT, SCRIPT_DIR]:
        env_path = search_dir / ".env"
        if env_path.exists():
            log.info("Загружаю .env из: %s", env_path)
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    env_vars[key] = value
                    os.environ.setdefault(key, value)
            break
    return env_vars


def upload_to_google_sheet(rows: list[list], num_files: int) -> None:
    """Записать данные в Google Sheet через gspread.

    1. Авторизация через Service Account
    2. Открыть таблицу по GOOGLE_SHEETS_ID
    3. Очистить лист "Товары" (или создать)
    4. Записать заголовки + товары
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        log.error(
            "Не установлены пакеты gspread / google-auth.\n"
            "Установите: pip install gspread google-auth"
        )
        sys.exit(1)

    # --- Путь к credentials ---
    creds_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "")
    if not creds_path:
        for search_dir in [SCRIPT_DIR, PROJECT_ROOT]:
            candidate = search_dir / "credentials.json"
            if candidate.exists():
                creds_path = str(candidate)
                break

    if not creds_path or not Path(creds_path).exists():
        log.error(
            "Файл credentials.json не найден.\n"
            "Укажите путь в .env: GOOGLE_CREDENTIALS_PATH=путь/к/credentials.json\n"
            "Или положите credentials.json в папку scripts/"
        )
        sys.exit(1)

    # --- ID таблицы ---
    sheets_id = os.environ.get("GOOGLE_SHEETS_ID", "")
    if not sheets_id:
        log.error(
            "Не указан GOOGLE_SHEETS_ID.\n"
            "Добавьте в .env: GOOGLE_SHEETS_ID=ваш_id_таблицы"
        )
        sys.exit(1)

    # --- Авторизация ---
    log.info("Авторизация в Google Sheets...")
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(credentials)

    # --- Открыть таблицу ---
    log.info("Открываю таблицу: %s", sheets_id)
    spreadsheet = gc.open_by_key(sheets_id)

    # --- Найти или создать лист "Товары" ---
    sheet_name = "Товары"
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        log.info("Лист '%s' найден — очищаю...", sheet_name)
        worksheet.clear()
    except gspread.exceptions.WorksheetNotFound:
        log.info("Лист '%s' не найден — создаю...", sheet_name)
        worksheet = spreadsheet.add_worksheet(
            title=sheet_name, rows=len(rows) + 10, cols=7
        )

    # --- Записать данные пакетно ---
    log.info("Записываю %d строк (заголовок + %d товаров)...", len(rows), len(rows) - 1)

    if worksheet.row_count < len(rows):
        worksheet.resize(rows=len(rows) + 10)

    worksheet.update(rows, value_input_option="USER_ENTERED")

    num_products = len(rows) - 1
    log.info(
        "Загружено %d товаров из %d файлов в Google Sheet",
        num_products,
        num_files,
    )


def main():
    # Загрузить переменные окружения из .env
    load_env()

    parser = argparse.ArgumentParser(description="Конвертер Excel → Google Sheet")
    parser.add_argument(
        "--path",
        default=os.environ.get("EXCEL_DIR", DEFAULT_EXCEL_DIR),
        help="Папка с .xlsx файлами (по умолчанию: C:\\price\\)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только парсинг, без записи в Google Sheet",
    )
    args = parser.parse_args()

    excel_dir = Path(args.path)
    if not excel_dir.exists():
        log.error("Папка не найдена: %s", excel_dir)
        sys.exit(1)

    # Найти все .xlsx файлы
    xlsx_files = sorted(glob.glob(str(excel_dir / "*.xlsx")))
    if not xlsx_files:
        log.error("В папке %s нет .xlsx файлов", excel_dir)
        sys.exit(1)

    log.info("Найдено файлов: %d", len(xlsx_files))

    # Загрузить маппинг категорий
    category_map = load_category_map()
    log.info("Загружено категорий в маппинге: %d", len(category_map))

    # Загрузить метки
    badges = load_badges()
    badge_count = sum(len(v) for k, v in badges.items() if k != "исключения")
    log.info("Загружено меток: %d", badge_count)

    # Парсить все файлы
    all_products = []
    for filepath in xlsx_files:
        products = parse_excel_file(filepath)
        all_products.extend(products)

    log.info("Всего товаров из %d файлов: %d", len(xlsx_files), len(all_products))

    # Применить маппинг групп
    all_products = apply_group_mapping(all_products, category_map)

    # Подготовить строки для Google Sheet
    rows = products_to_rows(all_products, badges)

    # Статистика по группам
    groups = {}
    for p in all_products:
        g = p["display_group"]
        groups[g] = groups.get(g, 0) + 1
    log.info("Распределение по группам:")
    for g in sorted(groups, key=groups.get, reverse=True):
        log.info("  %s: %d товаров", g, groups[g])

    if args.dry_run:
        log.info("--dry-run: запись в Google Sheet пропущена")
        # Вывести первые 5 строк как пример
        print("\nПример данных (первые 5 товаров):")
        print("-" * 100)
        for row in rows[:6]:  # заголовок + 5 товаров
            print(" | ".join(str(x) for x in row))
        print("-" * 100)
        print(f"Всего строк (без заголовка): {len(rows) - 1}")
    else:
        upload_to_google_sheet(rows, num_files=len(xlsx_files))

    return rows


if __name__ == "__main__":
    main()
