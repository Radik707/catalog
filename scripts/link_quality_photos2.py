# -*- coding: utf-8 -*-
"""
link_quality_photos2.py — улучшенное сопоставление и ДОПРИВЯЗКА фото
из папок photos/kids, photos/difrent, photos/Mistral.

Отличие от link_quality_photos.py: надёжная нормализация-для-сопоставления
core(s), которая снимает хвосты фасовки/веса в любом порядке и игнорирует
пробелы/точки/скобки, а также префиксное сопоставление, когда «лишний хвост»
состоит ТОЛЬКО из токенов фасовки. Разные варианты одного продукта
(вкус/животное/цвет) НЕ сливаются.

Браузер/сервер/.env/credentials не трогаются. upload.py НЕ запускается.

Запуск:
    python scripts/link_quality_photos2.py --dry-run   # только показать план
    python scripts/link_quality_photos2.py             # загрузить + записать JSON
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path

from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Папка-источник → имя папки в Cloudinary
FOLDER_MAP = [
    (PROJECT_ROOT / "photos" / "kids", "kids"),
    (PROJECT_ROOT / "photos" / "difrent", "difrent"),
    (PROJECT_ROOT / "photos" / "Mistral", "mistral"),
]

VALID_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MIN_SIDE = 500

PHOTO_URLS_PATH = SCRIPT_DIR / "photo_urls.json"
PHOTO_OVERRIDES_PATH = SCRIPT_DIR / "photo_overrides.json"
PRODUCTS_TMP = PROJECT_ROOT / "_p.json"

# Токен фасовки/веса в конце строки. Применяется ПОВТОРНО, пока что-то снимается.
# Порядок важен: сначала числовые конструкции, потом одиночные числа.
TAIL_PATTERNS = [
    r"\d+\s*(?:гр|кг|мл|мин|шт|г|л)\b\.?",   # 13г, 5кг, 20мл, 1мин, 24шт, 400 г
    r"\d+\s*[xх]\s*\d+",                       # 5x80, 5х80
    r"/\s*\d+",                                # /100, /22
    r"№\s*\d+",                                # №31
    r"\(\s*\d+\s*\)",                          # (6), (12)
    r"\bт/б\b", r"\bупк\b", r"\bшт\b",          # хвостовые служебные
    r"\d+",                                    # одиночное число
]

# Символы, допустимые в «лишнем хвосте» при префиксном сопоставлении
# (только цифры/единицы измерения/разделители — НЕ буквы продукта).
PACK_SUFFIX_RE = re.compile(
    r"^[\s\.\(\)/xх×№\-]*"
    r"(?:\d+\s*(?:гр|кг|мл|мин|шт|г|л)?\b\.?\s*[\(\)/xх×№\d\s\.\-]*)*"
    r"(?:т/б|упк)?[\s\.\(\)/]*$",
    re.IGNORECASE,
)


def load_env() -> None:
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def strip_tail(s: str) -> str:
    """Снять хвостовые токены фасовки/веса повторно, пока что-то снимается."""
    prev = None
    cur = s
    while prev != cur:
        prev = cur
        cur = cur.strip()
        for pat in TAIL_PATTERNS:
            m = re.search(pat + r"\s*$", cur, flags=re.IGNORECASE)
            if m:
                cur = cur[: m.start()].rstrip()
                break  # снова с начала списка
    return cur


def squash(s: str) -> str:
    """Оставить только буквы/цифры/кириллицу (агрессивно: убрать пробелы/точки/скобки)."""
    return re.sub(r"[^0-9a-zA-Zа-яёА-ЯЁ]+", "", s.lower())


def core(s: str) -> str:
    """Ядро для сравнения: нижний регистр, снять хвост фасовки, убрать пунктуацию/пробелы."""
    s = s.lower().strip()
    s = strip_tail(s)
    return squash(s)


def squash_keep_pack(s: str) -> str:
    """Полное «ядро без хвоста-фасовки», но БЕЗ удаления хвоста — для префикс-логики."""
    return squash(s.lower().strip())


def is_pack_only(suffix: str) -> bool:
    """True, если «лишний хвост» (исходный, до squash) состоит только из фасовки/цифр."""
    if not suffix.strip():
        return True
    return bool(PACK_SUFFIX_RE.match(suffix))


def alpha_core(s: str) -> str:
    """Ядро ТОЛЬКО из «словесных» (буквенных) токенов, без любых токенов фасовки.

    Удаляет числа/единицы измерения/упаковку В ЛЮБОМ месте строки, оставляя
    только буквенные слова (вкус/название/вариант — бегемотик, Нежные, Бутылочки).
    Используется как запасной ярус, когда хвост фасовки стоит НЕ в конце
    (например, перед словом-вариантом). Варианты-слова сохраняются → разные
    варианты по-прежнему НЕ сливаются.
    """
    s = s.lower()
    toks = re.findall(r"[a-zа-яё]+|[0-9][0-9a-zа-яё.,]*", s)
    units = {"г", "гр", "кг", "мл", "л", "шт", "мин", "x", "х", "в", "№"}
    keep = []
    for t in toks:
        if re.match(r"[0-9]", t):       # начинается с цифры → токен фасовки/веса
            continue
        if t in units:                   # одиночная единица измерения
            continue
        keep.append(t)
    return "".join(keep)


def match_product(stem: str, products: list[str]) -> list[str]:
    """Вернуть список РАЗНЫХ товаров-кандидатов для имени файла stem."""
    fcore = core(stem)
    if not fcore:
        return []

    matched: list[str] = []
    for pname in products:
        pcore = core(pname)
        if not pcore:
            continue

        # 1) Равенство ядер
        if fcore == pcore:
            matched.append(pname)
            continue

        # 2) Префиксное сопоставление: одно ядро — префикс другого,
        #    и «лишний хвост» (по исходным именам) — только фасовка.
        if pcore.startswith(fcore):
            # У товара длиннее: лишний хвост у товара
            longer, shorter_core = pname, fcore
        elif fcore.startswith(pcore):
            longer, shorter_core = stem, pcore
        else:
            continue

        # Восстановить «лишний хвост» из ИСХОДНОГО имени длинной строки.
        # Берём исходник longer, снимаем известный общий префикс по squash-длине.
        suffix = _extra_suffix(longer, shorter_core)
        if suffix is not None and is_pack_only(suffix):
            matched.append(pname)

    matched = list(dict.fromkeys(matched))
    if matched:
        return matched

    # 3) Запасной ярус: сравнение по буквенным словам (фасовка вырезана везде).
    #    Срабатывает, когда токен упаковки стоит ПЕРЕД словом-вариантом.
    fa = alpha_core(stem)
    if len(fa) >= 6:  # защита от слишком коротких ядер
        alpha_matched = [p for p in products if alpha_core(p) == fa]
        matched = list(dict.fromkeys(alpha_matched))

    return matched


def _extra_suffix(original: str, common_core: str):
    """Вернуть исходный «хвост» original после общего ядра common_core (squash-сравнение).

    Идём по символам original, накапливая squash-форму, пока она не покроет
    common_core. Возвращаем остаток исходной строки. None — если не покрылось.
    """
    acc = ""
    base = original.lower()
    for i, ch in enumerate(base):
        sq = re.sub(r"[^0-9a-zа-яё]+", "", ch)
        acc += sq
        if acc == common_core:
            return original[i + 1:]
        if not common_core.startswith(acc):
            return None
    return None


def is_quality_image(path: Path) -> bool:
    if path.suffix.lower() not in VALID_EXT:
        return False
    try:
        with Image.open(path) as im:
            w, h = im.size
        return min(w, h) >= MIN_SIDE
    except Exception:
        return False


def translit(s: str) -> str:
    """Безопасное латинское имя из кириллицы для public_id Cloudinary."""
    table = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }
    out = []
    for ch in s.lower():
        if ch in table:
            out.append(table[ch])
        elif ch.isalnum():
            out.append(ch)
        elif ch in " -_":
            out.append("_")
        # прочее (скобки, точки, плюсы) выкидываем
    res = re.sub(r"_+", "_", "".join(out)).strip("_")
    return res or "photo"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    products = [p["name"] for p in json.loads(PRODUCTS_TMP.read_text(encoding="utf-8"))]

    photo_urls = json.loads(PHOTO_URLS_PATH.read_text(encoding="utf-8")) if PHOTO_URLS_PATH.exists() else {}
    overrides = json.loads(PHOTO_OVERRIDES_PATH.read_text(encoding="utf-8")) if PHOTO_OVERRIDES_PATH.exists() else {}

    # Товары, у которых УЖЕ есть качественная привязка в этих папках — не трогаем.
    already_linked_products = {
        k for k, v in overrides.items()
        if isinstance(v, str) and any(v.startswith(p + "/") for p in ("kids", "difrent", "mistral", "Mistral"))
    }

    if not args.dry_run:
        import cloudinary
        import cloudinary.uploader
        load_env()
        cloudinary.config(
            cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
            api_key=os.environ["CLOUDINARY_API_KEY"],
            api_secret=os.environ["CLOUDINARY_API_SECRET"],
            secure=True,
        )

    report = {}

    for src_dir, cloud_folder in FOLDER_MAP:
        r = {
            "linked_new": [],
            "skipped_already": [],
            "skipped_quality": [],
            "skipped_numeric": [],
            "skipped_notfound": [],
            "skipped_ambiguous": [],
        }
        if src_dir.exists():
            for fpath in sorted(src_dir.iterdir()):
                if not fpath.is_file():
                    continue
                fname = fpath.name
                stem = fpath.stem

                if not is_quality_image(fpath):
                    r["skipped_quality"].append(fname)
                    continue
                if re.fullmatch(r"\d+", stem.strip()):
                    r["skipped_numeric"].append(fname)
                    continue

                cands = match_product(stem, products)
                if not cands:
                    r["skipped_notfound"].append(fname)
                    continue
                if len(cands) > 1:
                    r["skipped_ambiguous"].append(f"{fname} -> {cands}")
                    continue

                product = cands[0]

                if product in already_linked_products:
                    r["skipped_already"].append(f"{fname} -> {product}")
                    continue

                safe_name = translit(stem) + fpath.suffix.lower()
                public_id = f"{cloud_folder}/{translit(stem)}"
                value = f"{cloud_folder}/{safe_name}"

                if not args.dry_run:
                    res = cloudinary.uploader.upload(
                        str(fpath),
                        public_id=public_id,
                        overwrite=True,
                        resource_type="image",
                        eager=[{"format": "webp", "quality": "auto"}],
                        eager_async=True,
                    )
                    photo_urls[safe_name] = res["secure_url"]
                    overrides[product] = value

                r["linked_new"].append(f"{product}  <=  {fname}  ->  {value}")

        report[cloud_folder] = r

    if not args.dry_run:
        PHOTO_URLS_PATH.write_text(json.dumps(photo_urls, ensure_ascii=False, indent=2), encoding="utf-8")
        PHOTO_OVERRIDES_PATH.write_text(json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8")

    sys.stdout.buffer.write(json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")


if __name__ == "__main__":
    main()
