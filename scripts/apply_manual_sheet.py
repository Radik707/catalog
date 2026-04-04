"""
apply_manual_sheet.py — Применение ручной привязки из photo_manual.xlsx

Читает photo_manual.xlsx (лист «Товары»):
  A: Название товара
  C: Файл фото → обновляет photo_overrides.json
  D: Описание   → обновляет description_overrides.json

Использование:
    python apply_manual_sheet.py
    python apply_manual_sheet.py --dry-run   # показать без сохранения
"""

import sys
import json
import logging
import argparse
from pathlib import Path

import openpyxl

sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

SHEET_PATH = PROJECT_ROOT / "photo_manual.xlsx"
OVERRIDES_PATH = SCRIPT_DIR / "photo_overrides.json"
DESC_OVERRIDES_PATH = SCRIPT_DIR / "description_overrides.json"


def load_existing(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Применение ручной привязки фото и описаний из photo_manual.xlsx"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Показать результат без сохранения файлов",
    )
    args = parser.parse_args()

    if not SHEET_PATH.exists():
        log.error("Файл не найден: %s", SHEET_PATH)
        log.error("Сначала запустите: python scripts/make_manual_sheet.py")
        raise SystemExit(1)

    wb = openpyxl.load_workbook(SHEET_PATH, data_only=True, read_only=True)

    if "Товары" not in wb.sheetnames:
        log.error("Лист «Товары» не найден в %s", SHEET_PATH)
        raise SystemExit(1)

    ws = wb["Товары"]

    new_photos: dict[str, str] = {}    # {product_name: file_name}
    new_descs: dict[str, str] = {}     # {product_name: description}
    skipped = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        name = str(row[0]).strip() if row[0] else ""
        raw_file = str(row[2]).strip() if len(row) > 2 and row[2] else ""
        description = str(row[3]).strip() if len(row) > 3 and row[3] else ""

        if not name:
            skipped += 1
            continue

        if raw_file:
            # Извлечь только имя файла из file:///C:/path/to/447.webp или просто 447.webp
            file_name = Path(raw_file.replace("file:///", "").replace("file://", "")).name
            if not file_name:
                log.warning("Не удалось извлечь имя файла из: %s", raw_file)
                skipped += 1
                continue
            # Исправить двойное расширение: 869.jpgjpg → 869.jpg
            for ext in (".jpgjpg", ".jpegjpeg", ".pngpng", ".webpwebp"):
                if file_name.lower().endswith(ext):
                    trim = len(ext) // 2  # 7//2=3 для .jpgjpg
                    file_name = file_name[: len(file_name) - trim]
                    log.warning("Исправлено двойное расширение: %s → %s", raw_file, file_name)
                    break
            if name in new_photos:
                log.warning("Дубль товара «%s» — оставляю первое вхождение", name)
            else:
                new_photos[name] = file_name

        if description:
            if name not in new_descs:
                new_descs[name] = description

    wb.close()

    log.info(
        "Прочитано: фото=%d, описаний=%d, пустых строк=%d",
        len(new_photos), len(new_descs), skipped,
    )

    if not new_photos and not new_descs:
        print("Нет заполненных строк. Заполните колонки C и/или D в photo_manual.xlsx.")
        return

    if args.dry_run:
        if new_photos:
            print(f"\n--- Привязки фото (dry-run, {len(new_photos)} шт.) ---")
            for name, fn in list(new_photos.items())[:20]:
                print(f"  {name!r}  →  {fn}")
            if len(new_photos) > 20:
                print(f"  ... и ещё {len(new_photos) - 20}")
        if new_descs:
            print(f"\n--- Описания (dry-run, {len(new_descs)} шт.) ---")
            for name, desc in list(new_descs.items())[:10]:
                print(f"  {name!r}  →  {desc[:60]}...")
            if len(new_descs) > 10:
                print(f"  ... и ещё {len(new_descs) - 10}")
        return

    # ── Обновить photo_overrides.json ─────────────────────────────────────────
    photo_added = photo_updated = 0
    if new_photos:
        existing_photos = load_existing(OVERRIDES_PATH)
        log.info("Существующих привязок в photo_overrides.json: %d", len(existing_photos))
        for name, fn in new_photos.items():
            if name in existing_photos:
                photo_updated += 1
            else:
                photo_added += 1
        merged_photos = {**existing_photos, **new_photos}
        save_json(OVERRIDES_PATH, merged_photos)
        log.info("Сохранено в %s", OVERRIDES_PATH)

    # ── Обновить description_overrides.json ───────────────────────────────────
    desc_added = desc_updated = 0
    if new_descs:
        existing_descs = load_existing(DESC_OVERRIDES_PATH)
        log.info("Существующих описаний в description_overrides.json: %d", len(existing_descs))
        for name in new_descs:
            if name in existing_descs:
                desc_updated += 1
            else:
                desc_added += 1
        merged_descs = {**existing_descs, **new_descs}
        save_json(DESC_OVERRIDES_PATH, merged_descs)
        log.info("Сохранено в %s", DESC_OVERRIDES_PATH)

    # ── Итог ──────────────────────────────────────────────────────────────────
    print(f"\nПривязано фото:    {len(new_photos)}  (новых: {photo_added}, обновлено: {photo_updated})")
    print(f"Добавлено описаний: {len(new_descs)}  (новых: {desc_added}, обновлено: {desc_updated})")
    print()
    if new_photos:
        print(f"  → {OVERRIDES_PATH}")
    if new_descs:
        print(f"  → {DESC_OVERRIDES_PATH}")
    print()
    print("Следующий шаг: python scripts/upload.py  (обновит Google Sheet)")


if __name__ == "__main__":
    main()
