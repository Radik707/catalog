"""
make_manual_sheet.py — Создание Excel для ручной привязки фото и описаний к товарам

Использование:
    python make_manual_sheet.py
    python make_manual_sheet.py --price C:\\другая\\папка

Результат: C:\\catalog\\photo_manual.xlsx
  Лист "Товары": A=Название, B=Группа, C=Файл фото, D=Описание, E=Статус
  Сортировка: сначала товары без фото, потом с фото.
"""

import os
import sys
import json
import glob
import logging
import argparse
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

DEFAULT_PRICE_DIR = r"C:\price"
OUTPUT_PATH = PROJECT_ROOT / "photo_manual.xlsx"


# ── Загрузка данных ───────────────────────────────────────────────────────────

def load_env() -> None:
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


def load_category_map() -> dict:
    path = SCRIPT_DIR / "category_map.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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

PRODUCT_CONTAINS_OVERRIDES = [
    ("паста шок", "Батончики и шоколад"),
    ("шок. паста", "Батончики и шоколад"),
]


def get_group(name: str, source_category: str, category_map: dict) -> str:
    name_lower = name.lower()
    for prefix, group in PRODUCT_OVERRIDES.items():
        if name_lower.startswith(prefix.lower()):
            return group
    for substring, group in PRODUCT_CONTAINS_OVERRIDES:
        if substring.lower() in name_lower:
            return group
    return category_map.get(source_category, "Другое")


def parse_products(price_dir: Path, category_map: dict) -> list[dict]:
    """Загрузить уникальные товары из всех Excel-прайсов."""
    xlsx_files = sorted(glob.glob(str(price_dir / "*.xlsx")))
    if not xlsx_files:
        log.error("В папке %s нет .xlsx файлов", price_dir)
        sys.exit(1)

    seen: set[str] = set()
    products: list[dict] = []

    for filepath in xlsx_files:
        wb = openpyxl.load_workbook(filepath, data_only=True, read_only=True)
        ws = wb.active
        current_category = "Без категории"

        for row in ws.iter_rows(min_row=1, values_only=True):
            a = row[0] if len(row) > 0 else None
            b = row[1] if len(row) > 1 else None
            c = row[2] if len(row) > 2 else None

            if a is None and b is None and c is None:
                continue

            b_str = str(b).strip().lower() if b else ""
            if b_str == "цена":
                continue

            if a is not None and str(a).strip() and b is None and c is None:
                raw = str(a).strip()
                if len(raw) >= 2 and raw[0] == "а" and raw[1].isupper():
                    raw = raw[1:]
                current_category = raw
                continue

            if a is not None and b is not None:
                name = str(a).strip()
                if not name or name in seen:
                    continue
                try:
                    float(b)
                except (ValueError, TypeError):
                    continue
                seen.add(name)
                products.append({
                    "name": name,
                    "group": get_group(name, current_category, category_map),
                })

        wb.close()

    log.info("Товаров из прайсов: %d (уникальных)", len(products))
    return products


def load_photo_overrides() -> dict[str, str]:
    """Загрузить photo_overrides.json → {excel_name: file_name}."""
    path = SCRIPT_DIR / "photo_overrides.json"
    if not path.exists():
        log.warning("photo_overrides.json не найден — фото не будут предзаполнены")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    log.info("Загружено привязок фото: %d", len(data))
    return data


def load_file_to_description() -> dict[str, str]:
    """Загрузить photo_map.json → {file_name: description}."""
    path = SCRIPT_DIR / "photo_map.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        photo_map = json.load(f)

    result: dict[str, str] = {}
    for entry in photo_map:
        fn = entry.get("file_name")
        desc = (entry.get("description") or "").strip()
        if fn and desc and fn not in result:
            result[fn] = desc
    return result


def load_description_overrides() -> dict[str, str]:
    """Загрузить description_overrides.json → {excel_name: description}."""
    path = SCRIPT_DIR / "description_overrides.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Стили ─────────────────────────────────────────────────────────────────────

def style_header(cell, bg_hex: str) -> None:
    cell.font = Font(bold=True, color="FFFFFF", size=10)
    cell.fill = PatternFill("solid", fgColor=bg_hex)
    cell.alignment = Alignment(horizontal="center", vertical="center")
    thin = Side(style="thin", color="FFFFFF")
    cell.border = Border(left=thin, right=thin, bottom=thin)


def style_data(cell, wrap: bool = False) -> None:
    cell.alignment = Alignment(vertical="center", wrap_text=wrap)
    cell.font = Font(size=10)


# ── Построение листа ──────────────────────────────────────────────────────────

def build_sheet(
    wb: openpyxl.Workbook,
    products: list[dict],
    overrides: dict[str, str],
    file_to_desc: dict[str, str],
    desc_overrides: dict[str, str],
) -> tuple[int, int]:
    """Создать лист «Товары». Возвращает (с_фото, без_фото)."""
    ws = wb.create_sheet("Товары")

    # Заголовки
    headers = ["Название товара", "Группа", "Файл фото", "Описание товара", "Статус"]
    colors = ["2E75B6", "2E75B6", "375623", "7030A0", "C55A11"]
    for col, (header, color) in enumerate(zip(headers, colors), 1):
        cell = ws.cell(row=1, column=col, value=header)
        style_header(cell, color)
    ws.row_dimensions[1].height = 20

    # Собрать строки с данными
    rows_without: list[dict] = []
    rows_with: list[dict] = []

    for p in products:
        name = p["name"]
        file_name = overrides.get(name, "")
        description = desc_overrides.get(name, "")
        if not description and file_name:
            description = file_to_desc.get(file_name, "")

        row_data = {
            "name": name,
            "group": p["group"],
            "file_name": file_name,
            "description": description,
        }
        if file_name:
            rows_with.append(row_data)
        else:
            rows_without.append(row_data)

    # Сортировка: без фото первыми (по имени), потом с фото (по имени)
    rows_without.sort(key=lambda r: r["name"].lower())
    rows_with.sort(key=lambda r: r["name"].lower())
    all_rows = rows_without + rows_with

    # Запись данных
    for row_idx, r in enumerate(all_rows, 2):
        has_photo = bool(r["file_name"])
        bg = "EBF3FB" if row_idx % 2 == 0 else "FFFFFF"
        if has_photo:
            bg = "EBF7EE" if row_idx % 2 == 0 else "F5FBF7"

        ws.cell(row=row_idx, column=1, value=r["name"])
        ws.cell(row=row_idx, column=2, value=r["group"])
        ws.cell(row=row_idx, column=3, value=r["file_name"])
        ws.cell(row=row_idx, column=4, value=r["description"])
        # Колонка E: формула — если C заполнена, ✅, иначе ❌
        ws.cell(row=row_idx, column=5, value=f'=IF(C{row_idx}<>"","✅","❌")')

        for col in range(1, 6):
            cell = ws.cell(row=row_idx, column=col)
            wrap = col == 4
            style_data(cell, wrap=wrap)
            cell.fill = PatternFill("solid", fgColor=bg)

    # Ширина колонок
    ws.column_dimensions["A"].width = 50
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 30
    ws.column_dimensions["D"].width = 60
    ws.column_dimensions["E"].width = 10

    # Заморозить первую строку
    ws.freeze_panes = "A2"

    # Автофильтр
    total = len(all_rows)
    ws.auto_filter.ref = f"A1:E{total + 1}"

    log.info("Лист «Товары»: %d строк", total)
    return len(rows_with), len(rows_without)


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    load_env()

    parser = argparse.ArgumentParser(
        description="Создание Excel для ручной привязки фото и описаний"
    )
    parser.add_argument(
        "--price",
        default=os.environ.get("EXCEL_DIR", DEFAULT_PRICE_DIR),
        help=f"Папка с .xlsx прайсами (по умолчанию: {DEFAULT_PRICE_DIR})",
    )
    args = parser.parse_args()

    price_dir = Path(args.price)
    if not price_dir.exists():
        log.error("Папка с прайсами не найдена: %s", price_dir)
        sys.exit(1)

    category_map = load_category_map()
    products = parse_products(price_dir, category_map)
    overrides = load_photo_overrides()
    file_to_desc = load_file_to_description()
    desc_overrides = load_description_overrides()

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    with_photo, without_photo = build_sheet(wb, products, overrides, file_to_desc, desc_overrides)

    wb.save(OUTPUT_PATH)
    log.info("Файл сохранён: %s", OUTPUT_PATH)

    total = with_photo + without_photo
    print(f"\nГотово!")
    print(f"  Товаров всего:  {total}")
    print(f"  С фото:         {with_photo}")
    print(f"  Без фото:       {without_photo}")
    print(f"  Файл:           {OUTPUT_PATH}")
    print()
    print("Инструкция:")
    print("  1. Откройте photo_manual.xlsx")
    print("  2. Заполните колонку C (файл фото) и/или D (описание) для нужных товаров")
    print("  3. Запустите: python scripts/apply_manual_sheet.py")


if __name__ == "__main__":
    main()
