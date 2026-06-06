r"""
sheet_tool.py — резервное копирование и откат каталога в Google Sheet.

Подстраховка для веб-загрузчика: перед каждым обновлением делаем копию листа
«Товары» в лист «Товары_BACKUP». Если новая загрузка сбила каталог — откатываемся.

Команды:
    python sheet_tool.py backup    # Товары → Товары_BACKUP (печатает BACKUP_OK rows=N)
    python sheet_tool.py rollback  # Товары_BACKUP → Товары (печатает ROLLBACK_OK rows=N)
    python sheet_tool.py count     # печатает число товаров в «Товары» (COUNT rows=N)

Настройки берутся как в upload.py: GOOGLE_SHEETS_ID и credentials.json
(из .env в корне проекта или в scripts/, и credentials.json в scripts/).
"""

import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

SHEET_NAME = "Товары"
BACKUP_NAME = "Товары_BACKUP"
NEW_NAME = "Товары_NEW"  # отложенная новая версия (для «всё равно применить»)


def load_env() -> None:
    """Загрузка .env (как в upload.py): ключ=значение, из корня или scripts/."""
    for search_dir in (PROJECT_ROOT, SCRIPT_DIR):
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
    """Авторизация и открытие таблицы по GOOGLE_SHEETS_ID."""
    import gspread
    from google.oauth2.service_account import Credentials

    creds_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "")
    if not creds_path:
        for d in (SCRIPT_DIR, PROJECT_ROOT):
            candidate = d / "credentials.json"
            if candidate.exists():
                creds_path = str(candidate)
                break
    sheets_id = os.environ.get("GOOGLE_SHEETS_ID", "")
    if not creds_path or not sheets_id:
        print("ERROR: нет credentials.json или GOOGLE_SHEETS_ID")
        sys.exit(2)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    return gspread.authorize(creds).open_by_key(sheets_id)


def copy_sheet(ss, src_name: str, dst_name: str) -> int:
    """Скопировать значения листа src → dst (dst создаётся/очищается).

    Возвращает число строк данных (без заголовка).
    """
    from gspread.exceptions import WorksheetNotFound

    src = ss.worksheet(src_name)
    values = src.get_all_values()  # включая заголовок

    try:
        dst = ss.worksheet(dst_name)
        dst.clear()
    except WorksheetNotFound:
        cols = len(values[0]) if values else 9
        dst = ss.add_worksheet(title=dst_name, rows=len(values) + 10, cols=cols)

    if dst.row_count < len(values):
        dst.resize(rows=len(values) + 10)
    if values:
        dst.update(values, value_input_option="USER_ENTERED")

    return max(0, len(values) - 1)


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    load_env()
    ss = open_spreadsheet()

    if cmd == "backup":
        rows = copy_sheet(ss, SHEET_NAME, BACKUP_NAME)
        print(f"BACKUP_OK rows={rows}")

    elif cmd == "rollback":
        from gspread.exceptions import WorksheetNotFound
        try:
            ss.worksheet(BACKUP_NAME)
        except WorksheetNotFound:
            print("NO_BACKUP")
            sys.exit(1)
        rows = copy_sheet(ss, BACKUP_NAME, SHEET_NAME)
        print(f"ROLLBACK_OK rows={rows}")

    elif cmd == "count":
        ws = ss.worksheet(SHEET_NAME)
        rows = max(0, len(ws.get_all_values()) - 1)
        print(f"COUNT rows={rows}")

    elif cmd == "stash_new":
        # Отложить текущую (новую, подозрительную) версию в Товары_NEW
        rows = copy_sheet(ss, SHEET_NAME, NEW_NAME)
        print(f"STASH_OK rows={rows}")

    elif cmd == "apply_new":
        # Применить отложенную новую версию: Товары_NEW → Товары
        from gspread.exceptions import WorksheetNotFound
        try:
            ss.worksheet(NEW_NAME)
        except WorksheetNotFound:
            print("NO_NEW")
            sys.exit(1)
        rows = copy_sheet(ss, NEW_NAME, SHEET_NAME)
        print(f"APPLY_OK rows={rows}")

    elif cmd == "drop_new":
        # Удалить отложенную версию (решено оставить прошлую)
        from gspread.exceptions import WorksheetNotFound
        try:
            ss.del_worksheet(ss.worksheet(NEW_NAME))
        except WorksheetNotFound:
            pass
        print("DROP_OK")

    else:
        print("Использование: sheet_tool.py [backup|rollback|count|stash_new|apply_new|drop_new]")
        sys.exit(2)


if __name__ == "__main__":
    main()
