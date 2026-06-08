# -*- coding: utf-8 -*-
"""
link_quality_photos.py — загрузка и привязка КАЧЕСТВЕННЫХ фото из трёх папок.

Назначение: разовый скрипт (по аналогии с akkond_search) для папок
photos/kids, photos/difrent, photos/Mistral. Делает:
  1. читает список товаров (_products_tmp.json, полученный через sheet_helper.py);
  2. отбирает качественные изображения (jpg/jpeg/png/webp, min(w,h) >= 500);
  3. сопоставляет файл с товаром по нормализованному имени;
  4. грузит сопоставленные файлы в Cloudinary (папка = kids/difrent/mistral);
  5. пишет secure_url в scripts/photo_urls.json (ключ = имя файла);
  6. привязывает товар в scripts/photo_overrides.json (значение = "<папка>/<файл>"),
     удаляет старую запись-скриншот этого товара.

Браузер/сервер/.env/credentials не трогаются. upload.py НЕ запускается.
"""

import os
import re
import sys
import json
from pathlib import Path

from PIL import Image
import cloudinary
import cloudinary.uploader

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Папка-источник (относительно корня проекта) → имя папки в Cloudinary
FOLDER_MAP = {
    PROJECT_ROOT / "photos" / "kids": "kids",
    PROJECT_ROOT / "photos" / "difrent": "difrent",
    PROJECT_ROOT / "photos" / "Mistral": "mistral",
}

VALID_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MIN_SIDE = 500

PHOTO_URLS_PATH = SCRIPT_DIR / "photo_urls.json"
PHOTO_OVERRIDES_PATH = SCRIPT_DIR / "photo_overrides.json"
PRODUCTS_TMP = PROJECT_ROOT / "_products_tmp.json"


def load_env() -> None:
    """Загрузить переменные из .env (как в upload.py)."""
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def normalize_name(name: str) -> str:
    """Нормализация имени для сопоставления (как в задании/sheet_helper)."""
    return re.sub(r"\s+", " ", re.sub(r",\s*[А-Яа-яA-Za-z.]+\s*$", "", name)).strip().lower()


def is_quality_image(path: Path) -> bool:
    """Качественное изображение: допустимое расширение и min(w,h) >= 500."""
    if path.suffix.lower() not in VALID_EXT:
        return False
    try:
        with Image.open(path) as im:
            w, h = im.size
        return min(w, h) >= MIN_SIDE
    except Exception:
        return False


def main() -> None:
    load_env()

    cloudinary.config(
        cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
        api_key=os.environ["CLOUDINARY_API_KEY"],
        api_secret=os.environ["CLOUDINARY_API_SECRET"],
        secure=True,
    )

    # --- Список товаров ---
    products = json.loads(PRODUCTS_TMP.read_text(encoding="utf-8"))
    product_names = [p["name"] for p in products]
    # Индекс: норм_имя → список полных имён (для выявления неоднозначности)
    norm_to_products: dict[str, list[str]] = {}
    for name in product_names:
        norm_to_products.setdefault(normalize_name(name), []).append(name)

    # --- Существующие JSON ---
    photo_urls = json.loads(PHOTO_URLS_PATH.read_text(encoding="utf-8")) if PHOTO_URLS_PATH.exists() else {}
    overrides = json.loads(PHOTO_OVERRIDES_PATH.read_text(encoding="utf-8")) if PHOTO_OVERRIDES_PATH.exists() else {}

    report: dict[str, dict] = {}
    screenshots_replaced = 0

    for src_dir, cloud_folder in FOLDER_MAP.items():
        r = {
            "total": 0,
            "linked": 0,
            "skipped_quality": [],
            "skipped_numeric": [],
            "skipped_notfound": [],
            "skipped_ambiguous": [],
            "linked_names": [],
        }
        if not src_dir.exists():
            report[cloud_folder] = r
            continue

        for fpath in sorted(src_dir.iterdir()):
            if not fpath.is_file():
                continue
            r["total"] += 1
            fname = fpath.name
            stem = fpath.stem

            # 2. Качество
            if not is_quality_image(fpath):
                r["skipped_quality"].append(fname)
                continue

            # 3a. Имя-число → пропуск
            if re.fullmatch(r"\d+", stem.strip()):
                r["skipped_numeric"].append(fname)
                continue

            # 3b. Сопоставление по нормализованному имени
            nf = normalize_name(stem)
            matched: list[str] = []
            for norm_p, full_list in norm_to_products.items():
                # точное равенство ИЛИ имя файла = префикс/подстрока имени товара
                if nf == norm_p or (nf and nf in norm_p):
                    matched.extend(full_list)

            # Уникальные РАЗНЫЕ товары
            unique_matched = list(dict.fromkeys(matched))

            if not unique_matched:
                r["skipped_notfound"].append(fname)
                continue
            if len(unique_matched) > 1:
                r["skipped_ambiguous"].append(f"{fname} -> {unique_matched}")
                continue

            product = unique_matched[0]

            # 4. Загрузка в Cloudinary. public_id = "<папка>/<stem безопасный>".
            # Слешей в именах нет (проверено), но на всякий случай чистим.
            safe_stem = stem.replace("/", "-").replace("\\", "-")
            safe_fname = safe_stem + fpath.suffix.lower()
            public_id = f"{cloud_folder}/{safe_stem}"

            try:
                res = cloudinary.uploader.upload(
                    str(fpath),
                    public_id=public_id,
                    overwrite=True,
                    resource_type="image",
                    eager=[{"format": "webp", "quality": "auto"}],
                    eager_async=True,
                )
            except Exception as e:
                r["skipped_notfound"].append(f"{fname} (ошибка загрузки: {e})")
                continue

            secure_url = res["secure_url"]

            # 5. photo_urls.json: ключ = безопасное имя файла с расширением
            photo_urls[safe_fname] = secure_url

            # Зафиксировать замену скриншота, если у самого товара она была
            if "creenshot" in str(overrides.get(product, "")).lower():
                screenshots_replaced += 1

            # 6. override: ключ = полное имя товара, значение = "<папка>/<safe_fname>"
            overrides[product] = f"{cloud_folder}/{safe_fname}"

            # Удалить старую запись-скриншот ЭТОГО товара под ДРУГИМ ключом
            # (ключ совпадает с product по подстроке И значение содержит "creenshot")
            to_del = []
            for k, v in overrides.items():
                if k == product:
                    continue
                if "creenshot" in str(v).lower() and (
                    normalize_name(k) == normalize_name(product)
                    or product in k
                    or k in product
                ):
                    to_del.append(k)
            for k in to_del:
                del overrides[k]
                screenshots_replaced += 1

            r["linked"] += 1
            r["linked_names"].append(f"{product}  <=  {fname}")

        report[cloud_folder] = r

    # --- Сохранить JSON ---
    PHOTO_URLS_PATH.write_text(
        json.dumps(photo_urls, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    PHOTO_OVERRIDES_PATH.write_text(
        json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- Отчёт ---
    out = {"folders": report, "screenshots_replaced": screenshots_replaced}
    sys.stdout.buffer.write(
        json.dumps(out, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    )


if __name__ == "__main__":
    main()
