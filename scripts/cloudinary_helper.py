"""
cloudinary_helper.py — Загрузка одного фото товара в Cloudinary (папка presenter/).

Назначение: вызывается из admin.py через shell-out (_run_py) при привязке фото
товара в панели администратора. Папка всегда presenter/ — фото из панели (D-06).

Интерфейс командной строки:
    python cloudinary_helper.py upload --path <tmp_path> --name <original_name>

Результат — JSON в stdout:
    {"ok": true,  "ref": "presenter/<stem>.<ext>", "url": "<secure_url>"}
    {"ok": false, "message": "<причина отказа>"}

Код возврата: 0 = успех, 1 = ошибка.
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path

# Настройка логирования в stderr (чтобы не мешать JSON в stdout)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
log = logging.getLogger("cloudinary_helper")

# Расположение директорий
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Папка в Cloudinary для фото из панели администратора — всегда presenter/ (D-06)
CLOUDINARY_FOLDER = "presenter"


def _print_json(data: dict) -> None:
    """Напечатать JSON-ответ в stdout в UTF-8 (обход cp1252 на Windows)."""
    out = json.dumps(data, ensure_ascii=False)
    sys.stdout.buffer.write((out + "\n").encode("utf-8"))
    sys.stdout.buffer.flush()


def load_env() -> None:
    """Загрузить переменные из .env — сначала PROJECT_ROOT, потом SCRIPT_DIR.

    Использует os.environ.setdefault: уже установленные переменные не перезаписываются.
    Паттерн скопирован из upload_photos.py строки 60–76.
    """
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
                    os.environ.setdefault(key.strip(), value.strip().strip("'\""))
            return


def init_cloudinary():
    """Инициализировать Cloudinary из переменных окружения.

    При отсутствии ключей — печатает JSON {ok: false} и завершает процесс.
    Ключи не попадают в ответ клиенту (T-04-11).
    """
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    api_key = os.environ.get("CLOUDINARY_API_KEY", "")
    api_secret = os.environ.get("CLOUDINARY_API_SECRET", "")

    # Проверка наличия всех трёх ключей
    if not all([cloud_name, api_key, api_secret]):
        missing = [k for k, v in {
            "CLOUDINARY_CLOUD_NAME": cloud_name,
            "CLOUDINARY_API_KEY": api_key,
            "CLOUDINARY_API_SECRET": api_secret,
        }.items() if not v]
        log.error("Не заданы переменные Cloudinary: %s", ", ".join(missing))
        _print_json({"ok": False, "message": "Cloudinary не настроен"})
        sys.exit(1)

    # Импорт cloudinary только после проверки ключей
    try:
        import cloudinary
        import cloudinary.uploader
    except ImportError:
        log.error("cloudinary не установлен. Выполните: pip install cloudinary>=1.40")
        _print_json({"ok": False, "message": "Cloudinary не установлен на сервере"})
        sys.exit(1)

    # Конфигурация SDK — secure=True для HTTPS URL (паттерн из upload_photos.py)
    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )

    return cloudinary


def get_ref(original_name: str) -> str:
    """Сформировать ссылку привязки фото для вкладки «Правки».

    Формат: "presenter/<stem>.<ext>" — папка всегда presenter/ (D-06).
    Пример: "photo.jpg" → "presenter/photo.jpg"

    Используется как значение правки типа 'photo' в «Правках» Google Sheet.
    """
    stem = Path(original_name).stem
    ext = Path(original_name).suffix.lower()
    if not ext:
        ext = ".jpg"
    return f"{CLOUDINARY_FOLDER}/{stem}{ext}"


def get_public_id(original_name: str) -> str:
    """Сформировать public_id для Cloudinary (без расширения).

    Cloudinary хранит расширение отдельно, поэтому public_id = folder/stem.
    Пример: "photo.jpg" → "presenter/photo"
    """
    stem = Path(original_name).stem
    return f"{CLOUDINARY_FOLDER}/{stem}"


def upload_file(tmp_path: str, original_name: str) -> None:
    """Загрузить файл в Cloudinary presenter/ и вернуть результат в JSON.

    Параметры:
        tmp_path      — путь к временному файлу на диске
        original_name — оригинальное имя файла (для public_id и ref)

    Выводит в stdout:
        {ok: true, ref: "presenter/<stem>.<ext>", url: "<secure_url>"}
        {ok: false, message: "Не удалось загрузить фото"} при ошибке

    Ошибки Cloudinary — только в лог, клиенту нейтральное сообщение (T-04-11).
    """
    cloudinary_mod = init_cloudinary()
    import cloudinary.uploader

    public_id = get_public_id(original_name)
    ref = get_ref(original_name)

    log.info("Загружаю: %s → public_id=%s", original_name, public_id)

    try:
        result = cloudinary.uploader.upload(
            tmp_path,
            public_id=public_id,
            overwrite=True,              # замена фото при повторной загрузке
            resource_type="image",
            # Автогенерация WebP при запросе (как в upload_photos.py)
            eager=[{"format": "webp", "quality": "auto"}],
            eager_async=True,
        )
        url = result["secure_url"]
        log.info("Загружено успешно: %s", url)
        _print_json({"ok": True, "ref": ref, "url": url})

    except Exception as e:
        # Технические детали — только в лог, не в ответ клиенту (T-04-11)
        log.error("Ошибка загрузки %s: %s", original_name, e)
        _print_json({"ok": False, "message": "Не удалось загрузить фото"})
        sys.exit(1)


def main() -> None:
    """Точка входа командной строки."""
    parser = argparse.ArgumentParser(
        description="Загрузка одного фото в Cloudinary (presenter/)"
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    # Подкоманда upload — загрузить один файл
    upload_parser = subparsers.add_parser("upload", help="Загрузить фото в presenter/")
    upload_parser.add_argument("--path", required=True, help="Путь к временному файлу на диске")
    upload_parser.add_argument("--name", required=True, help="Оригинальное имя файла (для public_id и ref)")

    args = parser.parse_args()

    # Загружаем переменные окружения перед выполнением
    load_env()

    if args.action == "upload":
        upload_file(args.path, args.name)


if __name__ == "__main__":
    main()
