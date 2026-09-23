# -*- coding: utf-8 -*-
"""
photo_rebind.py — автоматический перенос фото при переименовании товара в прайсе.

ЗАЧЕМ ЭТОТ МОДУЛЬ СУЩЕСТВУЕТ
----------------------------
Привязка фото (photo_overrides.json) держится на НАЗВАНИИ товара. Поставщик
переставляет слова в названиях при каждой выгрузке 1С:

    было : Стоевъ Кетчуп Острый с/бут 310г/12
    стало: Стоевъ Кетчуп 310г/12 стекло Острый

Для человека это один товар, для подстрочного матчинга — два разных. Связь
рвётся, и фото пропадает с витрины пачками по 40-60 штук. За 2026 год так
ломалось четырежды: «Добрый» 06-22, «Аква Драйв» 07-14, «Кофе Лебо» 09-17,
«Стоевъ» 09-23. Каждый раз это чинилось руками.

ИДЕЯ РЕШЕНИЯ
------------
Опознавать товар не по строке целиком, а по ОТПЕЧАТКУ — тому, что поставщик
не меняет: набор значимых слов + числа (граммовка и фасовка). Перестановка
слов, замена «с/б» на «стекло» и потеря «шт» отпечаток не меняют.

Артикула в прайсе нет (проверено: колонки — только название, цена, остатки),
поэтому отпечаток — единственный доступный устойчивый идентификатор.

ГЛАВНЫЙ ПРИНЦИП: ЛУЧШЕ ПУСТО, ЧЕМ ЧУЖОЕ
----------------------------------------
Это B2B-каталог: по фото делают заказ. Неверная картинка хуже её отсутствия —
агент закажет не тот товар. Поэтому автоперенос срабатывает только при
совпадении «без вариантов», а всё сомнительное уходит в отчёт человеку.

Защиты, каждая из которых выросла из реальной ошибки при ручном разборе:
  * числа должны совпасть точно — иначе «Суп рассольник 65г» получил бы фото
    «Супа горохового 60г»;
  * вес слова по редкости (IDF) — иначе «Эксклюзив» цепляется к «Экстра»,
    потому что общие слова «кофе лебо сублимированный» перевешивают;
  * отрыв от второго кандидата — если два старых товара похожи одинаково,
    выбирать наугад нельзя;
  * одно фото не может достаться двум новым товарам — при ручном разборе все
    четыре таких случая оказались ошибкой (второй товар был новинкой).

Модуль ЧИСТЫЙ: без сети, без файлов, без глобального состояния — что удобно
для тестов (scripts/test_photo_rebind.py).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

# ── Нормализация названий ────────────────────────────────────────────────────

# Сокращения прайса → развёрнутая форма. Нужны, чтобы «ирл. сливки» и
# «Ирландские сливки» встретились, а «с/б» и «стекло» считались одним словом.
# Ключ — то, что ищем (regex по границам), значение — во что приводим.
_EXPAND: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bирл\b"), "ирландские"),
    (re.compile(r"\bгорох\b"), "гороховый"),
    (re.compile(r"\bовощ\b"), "овощной"),
    (re.compile(r"\bраств\b"), "растворимый"),
    (re.compile(r"\bсублим\b"), "сублимированный"),
    (re.compile(r"\bклассич\b"), "классический"),
    (re.compile(r"\bфигур\b"), "фигурные"),
    (re.compile(r"\bвес\b"), "весовой"),
    (re.compile(r"\bфас\b"), "фасованный"),
    (re.compile(r"\bваф\b"), "вафли"),
    (re.compile(r"\bпеч\b"), "печенье"),
    (re.compile(r"\bнап\b"), "напиток"),
    (re.compile(r"\bконс\b"), "консерва"),
    (re.compile(r"\bприправ\w*\b"), "приправа"),
]

# Слова про УПАКОВКУ и единицы измерения. Поставщик меняет их свободно
# («с/б» → «стекло», «п/бут» → «пластик»), на то, ЧТО это за товар, они не
# влияют — поэтому из отпечатка выбрасываем.
_PACKAGING = {
    "сб", "стб", "стекло", "стеклянная", "му", "мягкая", "упаковка", "уп",
    "пбут", "пластик", "бут", "бутылка", "дпак", "дп", "дойпак", "жб", "банка",
    "зип", "лок", "ziplock", "zip", "пакет", "пак", "стакан", "стак", "брикет",
    "коробка", "кор", "шт", "штук", "г", "гр", "грамм", "кг", "мл", "л", "литр",
    "для", "из", "в", "с", "и", "на", "по", "мес", "евро", "ключ", "вс",
}

_PUNCT = re.compile(r"[«»\"()\[\],.+*/\\\-–—:;!?#№]")
_NUM = re.compile(r"\d+(?:[.,]\d+)?")
_SPLIT_DIGIT_LETTER = re.compile(r"(\d)([а-яёa-z])")
_SPLIT_LETTER_DIGIT = re.compile(r"([а-яёa-z])(\d)")


# Длина основы слова. Поставщик свободно меняет форму слова: «Икра из кабачков»
# → «Икра Кабачковая», «Сок Томатный» → «Сок Томатные». Сравнивать словоформы
# бесполезно, поэтому от каждого слова берём основу. Пять букв — компромисс,
# проверенный на реальных названиях: «кабачков»/«кабачковая» → «кабач» (одно),
# «экстра»/«эксклюзив» → «экстр»/«экскл» (разные), «перечный»/«перцовый» →
# «переч»/«перцо» (разные — это соседние соусы «Стоевъ», путать их нельзя).
_STEM_LEN = 5


def stem(word: str) -> str:
    """Основа слова — чтобы разные словоформы считались одним словом."""
    return word[:_STEM_LEN] if len(word) > _STEM_LEN else word


def normalize(name: str) -> str:
    """Привести название к единому виду: нижний регистр, без пунктуации,
    сокращения развёрнуты, число отделено от приклеенной единицы («100г» → «100 г»).
    """
    text = (name or "").lower().replace("ё", "е")
    text = _PUNCT.sub(" ", text)
    for pattern, replacement in _EXPAND:
        text = pattern.sub(replacement, text)
    text = _SPLIT_DIGIT_LETTER.sub(r"\1 \2", text)
    text = _SPLIT_LETTER_DIGIT.sub(r"\1 \2", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass(frozen=True)
class Fingerprint:
    """Отпечаток товара: что это за товар и в какой фасовке.

    words   — значимые слова (бренд, вид, вкус) без упаковочного мусора;
    numbers — числа из названия в порядке возрастания (граммовка, фасовка).
              Именно кортеж, а не множество: «400/20» и «20/400» — разные вещи,
              но порядок слов в названии произволен, поэтому сортируем.
    """

    words: frozenset[str] = field(default_factory=frozenset)
    numbers: tuple[str, ...] = ()

    def is_empty(self) -> bool:
        return not self.words


def fingerprint(name: str) -> Fingerprint:
    """Построить отпечаток товара по его названию."""
    text = normalize(name)
    numbers = tuple(sorted(n.replace(",", ".") for n in _NUM.findall(text)))
    words = {
        stem(token)
        for token in text.split(" ")
        if len(token) > 1 and not token.isdigit() and token not in _PACKAGING
    }
    return Fingerprint(frozenset(words), numbers)


# ── Сопоставление ────────────────────────────────────────────────────────────

# Порог схожести для автопринятия. Подобран по реальным парам из истории:
# верные переименования дают 0.55+, ошибочные кандидаты («Эксклюзив» против
# «Экстра») остаются ниже.
AUTO_SCORE = 0.55
# Насколько лучший кандидат обязан оторваться от второго. Без этого при двух
# одинаково похожих старых товарах выбор был бы случайным.
AUTO_MARGIN = 0.08


def _idf(candidates: list[str]) -> dict[str, float]:
    """Вес слов по редкости. «Кофе» встречается у сотни товаров и почти ничего
    не говорит, «рассольник» — у одного и решает всё. Без этого веса общая
    часть названия перевешивает различающую, и сопоставление ошибается.
    """
    total = len(candidates) or 1
    document_freq: dict[str, int] = {}
    for name in candidates:
        for word in fingerprint(name).words:
            document_freq[word] = document_freq.get(word, 0) + 1
    return {
        word: math.log((total + 1) / (freq + 1)) + 1.0
        for word, freq in document_freq.items()
    }


def similarity(left: Fingerprint, right: Fingerprint, weights: dict[str, float]) -> float:
    """Взвешенная мера Жаккара по словам: доля общего веса от общего объёма."""
    if left.is_empty() or right.is_empty():
        return 0.0
    intersection = union = 0.0
    for word in left.words | right.words:
        weight = weights.get(word, 1.0)
        union += weight
        if word in left.words and word in right.words:
            intersection += weight
    return intersection / union if union else 0.0


def differing_words(left: Fingerprint, right: Fingerprint) -> tuple[str, str] | None:
    """Проверить, не разные ли это ВАРИАНТЫ товара.

    Самый надёжный признак «это другой товар», найденный на реальных поломках.
    Смысл простой: при переименовании поставщик слова ПЕРЕСТАВЛЯЕТ, иногда
    добавляет («Дачный сезон» перед «Суп мясной») или убирает («с солью»).
    Тогда одно множество слов — подмножество другого, различие ОДНОСТОРОННЕЕ.

    А вот когда у каждого названия есть своё уникальное содержательное слово —
    это разные варианты одного продукта, и путать их нельзя:

        Эксклюзив ←→ Экстра        (кофе Лебо)
        Цыганский ←→ Острый        (кетчуп «Стоевъ»)
        Говядина  ←→ Грибы         (каша «Супершеф»)
        Рассольник ←→ Гороховый    (суп «Дачный сезон»)
        Овсяные   ←→ Кукурузные    (хлопья «Мистраль»)

    Каждая из этих пар давала ложное совпадение при подборе по похожести —
    общая часть названия слишком велика и перевешивает различающую.

    Возвращает пару различающих слов (для объяснения в отчёте) либо None,
    если различие одностороннее и переносить фото безопасно.
    """
    only_left = left.words - right.words
    only_right = right.words - left.words
    if only_left and only_right:
        return sorted(only_left)[0], sorted(only_right)[0]
    return None


@dataclass
class Suggestion:
    """Предложение перенести фото со старого товара на новый."""

    new_name: str
    old_name: str
    url: str
    score: float
    numbers_match: bool
    margin: float
    auto: bool           # можно применить без человека
    reason: str          # почему решили именно так — попадёт в отчёт


def suggest(
    new_names: list[str],
    old_photos: dict[str, str],
    *,
    auto_score: float = AUTO_SCORE,
    auto_margin: float = AUTO_MARGIN,
) -> list[Suggestion]:
    """Подобрать старое фото для каждого нового названия.

    new_names  — товары ТЕКУЩЕГО прайса, у которых фото не нашлось;
    old_photos — {название из прошлой версии каталога: URL фото}.

    Возвращает предложения, отсортированные: сначала автоприменимые.
    Ничего не пишет и не скачивает — только считает.
    """
    if not new_names or not old_photos:
        return []

    old_names = list(old_photos.keys())
    weights = _idf(old_names)
    old_prints = [(name, fingerprint(name)) for name in old_names]

    suggestions: list[Suggestion] = []
    for new_name in new_names:
        new_print = fingerprint(new_name)
        if new_print.is_empty():
            continue

        scored = sorted(
            (
                (similarity(new_print, old_print, weights), old_print.numbers == new_print.numbers, old_name)
                for old_name, old_print in old_prints
            ),
            key=lambda item: (item[1], item[0]),
            reverse=True,
        )
        best_score, numbers_match, best_name = scored[0]
        runner_up = next((s for s, _, name in scored[1:] if name != best_name), 0.0)
        margin = best_score - runner_up
        conflict = differing_words(new_print, fingerprint(best_name))

        if not numbers_match:
            reason = "граммовка не совпала"
        elif conflict:
            left, right = conflict
            reason = f"разные варианты товара: «{left}» против «{right}»"
        elif best_score < auto_score:
            reason = f"слабое сходство {best_score:.2f}"
        elif margin < auto_margin:
            reason = f"два похожих кандидата (отрыв {margin:.2f})"
        else:
            reason = f"уверенное совпадение {best_score:.2f}"

        suggestions.append(
            Suggestion(
                new_name=new_name,
                old_name=best_name,
                url=old_photos[best_name],
                score=round(best_score, 2),
                numbers_match=numbers_match,
                margin=round(margin, 2),
                auto=(
                    numbers_match
                    and conflict is None
                    and best_score >= auto_score
                    and margin >= auto_margin
                ),
                reason=reason,
            )
        )

    _drop_contested(suggestions)
    suggestions.sort(key=lambda s: (not s.auto, -s.score))
    return suggestions


def _drop_contested(suggestions: list[Suggestion]) -> None:
    """Снять автоприменение там, где одно фото claim-ят несколько новых товаров.

    При ручном разборе такой конфликт возникал четырежды и КАЖДЫЙ раз означал
    ошибку: правым был один кандидат, а второй товар оказывался новинкой, которой
    просто не с чем сопоставляться. Поэтому оставляем автоприменение только
    явному лидеру, остальных отправляем человеку.
    """
    by_url: dict[str, list[Suggestion]] = {}
    for suggestion in suggestions:
        if suggestion.auto:
            by_url.setdefault(suggestion.url, []).append(suggestion)

    for claimants in by_url.values():
        if len(claimants) < 2:
            continue
        claimants.sort(key=lambda s: s.score, reverse=True)
        for loser in claimants[1:]:
            loser.auto = False
            loser.reason = f"это фото забрал «{claimants[0].new_name}» (счёт выше)"
