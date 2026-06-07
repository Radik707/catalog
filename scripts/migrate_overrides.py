r"""
migrate_overrides.py — Разовая утилита миграции захардкоженных правил групп в память правок.

Назначение:
    Раскрыть словари PRODUCT_OVERRIDES (поиск по началу строки) и PRODUCT_CONTAINS_OVERRIDES
    (поиск по подстроке) из upload.py в точечные правки типа «group» по ТОЧНОМУ нормализованному
    имени товара (D-04) и записать их во вкладку «Правки» Google Sheet.

    После выполнения новые переопределения групп добавляются прямо во вкладку «Правки»
    — код upload.py больше не нужно трогать (D-07 закрыт).

Использование:
    python scripts/migrate_overrides.py --dry-run   # только показать план, без записи
    python scripts/migrate_overrides.py             # боевой запуск — записать во вкладку

Требования:
    - GOOGLE_SHEETS_ID в окружении (или .env)
    - credentials.json в scripts/ или в корне проекта
    - gspread и google-auth-oauthlib уже установлены (requirements.txt)

Примечания:
    - Скрипт только ДОПИСЫВАЕТ строки (append); существующие правки владельца не затирает.
    - Дубликаты (товар уже имеет group-правку) пропускаются с логом.
    - Миграция РАЗОВАЯ: после удаления PRODUCT_OVERRIDES из upload.py (Task 3) повторный
      запуск этого скрипта будет невозможен — и это ожидаемое поведение.
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# --- Путь к скриптам (чтобы импортировать upload.py) ---
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Имя вкладки «Правки» в Google Sheet
EDITS_SHEET_NAME = "Правки"

# Заголовки вкладки «Правки» (схема из 03-01-SUMMARY.md)
EDITS_HEADER = ["Товар", "Тип", "Значение"]

# --- Настройка логирования ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def expand_overrides(product_names: list[str]) -> dict[str, str]:
    """Раскрыть префиксные и подстрочные правила в точечные правки по нормализованным именам.

    Принимает список реальных названий товаров (из листа «Товары» или синтетических).
    Возвращает {normalize_name(имя): группа} для тех имён, что попали под
    хотя бы одно правило из PRODUCT_OVERRIDES (startswith) или PRODUCT_CONTAINS_OVERRIDES
    (substring). Логика сопоставления — копия apply_product_override: сначала prefix, затем
    substring; первое сработавшее правило побеждает.

    Ключи результата — ТОЧНЫЕ нормализованные имена, не префиксы (D-04).
    Функция НЕ делает сетевых вызовов — можно использовать в локальных тестах без Google.
    """
    from upload import PRODUCT_OVERRIDES, PRODUCT_CONTAINS_OVERRIDES, normalize_name

    result: dict[str, str] = {}

    for raw_name in product_names:
        name_lower = raw_name.lower()

        # Проверяем prefix-правила (startswith)
        matched_group: str | None = None
        for prefix, group in PRODUCT_OVERRIDES.items():
            if name_lower.startswith(prefix.lower()):
                matched_group = group
                break

        # Если prefix не совпал — проверяем substring-правила
        if matched_group is None:
            for substring, group in PRODUCT_CONTAINS_OVERRIDES:
                if substring.lower() in name_lower:
                    matched_group = group
                    break

        if matched_group is not None:
            key = normalize_name(raw_name)
            result[key] = matched_group

    return result


def load_env() -> None:
    """Загрузить переменные окружения из .env (как в upload.py и sheet_tool.py)."""
    project_root = SCRIPT_DIR.parent
    for search_dir in (project_root, SCRIPT_DIR):
        env_path = search_dir / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip().strip("'\""))
            break


def open_spreadsheet():
    """Авторизация через Service Account и открытие таблицы (паттерн из sheet_tool.py)."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        raise SystemExit(1, "Не установлен gspread или google-auth: pip install gspread google-auth")

    # Поиск credentials.json (те же места, что upload.py)
    creds_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "")
    if not creds_path:
        for d in (SCRIPT_DIR, SCRIPT_DIR.parent):
            candidate = d / "credentials.json"
            if candidate.exists():
                creds_path = str(candidate)
                break

    sheets_id = os.environ.get("GOOGLE_SHEETS_ID", "")
    if not creds_path:
        raise SystemExit(1, "ERROR: credentials.json не найден (GOOGLE_CREDENTIALS_PATH не задан)")
    if not sheets_id:
        raise SystemExit(1, "ERROR: GOOGLE_SHEETS_ID не задан в .env или окружении")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    return gspread.authorize(creds).open_by_key(sheets_id)


def get_existing_group_overrides(ss) -> set[str]:
    """Прочитать вкладку «Правки» и вернуть множество нормализованных имён, у которых
    уже есть правка типа 'group'. Нужно для пропуска дубликатов (T-03-06).

    Если вкладки «Правки» нет — возвращает пустое множество.
    """
    import gspread.exceptions

    from upload import normalize_name

    try:
        ws = ss.worksheet(EDITS_SHEET_NAME)
        values = ws.get_all_values()
    except gspread.exceptions.WorksheetNotFound:
        log.info("Вкладка «%s» ещё не существует — будет создана.", EDITS_SHEET_NAME)
        return set()

    if not values:
        return set()

    header = values[0]
    try:
        товар_i = header.index("Товар")
        тип_i = header.index("Тип")
    except ValueError:
        log.warning("Вкладка «%s»: ожидались колонки %s — пропускаем проверку дубликатов",
                    EDITS_SHEET_NAME, EDITS_HEADER)
        return set()

    existing: set[str] = set()
    for row in values[1:]:
        if len(row) > max(товар_i, тип_i):
            if str(row[тип_i]).strip() == "group" and str(row[товар_i]).strip():
                existing.add(normalize_name(str(row[товар_i]).strip()))

    return existing


def ensure_edits_sheet(ss):
    """Получить вкладку «Правки», создав её при отсутствии (с заголовками).

    Возвращает объект worksheet.
    """
    import gspread.exceptions

    try:
        ws = ss.worksheet(EDITS_SHEET_NAME)
        # Проверяем, есть ли заголовок
        values = ws.get_all_values()
        if not values:
            log.info("Вкладка «%s» пуста — добавляем заголовки.", EDITS_SHEET_NAME)
            ws.append_row(EDITS_HEADER, value_input_option="USER_ENTERED")
    except gspread.exceptions.WorksheetNotFound:
        log.info("Создаём вкладку «%s» с заголовками.", EDITS_SHEET_NAME)
        ws = ss.add_worksheet(title=EDITS_SHEET_NAME, rows=500, cols=3)
        ws.append_row(EDITS_HEADER, value_input_option="USER_ENTERED")

    return ws


def main() -> None:
    """Точка входа: разбор аргументов, раскрытие правил, запись во вкладку."""
    parser = argparse.ArgumentParser(
        description="Перенести PRODUCT_OVERRIDES и PRODUCT_CONTAINS_OVERRIDES из upload.py "
                    "во вкладку «Правки» Google Sheet (тип правки: group)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Показать план миграции без записи в Google Sheet",
    )
    args = parser.parse_args()

    # --- Импорт правил и функций из upload.py ---
    try:
        from upload import PRODUCT_OVERRIDES, PRODUCT_CONTAINS_OVERRIDES, load_current_groups
    except ImportError as exc:
        raise SystemExit(1) from exc

    # --- Загрузить .env ---
    load_env()

    # --- Шаг 1: получить список реальных названий товаров ---
    if args.dry_run:
        log.info("[dry-run] Загружаем текущий каталог для раскрытия правил...")
    else:
        log.info("Загружаем текущий каталог для раскрытия правил...")

    current_groups = load_current_groups()
    if not current_groups:
        # В dry-run режиме нет credentials — работаем с пустым списком, просто покажем правила
        log.warning(
            "Не удалось загрузить текущие группы (нет credentials или листа «Товары»). "
            "В --dry-run раскрытие будет показано на примере ключей PRODUCT_OVERRIDES."
        )
        # Используем ключи самих словарей как синтетические имена для демонстрации
        synthetic_names = list(PRODUCT_OVERRIDES.keys()) + [sub for sub, _ in PRODUCT_CONTAINS_OVERRIDES]
        real_names = synthetic_names
    else:
        # Реальные названия из листа «Товары» (денормализованные — нам нужны оригиналы)
        # load_current_groups возвращает {normalize_name: группа}, но нам нужны оригиналы
        # Читаем напрямую через те же credentials
        real_names = _load_raw_product_names()
        if not real_names:
            log.warning("Список товаров пуст — раскрытие невозможно.")
            raise SystemExit(0)

    # --- Шаг 2: раскрыть правила в точечные правки ---
    expanded = expand_overrides(real_names)
    log.info("Раскрыто правок: %d (из %d исходных правил)", len(expanded),
             len(PRODUCT_OVERRIDES) + len(PRODUCT_CONTAINS_OVERRIDES))

    if not expanded:
        log.info("Нет товаров, подходящих под правила — вкладка не изменяется.")
        raise SystemExit(0)

    # --- Шаг 3: dry-run — показать план ---
    if args.dry_run:
        log.info("[dry-run] Будет записано %d строк типа 'group':", len(expanded))
        # Группируем по исходному правилу для наглядности
        _print_dry_run_report(expanded, PRODUCT_OVERRIDES, PRODUCT_CONTAINS_OVERRIDES)
        log.info("[dry-run] Запись в Google Sheet НЕ выполнялась.")
        return

    # --- Шаг 4: боевой запуск — открыть таблицу ---
    log.info("Открываем Google Sheet...")
    try:
        ss = open_spreadsheet()
    except SystemExit:
        raise
    except Exception as exc:
        log.error("Не удалось открыть таблицу: %s", exc)
        raise SystemExit(1) from exc

    # --- Шаг 5: проверить существующие правки group (дедупликация, T-03-06) ---
    existing_keys = get_existing_group_overrides(ss)
    if existing_keys:
        log.info("Уже существует group-правок во вкладке: %d — дубликаты будут пропущены",
                 len(existing_keys))

    # --- Шаг 6: собрать новые строки (без дубликатов) ---
    new_rows: list[list[str]] = []
    skipped = 0
    for norm_name, group in sorted(expanded.items()):
        if norm_name in existing_keys:
            log.info("  Пропуск (уже есть): %s → %s", norm_name, group)
            skipped += 1
            continue
        new_rows.append([norm_name, "group", group])

    log.info("Новых строк для записи: %d (пропущено дубликатов: %d)", len(new_rows), skipped)

    if not new_rows:
        log.info("Все правки уже присутствуют во вкладке — ничего не записываем.")
        raise SystemExit(0)

    # --- Шаг 7: убедиться, что вкладка существует и дописать ---
    ws = ensure_edits_sheet(ss)
    ws.append_rows(new_rows, value_input_option="USER_ENTERED")
    log.info("Записано строк во вкладку «%s»: %d", EDITS_SHEET_NAME, len(new_rows))
    log.info("Миграция завершена.")


def _load_raw_product_names() -> list[str]:
    """Загрузить оригинальные (ненормализованные) названия товаров из листа «Товары».

    Используется для раскрытия правил по реальному каталогу.
    """
    load_env()
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        return []

    creds_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "")
    if not creds_path:
        for d in (SCRIPT_DIR, SCRIPT_DIR.parent):
            c = d / "credentials.json"
            if c.exists():
                creds_path = str(c)
                break

    sheets_id = os.environ.get("GOOGLE_SHEETS_ID", "")
    if not creds_path or not sheets_id:
        return []

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    try:
        creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        ss = gspread.authorize(creds).open_by_key(sheets_id)
        values = ss.worksheet("Товары").get_all_values()
    except Exception as exc:  # noqa: BLE001
        log.warning("Не удалось загрузить список товаров: %s", exc)
        return []

    if not values:
        return []

    header = values[0]
    try:
        name_i = header.index("Наименование")
    except ValueError:
        return []

    return [str(row[name_i]).strip() for row in values[1:] if len(row) > name_i and row[name_i]]


def _print_dry_run_report(
    expanded: dict[str, str],
    product_overrides: dict[str, str],
    product_contains_overrides: list[tuple[str, str]],
) -> None:
    """Вывести подробный отчёт dry-run: по каждому исходному правилу — сколько товаров раскрылось."""
    # Группируем раскрытые правки по исходному правилу для читаемости
    prefix_hits: dict[str, list[str]] = {k: [] for k in product_overrides}
    substring_hits: dict[str, list[str]] = {sub: [] for sub, _ in product_contains_overrides}
    unattributed: list[str] = []

    for norm_name, group in expanded.items():
        attributed = False
        # Пробуем отнести к prefix-правилу
        for prefix in product_overrides:
            if norm_name.startswith(prefix.lower()):
                prefix_hits[prefix].append(norm_name)
                attributed = True
                break
        if not attributed:
            # Пробуем отнести к substring-правилу
            for sub, _ in product_contains_overrides:
                if sub.lower() in norm_name:
                    substring_hits[sub].append(norm_name)
                    attributed = True
                    break
        if not attributed:
            unattributed.append(norm_name)

    log.info("--- Отчёт по prefix-правилам (PRODUCT_OVERRIDES) ---")
    for prefix, group in product_overrides.items():
        hits = prefix_hits.get(prefix, [])
        log.info("  Правило [%s → %s]: %d товаров", prefix, group, len(hits))
        for name in hits:
            log.info("    • %s", name)

    log.info("--- Отчёт по substring-правилам (PRODUCT_CONTAINS_OVERRIDES) ---")
    for sub, group in product_contains_overrides:
        hits = substring_hits.get(sub, [])
        log.info("  Правило [%s → %s]: %d товаров", sub, group, len(hits))
        for name in hits:
            log.info("    • %s", name)

    if unattributed:
        log.warning("Не атрибутировано (логическая ошибка): %s", unattributed)


if __name__ == "__main__":
    main()
