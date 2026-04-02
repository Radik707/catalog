"""
upload_photos.py — Загрузка фото товаров в Cloudinary
Задача 3.4.2

Читает photo_map.json, загружает файлы из папки photos/ в Cloudinary,
сохраняет photo_urls.json: {file_name → secure_url}.

Использование:
    python upload_photos.py              # загрузить все новые фото
    python upload_photos.py --force      # перезагрузить уже загруженные
    python upload_photos.py --dry-run    # показать что будет загружено

Настройка (.env в корне проекта):
    CLOUDINARY_CLOUD_NAME=mycloud
    CLOUDINARY_API_KEY=123456789
    CLOUDINARY_API_SECRET=abc...
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# --- Настройка логирования ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

PHOTOS_DIR = PROJECT_ROOT / "photos"
PHOTO_MAP_PATH = SCRIPT_DIR / "photo_map.json"
PHOTO_URLS_PATH = SCRIPT_DIR / "photo_urls.json"
PHOTO_OVERRIDES_PATH = SCRIPT_DIR / "photo_overrides.json"

# Папка в Cloudinary для всех фото каталога
CLOUDINARY_FOLDER = "catalog"


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------

def load_env() -> None:
    """Загрузить переменные из .env (как в upload.py)."""
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
                    os.environ.setdefault(key, value)
            return


def load_photo_map() -> list[dict]:
    """Загрузить photo_map.json."""
    if not PHOTO_MAP_PATH.exists():
        log.error("photo_map.json не найден: %s", PHOTO_MAP_PATH)
        log.error("Сначала запустите: python extract_photos.py")
        sys.exit(1)
    with open(PHOTO_MAP_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_photo_urls() -> dict[str, str]:
    """Загрузить существующий photo_urls.json (для пропуска уже загруженных)."""
    if PHOTO_URLS_PATH.exists():
        with open(PHOTO_URLS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_photo_urls(urls: dict[str, str]) -> None:
    """Сохранить photo_urls.json."""
    with open(PHOTO_URLS_PATH, "w", encoding="utf-8") as f:
        json.dump(urls, f, ensure_ascii=False, indent=2)


def get_public_id(file_name: str) -> str:
    """Сформировать public_id для Cloudinary из имени файла.

    «faradella-glazirovannyj.jpg» → «catalog/faradella-glazirovannyj»
    Расширение не включается — Cloudinary хранит его отдельно.
    """
    stem = Path(file_name).stem
    return f"{CLOUDINARY_FOLDER}/{stem}"


# ---------------------------------------------------------------------------
# Основная логика
# ---------------------------------------------------------------------------

def main() -> None:
    load_env()

    parser = argparse.ArgumentParser(
        description="Загрузка фото товаров в Cloudinary"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Перезагрузить уже загруженные фото (overwrite=True)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Показать список файлов без загрузки",
    )
    args = parser.parse_args()

    # --- Проверить переменные Cloudinary ---
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    api_key = os.environ.get("CLOUDINARY_API_KEY", "")
    api_secret = os.environ.get("CLOUDINARY_API_SECRET", "")

    if not all([cloud_name, api_key, api_secret]):
        missing = [k for k, v in {
            "CLOUDINARY_CLOUD_NAME": cloud_name,
            "CLOUDINARY_API_KEY": api_key,
            "CLOUDINARY_API_SECRET": api_secret,
        }.items() if not v]
        log.error("Не заданы переменные в .env: %s", ", ".join(missing))
        sys.exit(1)

    # --- Импорт Cloudinary ---
    try:
        import cloudinary
        import cloudinary.uploader
    except ImportError:
        log.error("cloudinary не установлен. Выполните: pip install cloudinary")
        sys.exit(1)

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )

    # --- Загрузить данные ---
    photo_map = load_photo_map()
    photo_urls = load_photo_urls()

    if args.force:
        log.info("--force: существующие записи будут перезаписаны")

    # --- Источник 1: photo_map.json (автоматические из PDF) ---
    # file_name → список товаров (несколько товаров могут делить одно фото)
    files_to_upload: dict[str, list[str]] = {}
    for entry in photo_map:
        fn = entry.get("file_name")
        if not fn:
            continue
        names = files_to_upload.setdefault(fn, [])
        names.append(entry.get("original_name", ""))

    # --- Источник 2: photo_overrides.json (ручные привязки) ---
    if PHOTO_OVERRIDES_PATH.exists():
        with open(PHOTO_OVERRIDES_PATH, "r", encoding="utf-8") as f:
            overrides: dict[str, str] = json.load(f)
        for product_name, fn in overrides.items():
            if fn and fn not in files_to_upload:
                files_to_upload[fn] = [product_name]
            elif fn:
                files_to_upload[fn].append(product_name)
        log.info("Добавлено из photo_overrides.json: %d уникальных файлов", len(overrides))

    # --- Источник 3: файлы в папке photos/, которых нет в photo_urls.json ---
    if PHOTOS_DIR.exists():
        for photo_path in sorted(PHOTOS_DIR.iterdir()):
            if photo_path.is_file() and photo_path.suffix.lower() in {
                ".jpg", ".jpeg", ".png", ".webp", ".gif"
            }:
                fn = photo_path.name
                if fn not in files_to_upload:
                    files_to_upload[fn] = []
        log.info("Всего файлов в папке photos/: %d", sum(
            1 for p in PHOTOS_DIR.iterdir()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        ))

    log.info("Уникальных файлов к проверке: %d", len(files_to_upload))
    log.info("Уже загружено в Cloudinary: %d", len(photo_urls))

    # --- Определить что нужно загружать ---
    to_upload = []
    skipped = 0
    missing_files = 0

    for file_name, product_names in sorted(files_to_upload.items()):
        photo_path = PHOTOS_DIR / file_name

        if not photo_path.exists():
            log.warning("Файл не найден: %s", photo_path)
            missing_files += 1
            continue

        if file_name in photo_urls and not args.force:
            skipped += 1
            continue

        to_upload.append((file_name, photo_path, product_names))

    log.info(
        "К загрузке: %d | Пропущено (уже есть): %d | Файлы не найдены: %d",
        len(to_upload),
        skipped,
        missing_files,
    )

    if args.dry_run:
        print("\n--- Файлы к загрузке (dry-run) ---")
        for file_name, photo_path, names in to_upload:
            size_kb = photo_path.stat().st_size // 1024
            print(f"  {file_name} ({size_kb} KB) → товары: {', '.join(names[:2])}"
                  + (" ..." if len(names) > 2 else ""))
        print(f"\nВсего: {len(to_upload)} файлов")
        return

    if not to_upload:
        print("Все фото уже загружены. Используйте --force для перезагрузки.")
        return

    # --- Загружать по одному ---
    uploaded = 0
    errors = 0

    for i, (file_name, photo_path, product_names) in enumerate(to_upload, 1):
        public_id = get_public_id(file_name)
        log.info(
            "[%d/%d] Загружаю: %s → %s",
            i, len(to_upload), file_name, public_id,
        )

        try:
            result = cloudinary.uploader.upload(
                str(photo_path),
                public_id=public_id,
                overwrite=args.force,
                resource_type="image",
                # Автоматически генерировать WebP при запросе
                eager=[{"format": "webp", "quality": "auto"}],
                eager_async=True,
            )
            url = result["secure_url"]
            photo_urls[file_name] = url
            uploaded += 1
            log.info("  ✓ %s", url)

            # Сохранять после каждого успешного upload (для возобновления)
            save_photo_urls(photo_urls)

        except Exception as e:
            log.error("  Ошибка загрузки %s: %s", file_name, e)
            errors += 1

    # --- Итог ---
    save_photo_urls(photo_urls)
    log.info("photo_urls.json сохранён: %s", PHOTO_URLS_PATH)

    print(f"\nГотово! Загружено: {uploaded} | Ошибок: {errors} | Пропущено: {skipped}")
    print(f"Всего URL в photo_urls.json: {len(photo_urls)}")
    if uploaded > 0:
        print(f"Файл карты URL: {PHOTO_URLS_PATH}")


if __name__ == "__main__":
    main()
