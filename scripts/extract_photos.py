"""
extract_photos.py — Извлечение фото товаров из PDF-каталога с помощью Claude Vision
Задача 3.4.1

Использование:
    python extract_photos.py                                        # PDF по умолчанию
    python extract_photos.py --pdf "C:\\catalog\\pdf\\catalog.pdf"  # указать PDF
    python extract_photos.py --start-page 10                        # начать с 10-й страницы
    python extract_photos.py --dry-run                              # без сохранения файлов

Настройка (.env в корне проекта):
    ANTHROPIC_API_KEY=sk-ant-...   # ключ API Claude
"""

import os
import sys
import json
import time
import base64
import logging
import argparse
import re
from pathlib import Path

# --- Настройка логирования ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

DEFAULT_PDF = PROJECT_ROOT / "pdf" / "Accond catalog.pdf"
DEFAULT_PHOTOS_DIR = PROJECT_ROOT / "photos"
PHOTO_MAP_PATH = SCRIPT_DIR / "photo_map.json"

CLAUDE_PROMPT = (
    "Analyze this product catalog page. For each product on the page, return a JSON array: "
    '[{"name": "product name in Russian", '
    '"description": "product description/composition/flavor in Russian (if visible)", '
    '"image_index": sequential number of the product photo on this page '
    "(top to bottom, left to right, starting from 1)}]. "
    "If the page has no products (cover, table of contents, decorative page), return empty array []. "
    "Return ONLY valid JSON, no other text."
)


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------

def load_env() -> None:
    """Загрузить переменные из .env (как в upload.py — без python-dotenv)."""
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


def slugify(name: str) -> str:
    """Транслитерировать русское название в ASCII-slug для имени файла.

    «Фараделла глазированная» → «faradella-glazirovannaja»
    """
    try:
        from transliterate import translit
        slug = translit(name, "ru", reversed=True)
    except Exception:
        # Fallback: убираем кириллицу, оставляем латиницу и цифры
        log.warning("transliterate недоступен — используется fallback для: %s", name)
        slug = name
    slug = slug.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "product"


# ---------------------------------------------------------------------------
# Работа с PDF (PyMuPDF)
# ---------------------------------------------------------------------------

def render_page_png(page) -> bytes:
    """Рендерить страницу в PNG при 200 DPI."""
    import fitz  # noqa: F401 — только для Matrix
    zoom = 200 / 72  # 72 DPI — базовое разрешение PDF
    mat = page.fitz.Matrix(zoom, zoom) if hasattr(page, "fitz") else __import__("fitz").Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return pix.tobytes("png")


def get_page_images_sorted(page) -> list[dict]:
    """Извлечь изображения страницы, отфильтровать мелкие, отсортировать по позиции.

    Сортировка: сверху вниз, слева направо — совпадает с image_index от Claude.

    Возвращает список dict: {xref, width, height, y0, x0}
    """
    result = []
    seen = set()

    # get_images(full=True) → (xref, smask, w, h, bpc, cs, alt_cs, name, filter, ref)
    for img_tuple in page.get_images(full=True):
        xref = img_tuple[0]
        w = img_tuple[2]
        h = img_tuple[3]

        if w < 100 or h < 100:
            continue
        if xref in seen:
            continue
        seen.add(xref)

        # Получить положение на странице
        try:
            rects = page.get_image_rects(xref)
        except Exception:
            rects = []

        if not rects:
            # Если позиция неизвестна, ставим в конец
            result.append({"xref": xref, "width": w, "height": h, "y0": 1e9, "x0": 1e9})
            continue

        bbox = rects[0]
        result.append({"xref": xref, "width": w, "height": h, "y0": bbox.y0, "x0": bbox.x0})

    # Сортируем: по строкам сверху вниз (шаг 60 пт), внутри строки — слева направо
    result.sort(key=lambda x: (int(x["y0"] / 60), x["x0"]))
    return result


def save_image(doc, xref: int, out_path: Path) -> bool:
    """Извлечь изображение из PDF и сохранить как JPEG.

    Если изображение уже в JPEG — сохраняем raw байты.
    Иначе — конвертируем через fitz.Pixmap.
    Возвращает True при успехе.
    """
    import fitz

    try:
        base_img = doc.extract_image(xref)
    except Exception as e:
        log.warning("    Не удалось извлечь xref=%d: %s", xref, e)
        return False

    img_bytes = base_img["image"]
    ext = base_img.get("ext", "").lower()

    try:
        if ext in ("jpeg", "jpg"):
            out_path.write_bytes(img_bytes)
        else:
            # Конвертируем в JPEG через Pixmap
            pix = fitz.Pixmap(img_bytes)
            if pix.n > 4:
                # CMYK → RGB
                pix = fitz.Pixmap(fitz.csRGB, pix)
            pix.save(str(out_path), output="jpeg")
        return True
    except Exception as e:
        log.warning("    Ошибка сохранения изображения: %s", e)
        return False


# ---------------------------------------------------------------------------
# Claude Vision API
# ---------------------------------------------------------------------------

def ask_claude(client, page_png: bytes) -> list[dict]:
    """Отправить PNG страницы в Claude Vision, получить список товаров."""
    b64 = base64.standard_b64encode(page_png).decode("utf-8")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": b64,
                    },
                },
                {"type": "text", "text": CLAUDE_PROMPT},
            ],
        }],
    )

    text = response.content[0].text.strip()

    # Убрать markdown-обёртку ```json ... ``` если Claude добавил
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    return json.loads(text)


# ---------------------------------------------------------------------------
# Основная логика
# ---------------------------------------------------------------------------

def main() -> None:
    load_env()

    parser = argparse.ArgumentParser(
        description="Извлечение фото товаров из PDF-каталога через Claude Vision"
    )
    parser.add_argument(
        "--pdf",
        default=str(DEFAULT_PDF),
        help=f"Путь к PDF-файлу (по умолчанию: {DEFAULT_PDF})",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_PHOTOS_DIR),
        help=f"Папка для сохранения фото (по умолчанию: {DEFAULT_PHOTOS_DIR})",
    )
    parser.add_argument(
        "--start-page",
        type=int,
        default=1,
        metavar="N",
        help="Начать с N-й страницы (1-based, по умолчанию: 1) — для возобновления",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Без сохранения файлов — только анализ через Claude API",
    )
    args = parser.parse_args()

    # --- Проверить API-ключ ---
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        log.error(
            "ANTHROPIC_API_KEY не задан.\n"
            "Добавьте в .env (корень проекта): ANTHROPIC_API_KEY=sk-ant-..."
        )
        sys.exit(1)

    # --- Проверить PDF ---
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        log.error("PDF не найден: %s", pdf_path)
        sys.exit(1)

    # --- Создать папку для фото ---
    output_dir = Path(args.output_dir)
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        log.info("Папка для фото: %s", output_dir)

    # --- Импорт зависимостей ---
    try:
        import fitz  # PyMuPDF
    except ImportError:
        log.error("PyMuPDF не установлен. Выполните: pip install PyMuPDF")
        sys.exit(1)

    try:
        import anthropic
    except ImportError:
        log.error("anthropic не установлен. Выполните: pip install anthropic")
        sys.exit(1)

    try:
        from transliterate import translit  # noqa: F401
    except ImportError:
        log.warning(
            "Библиотека transliterate не установлена. "
            "Имена файлов будут без транслитерации. "
            "Установите: pip install transliterate"
        )

    client = anthropic.Anthropic(api_key=api_key)

    # --- Загрузить существующий photo_map (для возобновления с --start-page) ---
    existing_map: list[dict] = []
    if args.start_page > 1 and PHOTO_MAP_PATH.exists():
        with open(PHOTO_MAP_PATH, "r", encoding="utf-8") as f:
            existing_map = json.load(f)
        log.info(
            "Загружен существующий photo_map (%d записей) — добавляю с страницы %d",
            len(existing_map),
            args.start_page,
        )

    # --- Открыть PDF ---
    log.info("Открываю PDF: %s", pdf_path)
    doc = fitz.open(str(pdf_path))
    total_pages = doc.page_count
    log.info("Страниц в PDF: %d", total_pages)

    photo_map: list[dict] = list(existing_map)
    total_photos = 0
    pages_with_products = 0
    slug_counter: dict[str, int] = {}

    # Заполнить счётчик slug из уже сохранённых записей (при возобновлении)
    for entry in existing_map:
        fn = entry.get("file_name") or ""
        if fn:
            slug = re.sub(r"-\d+\.jpg$", ".jpg", fn)
            slug = slug.replace(".jpg", "")
            slug_counter[slug] = slug_counter.get(slug, 0) + 1

    start_idx = max(0, args.start_page - 1)

    for page_num in range(start_idx, total_pages):
        page = doc[page_num]
        page_display = page_num + 1

        # --- Рендер страницы ---
        try:
            page_png = render_page_png(page)
        except Exception as e:
            log.error("Ошибка рендера страницы %d: %s", page_display, e)
            continue

        # --- Запрос к Claude ---
        try:
            products = ask_claude(client, page_png)
        except json.JSONDecodeError as e:
            log.error("Ошибка парсинга JSON от Claude (стр. %d): %s", page_display, e)
            time.sleep(0.5)
            continue
        except Exception as e:
            log.error("Ошибка API Claude (стр. %d): %s", page_display, e)
            time.sleep(0.5)
            continue

        if not products:
            log.info("Страница %d/%d — пропускаю (нет товаров)", page_display, total_pages)
            time.sleep(0.5)
            continue

        log.info(
            "Страница %d/%d — найдено %d товаров",
            page_display,
            total_pages,
            len(products),
        )
        pages_with_products += 1

        # --- Извлечь и отсортировать изображения страницы ---
        page_images = get_page_images_sorted(page)

        # --- Сопоставить товары с изображениями ---
        for item in products:
            name = (item.get("name") or "").strip()
            description = (item.get("description") or "").strip()
            image_index = item.get("image_index")

            if not name:
                continue

            # Найти изображение по image_index (1-based)
            img_info = None
            if isinstance(image_index, int) and 1 <= image_index <= len(page_images):
                img_info = page_images[image_index - 1]

            # Сгенерировать уникальное имя файла
            slug = slugify(name)
            count = slug_counter.get(slug, 0)
            slug_counter[slug] = count + 1
            file_name = f"{slug}.jpg" if count == 0 else f"{slug}-{count}.jpg"

            # Сохранить изображение
            saved = False
            if img_info is not None and not args.dry_run:
                out_path = output_dir / file_name
                saved = save_image(doc, img_info["xref"], out_path)
                if saved:
                    total_photos += 1

            # Запись в photo_map
            photo_map.append({
                "original_name": name,
                "file_name": file_name if img_info is not None else None,
                "description": description,
                "source_pdf": pdf_path.name,
                "page": page_display,
            })

            # Лог строки
            if img_info is None:
                status = "нет фото"
            elif args.dry_run:
                status = f"dry-run → {file_name}"
            elif saved:
                status = f"✓ {file_name}"
            else:
                status = f"ошибка сохранения → {file_name}"
            log.info("    %s [%s]", name, status)

        # --- Сохранить промежуточный photo_map после каждой страницы ---
        if not args.dry_run:
            with open(PHOTO_MAP_PATH, "w", encoding="utf-8") as f:
                json.dump(photo_map, f, ensure_ascii=False, indent=2)

        time.sleep(0.5)

    doc.close()

    # --- Финальное сохранение photo_map ---
    if not args.dry_run:
        with open(PHOTO_MAP_PATH, "w", encoding="utf-8") as f:
            json.dump(photo_map, f, ensure_ascii=False, indent=2)
        log.info("photo_map.json сохранён: %s", PHOTO_MAP_PATH)
    else:
        log.info("--dry-run: photo_map.json не сохранён")
        if photo_map:
            print("\nПример данных (первые 10 записей):")
            for entry in photo_map[:10]:
                desc = (entry["description"] or "—")[:60]
                fn = entry["file_name"] or "—"
                print(f"  {entry['original_name'][:40]} → {fn} | {desc}")

    print(f"\nГотово! Извлечено {total_photos} фото из {pages_with_products} страниц")
    print(f"Всего товаров в photo_map: {len(photo_map)}")
    if not args.dry_run:
        print(f"Файл карты: {PHOTO_MAP_PATH}")
        print(f"Папка фото: {output_dir}")


if __name__ == "__main__":
    main()
