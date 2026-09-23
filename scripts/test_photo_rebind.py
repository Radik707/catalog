# -*- coding: utf-8 -*-
"""
Тесты автопереноса фото при переименовании товара (photo_rebind.py).

Все пары здесь — НАСТОЯЩИЕ, из четырёх реальных поломок каталога 2026 года.
Именно на них проверяется, что механизм ловит переименования и при этом не
привязывает чужие картинки.

Запуск: python -m pytest scripts/test_photo_rebind.py -q
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from photo_rebind import (  # noqa: E402
    differing_words,
    fingerprint,
    normalize,
    stem,
    suggest,
)

URL = "https://res.cloudinary.com/x/image/upload/v1/presenter/{}.jpg"


def _auto(suggestions, new_name):
    """Найти предложение по имени нового товара."""
    for s in suggestions:
        if s.new_name == new_name:
            return s
    raise AssertionError(f"нет предложения для «{new_name}»")


# ── Нормализация ─────────────────────────────────────────────────────────────


class TestNormalize:
    def test_отделяет_число_от_единицы(self):
        assert "100 г" in normalize("Кофе 100г/50")

    def test_раскрывает_сокращения(self):
        assert "ирландские" in normalize("Кофе Лебо молотый ирл. сливки 70г/12шт")

    def test_ё_приводится_к_е(self):
        assert normalize("Вёрсты") == normalize("Версты")


class TestFingerprint:
    def test_перестановка_слов_не_меняет_отпечаток(self):
        a = fingerprint("Стоевъ Кетчуп Острый с/бут 310г/12")
        b = fingerprint("Стоевъ Кетчуп 310г/12 стекло Острый")
        assert a == b

    def test_упаковка_не_влияет(self):
        a = fingerprint("Стоевъ Соус Камикадзе п/бут 200г./20")
        b = fingerprint("Стоевъ Соус 200г/20 п/бут Камикадзе")
        assert a == b

    def test_вкус_попадает_в_отпечаток(self):
        """В отпечатке лежат ОСНОВЫ слов (см. stem), а не словоформы."""
        assert stem("острый") in fingerprint("Кетчуп Острый 310г/12").words
        assert stem("цыганский") in fingerprint("Кетчуп Цыганский 310г/12").words

    def test_словоформы_сливаются_в_одну_основу(self):
        """«Икра из кабачков» и «Икра Кабачковая» — один товар."""
        assert fingerprint("Икра из кабачков 480г/8") == fingerprint("Икра 480г/8 Кабачковая")

    def test_разные_вкусы_не_сливаются(self):
        """Стемминг не должен склеить соседние варианты товара."""
        assert stem("экстра") != stem("эксклюзив")
        assert stem("перечный") != stem("перцовый")

    def test_граммовка_сохраняется(self):
        assert fingerprint("Суп 65г/25").numbers == ("25", "65")

    def test_пустое_имя_безопасно(self):
        assert fingerprint("").is_empty()
        assert fingerprint(None).is_empty()


# ── Настоящие переименования: должны переноситься автоматически ──────────────


class TestНастоящиеПереименования:
    """Поставщик переставил слова — это тот же товар, фото обязано переехать."""

    @pytest.mark.parametrize(
        "old, new",
        [
            # «Стоевъ», 2026-09-23
            ("Стоевъ Кетчуп Острый с/бут 310г/12", "Стоевъ Кетчуп 310г/12 стекло Острый"),
            ("Стоевъ Соус Креветочный п/бут 250г/12", "Стоевъ Соус 250г/12 п/бут Креветочный"),
            ("Стоевъ Горчица Баварская с/б (евро) 190г/12", "Стоевъ Горчица 190г/12 стекло (евро) Баварская"),
            ("Стоевъ Приправа Петрушка zip-lock 10г./30", "Стоевъ Приправа 10г/30 zip-lock Петрушка"),
            ("Стоевъ Икра из кабачков  с/б (евро) 480г/8", "Стоевъ Икра 480г/8 стекло (евро) Кабачковая"),
            # «Кофе Лебо», 2026-09-17
            ("Кофе Лебо молотый Голд в/с (для чашки) 100г/50шт", "Кофе Лебо молотый м/у 100г/50 Голд (для чашки)"),
            ("Кофе Лебо Экстра м/у 170г/6 сублимированный", "Кофе Лебо сублимированный м/у 170/6 Экстра"),
            ("Кофе Лебо молотый карамель TOFEE 150г/12шт", "Кофе Лебо молотый м/у 150г/12 Карамель TOFEE"),
            # Супы, 2026-09-17
            ("Суперсуп гороховый с беконом пакет.70г/30", "Суперсуп пакет 70г/30 Гороховый с беконом"),
            ("Суп мясной с вермишелью пакет.60г/25", "Дачный сезон 60г/25 Суп мясной с вермишелью пакет"),
        ],
    )
    def test_переносится_автоматически(self, old, new):
        result = suggest([new], {old: URL.format("1")})
        assert result[0].auto, f"не перенеслось: {result[0].reason}"
        assert result[0].old_name == old


# ── Чужие товары: привязывать НЕЛЬЗЯ ─────────────────────────────────────────


class TestЧужиеНеПривязываются:
    """Каждый случай — ошибка, которую ловили руками при разборе поломок."""

    def test_эксклюзив_не_берет_фото_экстры(self):
        result = suggest(
            ["Кофе Лебо сублимированный м/у 100г/10 Эксклюзив"],
            {"Кофе Лебо Экстра м/у 100г/10 сублимированный": URL.format("1")},
        )
        assert not result[0].auto

    def test_рассольник_не_берет_фото_горохового(self):
        result = suggest(
            ["Дачный сезон 60г/25 Суп рассольник пакет"],
            {"Суп гороховый пакет.60г/25": URL.format("1")},
        )
        assert not result[0].auto

    def test_говядина_не_берет_фото_грибов(self):
        result = suggest(
            ["Супершеф 70г/12 Каша Гречка со вкус.Говядины стак"],
            {"Каша Гречка с грибами и овощ.стак.70г/12": URL.format("1")},
        )
        assert not result[0].auto

    def test_цыганский_не_берет_фото_острого(self):
        result = suggest(
            ["Стоевъ Кетчуп 310г/12 стекло Циганский"],
            {"Стоевъ Кетчуп Острый с/бут 310г/12": URL.format("1")},
        )
        assert not result[0].auto

    def test_овсяные_хлопья_не_берут_фото_кукурузных(self):
        result = suggest(
            ["Хлопья МИСТРАЛЬ Овсяные с отрубями 400 г/12"],
            {"Хлопья МИСТРАЛЬ Кукурузные 400г/12 (фермерские/цельнозерновые)": URL.format("1")},
        )
        assert not result[0].auto

    def test_новинка_без_пары_не_получает_ничего(self):
        result = suggest(
            ["Энергетик Ред Булл 1\\24*0,25 л. Ж/Б"],
            {"Энергетик Адреналин Раш 0.5\\12": URL.format("1")},
        )
        assert not result[0].auto

    def test_другая_граммовка_не_проходит_автоматом(self):
        """Суп 65г и суп 60г — переупаковка; решать должен человек."""
        result = suggest(
            ["Суп рассольник пакет 60г/25"],
            {"Суп рассольник пакет.65г/25": URL.format("1")},
        )
        assert not result[0].auto
        assert "граммовка" in result[0].reason


# ── Конкуренция за одно фото ─────────────────────────────────────────────────


class TestКонкуренцияЗаФото:
    def test_одно_фото_не_достается_двоим(self):
        """Правильный товар забирает фото, второй уходит человеку.

        Реальный случай: рядом с «Кетчуп Острый» появился «Кетчуп Цыганский»,
        и оба тянулись к одной картинке.
        """
        result = suggest(
            [
                "Стоевъ Кетчуп 310г/12 стекло Острый",
                "Стоевъ Кетчуп 310г/12 стекло Циганский",
            ],
            {"Стоевъ Кетчуп Острый с/бут 310г/12": URL.format("1")},
        )
        assert _auto(result, "Стоевъ Кетчуп 310г/12 стекло Острый").auto
        assert not _auto(result, "Стоевъ Кетчуп 310г/12 стекло Циганский").auto

    def test_верный_кандидат_выигрывает_у_соседа(self):
        """При выборе из нескольких старых берётся тот, у кого совпал вкус."""
        result = suggest(
            ["Кофе Лебо сублимированный м/у 70г/12 Ирландские сливки"],
            {
                "Кофе Лебо молотый ирл. сливки 70г/12шт": URL.format("верное"),
                "Кофе Лебо Экстра м/у 70г/12 сублимированный": URL.format("чужое"),
            },
        )
        assert result[0].old_name == "Кофе Лебо молотый ирл. сливки 70г/12шт"


# ── Устойчивость ─────────────────────────────────────────────────────────────


class TestУстойчивость:
    def test_пустые_входные_не_падают(self):
        assert suggest([], {}) == []
        assert suggest(["Товар"], {}) == []
        assert suggest([], {"Старый": URL.format("1")}) == []

    def test_каждому_новому_ровно_одно_предложение(self):
        new = ["Стоевъ Кетчуп 310г/12 стекло Острый", "Совсем новый товар 1/1"]
        result = suggest(new, {"Стоевъ Кетчуп Острый с/бут 310г/12": URL.format("1")})
        assert len(result) == len(new)

    def test_автоприменимые_идут_первыми(self):
        result = suggest(
            ["Совсем новый товар 1/1", "Стоевъ Кетчуп 310г/12 стекло Острый"],
            {"Стоевъ Кетчуп Острый с/бут 310г/12": URL.format("1")},
        )
        assert result[0].auto and not result[-1].auto


# ── Фиксация результата на диске (upload.persist_rebinds) ────────────────────


class TestФиксацияПривязок:
    """Автоперенос обязан ЗАПИСАТЬ связь, иначе она пересчитывалась бы каждый раз.

    Подменяем каталог скриптов на временный, чтобы не трогать боевые JSON.
    """

    @pytest.fixture
    def upload(self, tmp_path, monkeypatch):
        import importlib.util
        import json

        spec = importlib.util.spec_from_file_location(
            "upload_mod", str(Path(__file__).parent / "upload.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        monkeypatch.setattr(mod, "SCRIPT_DIR", tmp_path)
        (tmp_path / "photo_urls.json").write_text(
            json.dumps({"старое.jpg": "https://cdn/x/upload/v1/presenter/старое.jpg"}),
            encoding="utf-8",
        )
        (tmp_path / "photo_overrides.json").write_text(
            json.dumps({"Прежний товар": "presenter/старое.jpg"}), encoding="utf-8"
        )
        return mod, tmp_path

    def test_записывает_новый_ключ_и_не_трогает_старые(self, upload):
        import json

        mod, tmp = upload
        saved = mod.persist_rebinds(
            suggest(
                ["Стоевъ Кетчуп 310г/12 стекло Острый"],
                {"Стоевъ Кетчуп Острый с/бут 310г/12": "https://cdn/x/upload/v1/presenter/777.jpg"},
            )
        )
        assert saved == 1
        overrides = json.loads((tmp / "photo_overrides_auto.json").read_text(encoding="utf-8"))
        urls = json.loads((tmp / "photo_urls_auto.json").read_text(encoding="utf-8"))
        assert overrides["Стоевъ Кетчуп 310г/12 стекло Острый"] == "presenter/777.jpg"
        assert urls["777.jpg"] == "https://cdn/x/upload/v1/presenter/777.jpg"
        # Боевые файлы из git автоперенос не трогает — только свои runtime
        main = json.loads((tmp / "photo_overrides.json").read_text(encoding="utf-8"))
        assert main == {"Прежний товар": "presenter/старое.jpg"}

    def test_ссылка_с_обрезкой_привязывается_коротким_ключом(self, upload):
        """У обрезанных ссылок upload.py не выводит папку — работает только имя файла."""
        import json

        mod, tmp = upload
        cropped = "https://cdn/x/upload/c_crop,w_10/v1/presenter/888.jpg"
        mod.persist_rebinds(
            suggest(
                ["Стоевъ Кетчуп 310г/12 стекло Острый"],
                {"Стоевъ Кетчуп Острый с/бут 310г/12": cropped},
            )
        )
        overrides = json.loads((tmp / "photo_overrides_auto.json").read_text(encoding="utf-8"))
        assert overrides["Стоевъ Кетчуп 310г/12 стекло Острый"] == "888.jpg"

    def test_спорное_не_записывается(self, upload):
        mod, _ = upload
        assert mod.persist_rebinds(
            suggest(
                ["Стоевъ Кетчуп 310г/12 стекло Циганский"],
                {"Стоевъ Кетчуп Острый с/бут 310г/12": "https://cdn/x/upload/v1/presenter/1.jpg"},
            )
        ) == 0


# ── Кто считается потерявшим фото (upload.find_photo_orphans) ────────────────


class TestКтоОсталсяБезФото:
    """Механизм должен браться только за тех, у кого фото ДЕЙСТВИТЕЛЬНО нет.

    Дефект, пойманный на боевом предпросмотре 2026-09-23: товары с фото из
    админки («Правки») считались потерявшими его — 148 бессмысленных привязок
    товара к самому себе и 12 ложных «нужен взгляд владельца».
    """

    @pytest.fixture
    def upload(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "upload_orphans", str(Path(__file__).parent / "upload.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_фото_из_правок_не_считается_потерей(self, upload):
        products = [{"name": "Товар А", "photo_override": "presenter/1.jpg"}]
        assert upload.find_photo_orphans(products, {}) == []

    def test_фото_из_привязок_не_считается_потерей(self, upload):
        products = [{"name": "Товар А"}]
        photo_data = {"товар а": {"url": "https://cdn/1.jpg", "description": ""}}
        assert upload.find_photo_orphans(products, photo_data) == []

    def test_товар_совсем_без_фото_попадает_в_кандидаты(self, upload):
        products = [{"name": "Товар без картинки"}]
        assert upload.find_photo_orphans(products, {}) == ["Товар без картинки"]

    def test_пустая_строка_в_правке_не_спасает(self, upload):
        """Пустой photo_override — это отсутствие фото, а не фото."""
        products = [{"name": "Товар А", "photo_override": ""}]
        assert upload.find_photo_orphans(products, {}) == ["Товар А"]
