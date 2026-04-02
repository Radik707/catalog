"""
auto_match_photos.py — Автоматическое сопоставление фото с товарами
Читает photo_map.json + Excel прайсы → генерирует photo_overrides.json
"""

import re
import json
import glob
import sys
import openpyxl
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_PRICE_DIR = r"C:\price"

# ── Шумовые слова — удаляем из обоих названий ────────────────────────────
NOISE = {
    "акконд", "вес", "конфеты", "конфет", "конфету", "фас", "кор",
    "батончик", "десерт", "упк", "уп", "печ", "наб", "набор",
    "вкус", "вкусом", "вкуса", "вкусе",  # "со вкусом X" → X остаётся
    "в", "с", "со", "и", "по", "на", "от", "до", "для", "при", "над",
    "под", "за", "ко", "как", "или", "это",
}

# ── Различающие слова: если есть в Excel, но нет в PDF → отклонить ────────
DISTINGUISHING = {
    # Вкусы и начинки
    "делямусс", "делямус",
    "фундук",
    "арахис", "арахисовый", "арахисовой", "арахисовая",
    "миндал", "миндаль",
    "орехов", "орех",
    "шоколадн", "шоколад",
    "молочн", "молоко",
    "карамел", "карамель",
    "вишн", "вишня",
    "сливк", "сливоч", "сливки",
    "кокос",
    "клубн", "клубника",
    "лимон",
    "малина",
    "коньяк",
    "ром",
    "апельс", "апельсин",
    "ваниль",
    "пломбир",
    "нуга",
    "тирам", "тирамису",
    "изюм",
    "злак",
    "цукат",
    "финик",
    "инжир",
    "курага",
    "черносл", "чернослив",
    "брауни",
    "кофейн",
    "топл",
    "марш", "маршмеллоу",
    "сгущ",
    # Форма/вариант продукта
    "мини",
    "плюс",
    "лайт",
    "джуниор",
    "делямусс",
    "темн", "тёмный", "темный",
    "горький",
    "глазирован",  # «Ломтишка» ≠ «Ломтишка глазированный»
    "неглазирован",
    "двухслойн",
    "трёхслойн",
    "tоффи", "тоффи",
    "pralineo",
    "премиум", "преми",
    "печень",   # «с печеньем» = вариант продукта
    "начинк",   # «с начинкой» = вариант
    "сэндвич",
    "stick", "стик",
}

# ── Нормализация падежей → canonical token ───────────────────────────────
STEM_MAP = {
    # шоколад
    "шоколадной": "шоколадн", "шоколадная": "шоколадн", "шоколадным": "шоколадн",
    "шоколадного": "шоколадн", "шоколадные": "шоколадн", "шоколадно": "шоколадн",
    "шоколад": "шоколадн",
    # глазурь
    "глазури": "глазур", "глазурь": "глазур",
    "глазированный": "глазирован", "глазированные": "глазирован",
    "глазированным": "глазирован", "глазированного": "глазирован",
    "глазированная": "глазирован",
    # карамель
    "карамелизованное": "карамел", "карамелизированное": "карамел",
    "карамели": "карамел", "карамелью": "карамел", "карамель": "карамел",
    "карамельный": "карамел", "карамелизованного": "карамел",
    # арахис
    "арахисом": "арахис", "арахисовой": "арахис", "арахисовый": "арахис",
    "арахисовая": "арахис", "арахисовую": "арахис",
    # вишня
    "вишнёвый": "вишн", "вишневый": "вишн", "вишнёвой": "вишн",
    "вишневой": "вишн", "вишни": "вишн", "вишней": "вишн", "вишня": "вишн",
    # молоко
    "молочный": "молочн", "молочной": "молочн", "молочным": "молочн",
    "молочного": "молочн", "молока": "молочн", "молоко": "молочн", "молоком": "молочн",
    # фундук
    "фундуком": "фундук",
    # миндаль
    "миндалём": "миндал", "миндалем": "миндал", "миндаля": "миндал", "миндаль": "миндал",
    # орех
    "ореховая": "орехов", "ореховой": "орехов", "ореховый": "орехов",
    "ореховую": "орехов",
    # сливки
    "сливочного": "сливоч", "сливочный": "сливоч", "сливочной": "сливоч",
    "сливочным": "сливоч", "сливок": "сливк", "сливкам": "сливк",
    "сливками": "сливк", "сливки": "сливк",
    # птица/дивная
    "птица": "птиц", "птицы": "птиц", "птицу": "птиц", "птице": "птиц",
    "дивная": "дивн", "дивной": "дивн", "дивную": "дивн",
    # печенье → distinguishing
    "печеньем": "печень", "печенья": "печень", "печенье": "печень",
    # начинка → distinguishing
    "начинкой": "начинк", "начинку": "начинк", "начинки": "начинк", "начинка": "начинк",
    # кокос
    "кокоса": "кокос", "кокосовый": "кокос", "кокосовой": "кокос", "кокосом": "кокос",
    # лимон
    "лимона": "лимон",
    # сливочный ликёр
    "ликёра": "ликёр", "ликера": "ликёр",
    # топлёное молоко
    "топлёного": "топл", "топленого": "топл", "топлёный": "топл", "топленый": "топл",
    # клубника
    "клубники": "клубн", "клубникой": "клубн", "клубника": "клубн",
    "клубничный": "клубн", "клубничным": "клубн",
    # нуга
    "нуги": "нуга", "нугой": "нуга",
    # злаки
    "злаков": "злак", "злаки": "злак",
    # цукаты
    "цукатами": "цукат", "цукаты": "цукат",
    # финики
    "финики": "финик", "фиников": "финик", "финиками": "финик",
    # тирамису
    "тирамису": "тирам",
    # маршмеллоу
    "маршмеллоу": "марш",
    # кофейный
    "кофейного": "кофейн", "кофейный": "кофейн", "кофейной": "кофейн",
    # тёмный
    "тёмный": "темн", "темный": "темн",
}

# ── Раскрытие аббревиатур в Excel-названиях ──────────────────────────────
ABBREVS = [
    (r"\bшок\b",  "шоколадн"),
    (r"\bмол\b",  "молочн"),
    (r"\bглаз\b", "глазирован"),
    (r"\bкарам\b","карамел"),
]


def normalize(text: str) -> frozenset:
    """Нормализовать название → frozenset значимых токенов."""
    # Убрать кавычки и скобки
    text = re.sub(r"[«»\"\"\'()\[\]{}]", " ", text)
    # Убрать вес/количество: 500г, 2кг, 34/20, ф.90, *6, 30г/25
    text = re.sub(r"\d+\s*(?:г|кг|мл|шт|мм)\b", " ", text, flags=re.I)
    text = re.sub(r"ф\.\s*\d+", " ", text)
    text = re.sub(r"\*\s*\d+", " ", text)
    text = re.sub(r"\d+\s*/\s*\d+", " ", text)
    text = re.sub(r"\b\d+\b", " ", text)
    text = text.lower()
    # Раскрыть аббревиатуры
    for pattern, repl in ABBREVS:
        text = re.sub(pattern, repl, text)
    # Токенизация
    tokens = re.findall(r"[а-яёa-z]+", text)
    # Удалить шум и короткие токены
    tokens = [t for t in tokens if t not in NOISE and len(t) >= 3]
    # Нормализация падежей
    tokens = [STEM_MAP.get(t, t) for t in tokens]
    return frozenset(tokens)


def is_match(pdf_tokens: frozenset, excel_tokens: frozenset) -> bool:
    """True если pdf_tokens ⊆ excel_tokens И в Excel нет различающих лишних токенов.

    Дополнительная защита: если PDF содержит ≤ 2 токена (например, просто {трюфель}
    или {шоколадн, горький}), то любой лишний содержательный токен в Excel (≥ 3 символов)
    считается различающим — иначе «Трюфель» ошибочно совпадёт с «Шоконатка трюфель».
    """
    if not pdf_tokens:
        return False
    if not pdf_tokens.issubset(excel_tokens):
        return False
    extra = excel_tokens - pdf_tokens
    for token in extra:
        if token in DISTINGUISHING:
            return False
    # Строгий режим для 1-токенных запросов:
    # «Трюфель» не должен совпасть с «Шоконатка трюфель»
    if len(pdf_tokens) == 1 and any(len(t) >= 3 for t in extra):
        return False
    return True


def load_photos() -> list[dict]:
    """Загрузить photo_map.json. Дубли по original_name → оставляем без суффикса -N."""
    path = SCRIPT_DIR / "photo_map.json"
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    # Убрать записи без file_name
    raw = [e for e in raw if e.get("file_name")]

    # При дублях по original_name: предпочесть файл без суффикса -1, -2, ...
    best: dict[str, dict] = {}
    for entry in raw:
        key = (entry.get("original_name") or "").strip().lower()
        fn = entry["file_name"]
        if key not in best:
            best[key] = entry
        else:
            # Выбираем «более чистое» имя (без -1, -2 в суффиксе перед расширением)
            current_fn = best[key]["file_name"]
            # -1.jpg > без суффикса → предпочесть без -1
            if re.search(r"-\d+\.", current_fn) and not re.search(r"-\d+\.", fn):
                best[key] = entry

    return list(best.values())


def load_excel_products(price_dir: str) -> list[str]:
    """Загрузить уникальные названия товаров из всех Excel-прайсов."""
    seen: set[str] = set()
    products: list[str] = []

    for filepath in sorted(glob.glob(str(Path(price_dir) / "*.xlsx"))):
        wb = openpyxl.load_workbook(filepath, data_only=True, read_only=True)
        ws = wb.active
        for row in ws.iter_rows(min_row=1, values_only=True):
            a = row[0] if row else None
            b = row[1] if len(row) > 1 else None
            if a and b and str(b).strip().lower() != "цена":
                name = str(a).strip()
                if name and name not in seen:
                    seen.add(name)
                    products.append(name)
        wb.close()

    return products


def main():
    # ── Загрузка данных ────────────────────────────────────────────────────
    photos = load_photos()
    print(f"Фото в photo_map: {len(photos)}")

    excel_products = load_excel_products(DEFAULT_PRICE_DIR)
    print(f"Товаров в прайсах: {len(excel_products)}")

    # ── Предвычислить токены Excel ─────────────────────────────────────────
    excel_norm: list[tuple[str, frozenset]] = [
        (name, normalize(name)) for name in excel_products
    ]

    # ── Сопоставление ─────────────────────────────────────────────────────
    overrides: dict[str, str] = {}        # {excel_name: file_name}
    matched_photos: set[str] = set()      # file_name фото, нашедших пару
    unmatched_photos: list[dict] = []

    for entry in photos:
        file_name   = entry["file_name"]
        original    = (entry.get("original_name") or "").strip()
        pdf_tokens  = normalize(original)

        photo_matches: list[str] = []
        for excel_name, ex_tokens in excel_norm:
            if is_match(pdf_tokens, ex_tokens):
                photo_matches.append(excel_name)

        if photo_matches:
            matched_photos.add(file_name)
            for excel_name in photo_matches:
                # Если товар уже привязан — не перезаписываем
                if excel_name not in overrides:
                    overrides[excel_name] = file_name
        else:
            unmatched_photos.append(entry)

    # ── Сохранить photo_overrides.json ────────────────────────────────────
    out_path = SCRIPT_DIR / "photo_overrides.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(overrides, f, ensure_ascii=False, indent=2)

    # ── Статистика ────────────────────────────────────────────────────────
    products_with_photo = len(overrides)
    print(f"\n{'─'*60}")
    print(f"✓  Фото привязано:              {len(matched_photos)} из {len(photos)}")
    print(f"✓  Товаров получили фото:        {products_with_photo}")
    print(f"✗  Фото без пары:               {len(unmatched_photos)}")
    print(f"   Файл: {out_path}")
    print(f"{'─'*60}")

    if unmatched_photos:
        print("\nФото без пары (привяжите вручную через make_photo_sheet.py):")
        for e in unmatched_photos:
            print(f"  {e['file_name']:50s}  ← {e['original_name']}")

    # ── Показать примеры совпадений ───────────────────────────────────────
    print("\nПримеры привязок (первые 20):")
    for i, (excel_name, file_name) in enumerate(list(overrides.items())[:20]):
        print(f"  {file_name:45s} → {excel_name}")


if __name__ == "__main__":
    main()
