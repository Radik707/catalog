"""
test_upload_structure.py — Pytest-тесты функций двухуровневой структуры каталога.

Покрывает (план 05-02, задача 1):
- build_category_index: построение обратного индекса из structure_map
- apply_structure_mapping: проставление display_section/display_subgroup/_sort_key
- Fallback «Прочее»/«Прочее» для непокрытых категорий (D-12)
- Порядок колонок заголовка Sheet (header[-2]=="Подгруппа", header[-1]=="Раздел")
- Неизменность колонки «Группа» на позиции 4 (D-04)

Все тесты работают без сети и без реальных .xlsx файлов.
"""

import sys
from pathlib import Path
import pytest

# Добавляем папку scripts в путь поиска модулей
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import upload  # noqa: E402


# ── Минимальная карта структуры для тестов ──────────────────────────────────

SAMPLE_STRUCTURE_MAP = {
    "Сладкое": {
        "Конфеты": [
            "Акконд",
            "Коробочные",
        ],
        "Печенье и вафли": [
            "Сладонеж",
        ],
    },
    "Напитки": {
        "Воды и газировки": [
            "Кока-Кола",
            "Квас",
        ],
        "Энергетики": [
            "Энергетики",
        ],
    },
}


# ── Тесты build_category_index ───────────────────────────────────────────────

class TestBuildCategoryIndex:
    """Тесты построения обратного индекса категорий."""

    def test_index_maps_category_to_section_and_subgroup(self):
        """Индекс содержит корректный раздел и подгруппу для известной категории."""
        index = upload.build_category_index(SAMPLE_STRUCTURE_MAP)
        section, subgroup, sec_idx, sub_idx, cat_idx = index["Акконд"]
        assert section == "Сладкое"
        assert subgroup == "Конфеты"

    def test_index_cat_idx_increments_within_subgroup(self):
        """cat_idx увеличивается в пределах одной подгруппы."""
        index = upload.build_category_index(SAMPLE_STRUCTURE_MAP)
        _, _, _, _, idx_akkond = index["Акконд"]
        _, _, _, _, idx_korobochnye = index["Коробочные"]
        assert idx_akkond == 0
        assert idx_korobochnye == 1

    def test_index_sec_idx_for_napitrki_is_1(self):
        """Раздел «Напитки» идёт вторым (sec_idx=1)."""
        index = upload.build_category_index(SAMPLE_STRUCTURE_MAP)
        _, _, sec_idx, _, _ = index["Кока-Кола"]
        assert sec_idx == 1

    def test_index_covers_all_categories(self):
        """Индекс покрывает все категории из карты."""
        index = upload.build_category_index(SAMPLE_STRUCTURE_MAP)
        all_cats = set()
        for subgroups in SAMPLE_STRUCTURE_MAP.values():
            for cats in subgroups.values():
                all_cats.update(cats)
        assert set(index.keys()) == all_cats

    def test_index_energetiki_sort_key_last_in_napitrki(self):
        """«Энергетики» — последняя подгруппа в «Напитках» (sub_idx=1)."""
        index = upload.build_category_index(SAMPLE_STRUCTURE_MAP)
        _, subgroup, _, sub_idx, _ = index["Энергетики"]
        assert subgroup == "Энергетики"
        assert sub_idx == 1


# ── Тесты apply_structure_mapping ───────────────────────────────────────────

class TestApplyStructureMapping:
    """Тесты проставления раздела/подгруппы товарам."""

    def _make_product(self, source_category: str) -> dict:
        """Создать минимальный товар для тестирования."""
        return {
            "name": f"Товар {source_category}",
            "source_category": source_category,
            "display_group": "Тестовая группа",  # д.б. нетронута (D-04)
        }

    def test_covered_category_gets_correct_section(self):
        """Товар из покрытой категории получает корректный раздел."""
        index = upload.build_category_index(SAMPLE_STRUCTURE_MAP)
        products = [self._make_product("Кока-Кола")]
        result = upload.apply_structure_mapping(products, index)
        assert result[0]["display_section"] == "Напитки"

    def test_covered_category_gets_correct_subgroup(self):
        """Товар из покрытой категории получает корректную подгруппу."""
        index = upload.build_category_index(SAMPLE_STRUCTURE_MAP)
        products = [self._make_product("Кока-Кола")]
        result = upload.apply_structure_mapping(products, index)
        assert result[0]["display_subgroup"] == "Воды и газировки"

    def test_covered_category_gets_sort_key_tuple(self):
        """Товар из покрытой категории получает _sort_key в виде кортежа из трёх int."""
        index = upload.build_category_index(SAMPLE_STRUCTURE_MAP)
        products = [self._make_product("Акконд")]
        result = upload.apply_structure_mapping(products, index)
        sk = result[0]["_sort_key"]
        assert isinstance(sk, tuple) and len(sk) == 3

    def test_uncovered_category_gets_prochee_section(self):
        """Непокрытая категория получает раздел «Прочее» (D-12)."""
        index = upload.build_category_index(SAMPLE_STRUCTURE_MAP)
        products = [self._make_product("Неизвестная категория")]
        result = upload.apply_structure_mapping(products, index)
        assert result[0]["display_section"] == "Прочее"

    def test_uncovered_category_gets_prochee_subgroup(self):
        """Непокрытая категория получает подгруппу «Прочее» (D-12)."""
        index = upload.build_category_index(SAMPLE_STRUCTURE_MAP)
        products = [self._make_product("Неизвестная категория")]
        result = upload.apply_structure_mapping(products, index)
        assert result[0]["display_subgroup"] == "Прочее"

    def test_uncovered_category_does_not_raise(self):
        """apply_structure_mapping не падает при неизвестной категории (D-12)."""
        index = upload.build_category_index(SAMPLE_STRUCTURE_MAP)
        products = [self._make_product("Категория которой нет нигде")]
        # Должно выполниться без исключений
        result = upload.apply_structure_mapping(products, index)
        assert len(result) == 1

    def test_uncovered_sort_key_is_9999(self):
        """Непокрытая категория получает _sort_key = (9999, 9999, 9999) (уходит в конец)."""
        index = upload.build_category_index(SAMPLE_STRUCTURE_MAP)
        products = [self._make_product("Непокрытая")]
        result = upload.apply_structure_mapping(products, index)
        assert result[0]["_sort_key"] == (9999, 9999, 9999)

    def test_display_group_unchanged_by_structure_mapping(self):
        """display_group (колонка «Группа») не изменяется после apply_structure_mapping (D-04)."""
        index = upload.build_category_index(SAMPLE_STRUCTURE_MAP)
        products = [self._make_product("Акконд")]
        products[0]["display_group"] = "Конфеты и печенье"
        result = upload.apply_structure_mapping(products, index)
        # Группа должна остаться нетронутой
        assert result[0]["display_group"] == "Конфеты и печенье"


# ── Тесты заголовка Sheet (products_to_rows) ─────────────────────────────────

class TestProductsToRowsHeader:
    """Тесты формата заголовка и строк Sheet после добавления двух новых колонок."""

    def _make_minimal_product(self) -> dict:
        """Минимальный товар для вызова products_to_rows."""
        return {
            "name": "Тестовый товар",
            "price": 100.0,
            "stock": 10,
            "source_category": "Акконд",
            "display_group": "Конфеты и печенье",
            "supplier_file": "test.xlsx",
            "display_subgroup": "Конфеты",
            "display_section": "Сладкое",
        }

    def test_header_ends_with_podgruppa_razdel(self):
        """Последние два элемента заголовка — «Подгруппа» и «Раздел»."""
        products = [self._make_minimal_product()]
        rows = upload.products_to_rows(products)
        header = rows[0]
        assert header[-2] == "Подгруппа", f"Ожидали «Подгруппа», получили: {header[-2]}"
        assert header[-1] == "Раздел", f"Ожидали «Раздел», получили: {header[-1]}"

    def test_header_gruppa_at_index_4(self):
        """Колонка «Группа» остаётся на позиции 4 (D-04 — нулевой риск для витрины)."""
        products = [self._make_minimal_product()]
        rows = upload.products_to_rows(products)
        header = rows[0]
        assert header[4] == "Группа", f"Ожидали «Группа» на позиции 4, получили: {header[4]}"

    def test_row_last_two_values_match_subgroup_and_section(self):
        """Последние два значения строки товара — display_subgroup и display_section."""
        products = [self._make_minimal_product()]
        rows = upload.products_to_rows(products)
        # rows[0] — заголовок, rows[1] — первый товар
        data_row = rows[1]
        assert data_row[-2] == "Конфеты", f"Ожидали «Конфеты», получили: {data_row[-2]}"
        assert data_row[-1] == "Сладкое", f"Ожидали «Сладкое», получили: {data_row[-1]}"

    def test_row_gruppa_at_index_4_matches_display_group(self):
        """В строке товара позиция 4 содержит display_group (D-04)."""
        products = [self._make_minimal_product()]
        rows = upload.products_to_rows(products)
        data_row = rows[1]
        assert data_row[4] == "Конфеты и печенье"
