"""
test_structure_map.py — Pytest-тесты контракта structure_map.json.

Покрывает:
- Парсинг JSON и наличие ровно 5 разделов
- Полное покрытие всех 117 категорий из category_map.json (D-12)
- Отсутствие дублей категорий между подгруппами
- Расформирование группы «Стоевъ и Сэнсой» (REGRP-01)
- Разделение «Конфеты» и «Печенье и вафли», Сладонеж в «Печенье и вафли» (REGRP-02)
- «Мистраль Крупы варпак» в «Крупы и бакалея» (REGRP-03)
- Порядок разделов (STRUCT-02)
- Кластер «Коробочных конфет» последними в «Конфеты» (STRUCT-05 / D-06)
- «Энергетики» — последняя подгруппа в «Напитки» (STRUCT-03 / D-05)
"""

import json
from pathlib import Path
import pytest

# Папка scripts/ — рядом с этим тест-файлом
SCRIPTS_DIR = Path(__file__).resolve().parent

# 7 категорий бывшей группы «Коробочные конфеты» (STRUCT-05 / D-06)
BOXED_CANDIES = {
    "Коробочные",
    "Подарки",
    "Торты",
    "Набор конфет ЛЮСИ",
    "Набор конфет МВН",
    "Набор конфет Сонуар",
    "Фас. кор. конфеты",
}


# ── Фикстуры ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def structure_map() -> dict:
    """Загрузить structure_map.json один раз для всего модуля."""
    path = SCRIPTS_DIR / "structure_map.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def category_map() -> dict:
    """Загрузить category_map.json один раз для всего модуля."""
    path = SCRIPTS_DIR / "category_map.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def all_covered_categories(structure_map) -> set:
    """Плоское множество всех категорий из structure_map."""
    return {
        cat
        for subgroups in structure_map.values()
        for cats in subgroups.values()
        for cat in cats
    }


# ── Тесты ───────────────────────────────────────────────────────────────────

def test_файл_парсится(structure_map):
    """structure_map.json загружается как dict и содержит ровно 5 разделов."""
    assert isinstance(structure_map, dict), "structure_map.json должен быть объектом JSON"
    assert len(structure_map) == 5, (
        f"Ожидали 5 разделов верхнего уровня, получили {len(structure_map)}: "
        f"{list(structure_map.keys())}"
    )


def test_полное_покрытие(structure_map, category_map, all_covered_categories):
    """Множество категорий structure_map == множество ключей category_map.json (D-12).

    Если тест падает — выводит разницу в обе стороны для диагностики.
    """
    expected = set(category_map.keys())
    missing = expected - all_covered_categories   # есть в category_map, нет в structure_map
    extra = all_covered_categories - expected      # есть в structure_map, нет в category_map

    errors = []
    if missing:
        errors.append(f"ОТСУТСТВУЮТ в structure_map ({len(missing)}):\n  " + "\n  ".join(sorted(missing)))
    if extra:
        errors.append(f"ЛИШНИЕ в structure_map ({len(extra)}):\n  " + "\n  ".join(sorted(extra)))

    assert not errors, "\n\n".join(errors)


def test_нет_дублей(structure_map):
    """Ни одна категория не встречается в двух подгруппах одновременно."""
    flat = [
        cat
        for subgroups in structure_map.values()
        for cats in subgroups.values()
        for cat in cats
    ]
    duplicates = {cat for cat in flat if flat.count(cat) > 1}
    assert not duplicates, (
        f"Категории дублируются в нескольких подгруппах: {sorted(duplicates)}"
    )


def test_стоевъ_сэнсой_расформирована(structure_map):
    """Строки «Стоевъ и Сэнсой» нет среди разделов и подгрупп (REGRP-01)."""
    all_group_names = list(structure_map.keys())
    for subgroups in structure_map.values():
        all_group_names.extend(subgroups.keys())
    found = [k for k in all_group_names if "Стоевъ и Сэнсой" in k]
    assert not found, (
        f"Группа «Стоевъ и Сэнсой» должна быть расформирована, но найдена в: {found}"
    )


def test_конфеты_и_печенье_разделены(structure_map):
    """«Конфеты» и «Печенье и вафли» — разные подгруппы; «Сладонеж» только в «Печенье и вафли» (REGRP-02)."""
    sweet_subgroups = structure_map.get("Сладкое", {})
    assert "Конфеты" in sweet_subgroups, "Подгруппа «Конфеты» должна присутствовать в разделе «Сладкое»"
    assert "Печенье и вафли" in sweet_subgroups, "Подгруппа «Печенье и вафли» должна присутствовать в разделе «Сладкое»"

    confety = sweet_subgroups.get("Конфеты", [])
    pechenie = sweet_subgroups.get("Печенье и вафли", [])

    assert "Сладонеж" in pechenie, "«Сладонеж» должен быть в подгруппе «Печенье и вафли»"
    assert "Сладонеж" not in confety, "«Сладонеж» не должен быть в подгруппе «Конфеты»"


def test_варпак_мистраль_в_крупах(structure_map):
    """«Мистраль Крупы варпак» находится в подгруппе «Крупы и бакалея» (REGRP-03 / D-11)."""
    krupy_section = structure_map.get("Крупы, лапша, бакалея", {})
    krupy_subgroup = krupy_section.get("Крупы и бакалея", [])
    assert "Мистраль Крупы варпак" in krupy_subgroup, (
        "«Мистраль Крупы варпак» должен быть в подгруппе «Крупы и бакалея» раздела «Крупы, лапша, бакалея»"
    )


def test_порядок_разделов(structure_map):
    """Порядок разделов верхнего уровня строго фиксирован (STRUCT-02)."""
    expected = [
        "Сладкое",
        "Напитки",
        "Крупы, лапша, бакалея",
        "Соусы и консервация",
        "Снэки и прикассовое",
    ]
    actual = list(structure_map.keys())
    assert actual == expected, (
        f"Порядок разделов не совпадает:\n  Ожидали:  {expected}\n  Получили: {actual}"
    )


def test_коробочные_кучей(structure_map):
    """Последние 7 элементов массива подгруппы «Конфеты» — ровно набор «Коробочных конфет» (STRUCT-05 / D-06)."""
    confety = structure_map.get("Сладкое", {}).get("Конфеты", [])
    assert len(confety) >= 7, (
        f"Подгруппа «Конфеты» должна содержать минимум 7 категорий, содержит {len(confety)}"
    )
    last_7 = set(confety[-7:])
    assert last_7 == BOXED_CANDIES, (
        f"Последние 7 категорий в «Конфеты» должны быть «Коробочными конфетами».\n"
        f"  Ожидали:  {sorted(BOXED_CANDIES)}\n"
        f"  Получили: {sorted(last_7)}\n"
        f"  Разница:  {sorted(last_7 ^ BOXED_CANDIES)}"
    )


def test_энергетики_последние(structure_map):
    """«Энергетики» — последний ключ (подгруппа) в разделе «Напитки» (STRUCT-03 / D-05)."""
    napitki = structure_map.get("Напитки", {})
    subgroups = list(napitki.keys())
    assert subgroups, "Раздел «Напитки» пуст"
    assert subgroups[-1] == "Энергетики", (
        f"Подгруппа «Энергетики» должна быть последней в «Напитки», "
        f"но последняя: «{subgroups[-1]}» (все: {subgroups})"
    )
