r"""
upload.py — Скрипт-конвертер Excel → Google Sheet
Поддерживает два формата прайс-листов: старый (A=категория/название, B=цена, C=остаток)
и новый формат 1С (название в колонке D, «Цена»/«Остаток» в дальних колонках ≥ N).
Формат определяется автоматически по индексу колонки «Цена».

Новые товары (из нового формата, отсутствующие в текущем каталоге) получают
группу «Новинки» и бейдж «новинка». При недоступности текущих групп каталога
скрипт прерывается с кодом 1 (sys.exit), не допуская попадания всех товаров в «Новинки».

Режим --dry-run: парсинг без записи в Google Sheet. Используется для проверки
перед боевым прогоном (на сервере запускается через uploader/app.py с бэкапом через sheet_tool.py).

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
import re
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


# ── Поддержка НОВОГО формата выгрузки 1С ──
# В новом формате: название в колонке D (индекс 3), а «Цена»/«Остаток» — в дальних
# колонках (например N/O). Категорий-разделителей нет. Каждый товар продублирован
# строкой с названием в колонке A (двойная запятая) — её пропускаем.
NEW_FORMAT_NAME_COL = 3  # колонка D


def find_header_cols(ws) -> tuple[int | None, int | None]:
    """Найти индексы колонок «Цена» и «Остаток» в первых строках листа."""
    for row in ws.iter_rows(min_row=1, max_row=10, values_only=True):
        price_col = stock_col = None
        for j, v in enumerate(row):
            if v is None:
                continue
            s = str(v).strip().lower()
            if s == "цена":
                price_col = j
            elif s == "остаток":
                stock_col = j
        if price_col is not None and stock_col is not None:
            return price_col, stock_col
    return None, None


def is_new_format(price_col: int | None) -> bool:
    """Новый формат — если «Цена» найдена в дальней колонке (D и правее), а не в B/C."""
    return price_col is not None and price_col >= 5


def clean_new_name(name: str) -> str:
    """Убрать хвостовую ', <ед.>' (', шт' / ', кг' / ', упак' и т.п.) из названия."""
    return re.sub(r",\s*[А-Яа-яA-Za-z.]+\s*$", "", name).strip()


def normalize_name(name: str) -> str:
    """Нормализовать название для сопоставления (без хвостовой единицы, нижний регистр)."""
    return re.sub(r"\s+", " ", clean_new_name(name)).strip().lower()


def parse_new_format(filepath: str, price_col: int, stock_col: int) -> list[dict]:
    """Распарсить файл нового формата. Категорий нет (source_category пустой)."""
    filename = Path(filepath).name
    log.info("Парсинг (новый формат): %s", filename)
    wb = openpyxl.load_workbook(filepath, data_only=True, read_only=True)
    ws = wb.active
    products = []
    for row in ws.iter_rows(min_row=1, values_only=True):
        name = row[NEW_FORMAT_NAME_COL] if len(row) > NEW_FORMAT_NAME_COL else None
        price = row[price_col] if len(row) > price_col else None
        stock = row[stock_col] if len(row) > stock_col else None
        if not name or price is None:
            continue
        name = str(name).strip()
        if name.lower() == "наименование":
            continue
        try:
            price = round(float(price), 2)
        except (ValueError, TypeError):
            continue
        try:
            stock = int(float(stock)) if stock is not None else 0
        except (ValueError, TypeError):
            stock = 0
        products.append({
            "name": clean_new_name(name),
            "price": price,
            "stock": stock,
            "source_category": "",   # категории нет — группа определяется по текущему каталогу
            "supplier_file": filename,
        })
    wb.close()
    log.info("  Найдено товаров: %d", len(products))
    return products


def load_current_groups() -> dict:
    """Прочитать текущий каталог (лист «Товары») → {норм_название: группа}.

    Нужно для нового формата: сохранить группировку существующих товаров и
    определить действительно новые (которых не было).
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        return {}
    creds_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "")
    if not creds_path:
        for d in (SCRIPT_DIR, PROJECT_ROOT):
            c = d / "credentials.json"
            if c.exists():
                creds_path = str(c)
                break
    sheets_id = os.environ.get("GOOGLE_SHEETS_ID", "")
    if not creds_path or not sheets_id:
        return {}
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    try:
        creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        ss = gspread.authorize(creds).open_by_key(sheets_id)
        values = ss.worksheet("Товары").get_all_values()
    except Exception as e:  # noqa: BLE001
        log.warning("Не удалось прочитать текущие группы: %s", e)
        return {}
    if not values:
        return {}
    header = values[0]
    try:
        name_i = header.index("Наименование")
        grp_i = header.index("Группа")
    except ValueError:
        return {}
    mapping = {}
    for r in values[1:]:
        if len(r) > max(name_i, grp_i) and r[name_i] and r[grp_i]:
            mapping[normalize_name(r[name_i])] = r[grp_i]
    log.info("Загружено групп из текущего каталога: %d", len(mapping))
    return mapping


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


# Маппинг папок Cloudinary → логические имена в photo_overrides.json
CLOUDINARY_FOLDER_ALIAS: dict[str, str] = {"catalog": "akkond"}


def _build_url_index(photo_urls: dict[str, str]) -> dict[str, str]:
    """Строит индекс {logical_folder/filename → url} из photo_urls.json.

    Для каждого файла определяет папку Cloudinary по URL и применяет CLOUDINARY_FOLDER_ALIAS.
    Также добавляет записи без папки для обратной совместимости.
    """
    import re as _re
    index: dict[str, str] = {}
    for filename, url in photo_urls.items():
        m = _re.search(r"/upload/v\d+/([^/]+)/", url)
        cloudinary_folder = m.group(1) if m else None
        logical_folder = CLOUDINARY_FOLDER_ALIAS.get(cloudinary_folder, cloudinary_folder)
        if logical_folder:
            index[f"{logical_folder}/{filename}"] = url
        index[filename] = url  # обратная совместимость: ключ без папки
    return index


def load_photo_data() -> dict[str, dict[str, str]]:
    """Загрузить маппинг название_товара → {url, description} из photo_map.json + photo_urls.json.

    Приоритет: photo_overrides.json (ручные привязки) → автоматический маппинг.
    photo_overrides.json поддерживает формат "folder/filename" и просто "filename".
    При отсутствии файлов возвращает пустой словарь — скрипт работает без ошибок.
    """
    photo_map_path = SCRIPT_DIR / "photo_map.json"
    photo_urls_path = SCRIPT_DIR / "photo_urls.json"
    overrides_path = SCRIPT_DIR / "photo_overrides.json"

    if not photo_map_path.exists() or not photo_urls_path.exists():
        if not photo_map_path.exists():
            log.warning("photo_map.json не найден — фото не будут добавлены")
        if not photo_urls_path.exists():
            log.warning("photo_urls.json не найден — фото не будут добавлены")
        return {}

    with open(photo_map_path, "r", encoding="utf-8") as f:
        photo_map = json.load(f)
    with open(photo_urls_path, "r", encoding="utf-8") as f:
        photo_urls: dict[str, str] = json.load(f)

    # Индекс: "folder/filename" и "filename" → url
    url_index = _build_url_index(photo_urls)

    # Автоматический маппинг: original_name (lower) → {url, description}
    name_to_data: dict[str, dict[str, str]] = {}
    for entry in photo_map:
        original_name = (entry.get("original_name") or "").strip()
        file_name = entry.get("file_name")
        description = (entry.get("description") or "").strip()
        if original_name and file_name and file_name in url_index:
            name_to_data[original_name.lower()] = {
                "url": url_index[file_name],
                "description": description,
            }

    # Ручные привязки перезаписывают авто-маппинг (description не перезаписывается)
    if overrides_path.exists():
        with open(overrides_path, "r", encoding="utf-8") as f:
            overrides: dict[str, str] = json.load(f)
        for product_name, file_key in overrides.items():
            if file_key in url_index:
                existing = name_to_data.get(product_name.lower(), {})
                name_to_data[product_name.lower()] = {
                    "url": url_index[file_key],
                    "description": existing.get("description", ""),
                }
        log.info("Загружено ручных привязок фото: %d", len(overrides))

    log.info("Загружено фото в маппинге: %d", len(name_to_data))
    return name_to_data


def _find_photo_entry(name: str, photo_data: dict[str, dict[str, str]]) -> dict[str, str] | None:
    """Найти запись о фото по частичному совпадению названия (регистронезависимо)."""
    if not photo_data:
        return None
    name_lower = name.lower()
    for photo_name, data in photo_data.items():
        if photo_name in name_lower or name_lower in photo_name:
            return data
    return None


def get_photo_url(name: str, photo_data: dict[str, dict[str, str]]) -> str:
    """Найти URL фото для товара по частичному совпадению (регистронезависимо)."""
    entry = _find_photo_entry(name, photo_data)
    return entry.get("url", "") if entry else ""


def get_photo_description(name: str, photo_data: dict[str, dict[str, str]]) -> str:
    """Найти описание товара по частичному совпадению (регистронезависимо)."""
    entry = _find_photo_entry(name, photo_data)
    return entry.get("description", "") if entry else ""


def products_to_rows(
    products: list[dict],
    badges: dict | None = None,
    photo_data: dict[str, dict[str, str]] | None = None,
    new_names: set | None = None,
) -> list[list]:
    """Преобразовать список товаров в строки для Google Sheet.

    Формат: [Наименование, Цена, Остаток, Категория, Группа, Поставщик, Badge, ImageUrl, Description]
    Товары из new_names (реально новые) получают бейдж «новинка».
    """
    if badges is None:
        badges = {"исключения": [], "новинка": [], "хит": [], "акция": []}
    if photo_data is None:
        photo_data = {}
    new_names = new_names or set()
    header = ["Наименование", "Цена", "Остаток", "Категория", "Группа", "Поставщик", "Badge", "ImageUrl", "Description"]
    rows = [header]
    for p in products:
        badge = "новинка" if p["name"] in new_names else get_badge(p["name"], badges)
        rows.append([
            p["name"],
            p["price"],
            p["stock"],
            p["source_category"],
            p["display_group"],
            p["supplier_file"],
            badge,
            get_photo_url(p["name"], photo_data),
            get_photo_description(p["name"], photo_data),
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
            title=sheet_name, rows=len(rows) + 10, cols=9
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

    # Загрузить маппинг фото
    photo_data = load_photo_data()

    # Парсить все файлы (авто-определение формата: старый vs новый)
    all_products = []
    new_format_used = False
    for filepath in xlsx_files:
        wb = openpyxl.load_workbook(filepath, data_only=True, read_only=True)
        price_col, stock_col = find_header_cols(wb.active)
        wb.close()
        if is_new_format(price_col):
            new_format_used = True
            all_products.extend(parse_new_format(filepath, price_col, stock_col))
        else:
            all_products.extend(parse_excel_file(filepath))

    log.info("Всего товаров из %d файлов: %d", len(xlsx_files), len(all_products))

    # Применить маппинг групп (старый формат — по category_map + переопределения)
    all_products = apply_group_mapping(all_products, category_map)

    # Новый формат: групп в файле нет — берём из текущего каталога по названию,
    # а товары, которых раньше не было, помечаем как новинки и кладём в «Новинки».
    new_names: set = set()
    if new_format_used:
        current_groups = load_current_groups()
        if not current_groups:
            log.error("Новый формат, но не удалось прочитать текущие группы каталога — "
                      "обновление прервано (иначе все товары попали бы в «Новинки»).")
            sys.exit(1)
        new_count = 0
        for p in all_products:
            if p["source_category"] == "":  # пришёл из нового формата
                g = current_groups.get(normalize_name(p["name"]))
                if g and g != "Новинки":
                    p["display_group"] = g
                else:
                    p["display_group"] = "Новинки"
                    new_names.add(p["name"])
                    new_count += 1
        log.info("Новых товаров (в «Новинки»): %d", new_count)

    # Подготовить строки для Google Sheet
    rows = products_to_rows(all_products, badges, photo_data, new_names)

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
