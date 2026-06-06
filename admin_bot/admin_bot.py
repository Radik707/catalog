r"""
admin_bot.py — Telegram-бот администратора каталога.

Слушает нажатия inline-кнопок в уведомлениях, которые присылает веб-загрузчик
при проблеме с обновлением, и выполняет решение владельца:
  • «Оставить прошлую»      (keep)  → удаляет отложенную новую версию
  • «Всё равно применить»   (apply) → применяет отложенную версию (Товары_NEW → Товары)
  • «Показать файлы»        (files) → присылает в чат загруженные .xlsx для проверки

Связь — long polling (getUpdates) через прокси (Telegram в РФ ограничен).
Слушает только владельца (OWNER_CHAT_ID). Запросы к Google (sheet_tool) идут
БЕЗ прокси (напрямую), к Telegram — ЧЕРЕЗ прокси.

Запуск: python admin_bot.py
Настройки берёт из окружения (systemd EnvironmentFile=uploader/.env):
    TELEGRAM_TOKEN, OWNER_CHAT_ID, TG_PROXY,
    UPLOAD_SCRIPT (→ рядом sheet_tool.py), PYTHON_BIN, LAST_BATCH_DIR
"""

import os
import re
import sys
import time
import glob
import logging
import subprocess
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("admin_bot")

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent


def load_env() -> None:
    """Фолбэк-загрузка uploader/.env (systemd обычно уже даёт env)."""
    env_path = PROJECT_ROOT / "uploader" / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip("'\""))


load_env()

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_CHAT_ID", "0") or "0")
TG_PROXY = os.environ.get("TG_PROXY", "")
UPLOAD_SCRIPT = Path(
    os.environ.get("UPLOAD_SCRIPT", str(PROJECT_ROOT / "scripts" / "upload.py"))
)
SHEET_TOOL = UPLOAD_SCRIPT.parent / "sheet_tool.py"
PYTHON_BIN = os.environ.get("PYTHON_BIN", sys.executable)
LAST_BATCH_DIR = Path(
    os.environ.get("LAST_BATCH_DIR", str(PROJECT_ROOT / "uploader" / "last_batch"))
)

API = f"https://api.telegram.org/bot{TOKEN}"
PROXIES = {"https": TG_PROXY, "http": TG_PROXY} if TG_PROXY else None


# ── Telegram API (через прокси) ──

def tg(method: str, **params) -> dict:
    try:
        r = requests.post(f"{API}/{method}", json=params, timeout=40, proxies=PROXIES)
        data = r.json()
        if not data.get("ok"):
            log.warning("TG %s error: %s", method, data)
            return {}
        return data.get("result", {})
    except requests.RequestException as e:
        log.warning("TG %s exc: %s", method, e)
        return {}


def send(text: str) -> None:
    tg("sendMessage", chat_id=OWNER_ID, text=text)


def send_document(path: Path) -> None:
    try:
        with open(path, "rb") as f:
            requests.post(f"{API}/sendDocument",
                          data={"chat_id": OWNER_ID},
                          files={"document": (path.name, f)},
                          timeout=120, proxies=PROXIES)
    except (requests.RequestException, OSError) as e:
        log.warning("sendDocument %s exc: %s", path.name, e)


# ── Google (sheet_tool) — БЕЗ прокси ──

def run_sheet_tool(cmd: str) -> tuple[int, str]:
    """Запуск sheet_tool.py со снятыми proxy-переменными (Google идёт напрямую)."""
    env = {k: v for k, v in os.environ.items()
           if k.lower() not in ("https_proxy", "http_proxy", "all_proxy")}
    proc = subprocess.run(
        [PYTHON_BIN, str(SHEET_TOOL), cmd],
        cwd=str(SHEET_TOOL.parent),
        capture_output=True, text=True, timeout=600, env=env,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


# ── Обработчики ──

def handle_callback(cb: dict) -> None:
    cb_id = cb.get("id")
    user_id = cb.get("from", {}).get("id")
    data = cb.get("data", "")
    msg = cb.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    msg_id = msg.get("message_id")

    tg("answerCallbackQuery", callback_query_id=cb_id)
    if user_id != OWNER_ID:
        return

    if data == "keep":
        run_sheet_tool("drop_new")
        tg("editMessageText", chat_id=chat_id, message_id=msg_id,
           text="✅ Оставлена прошлая версия каталога. Новая отклонена.")

    elif data == "apply":
        rc, out = run_sheet_tool("apply_new")
        if "NO_NEW" in out:
            send("Отложенной версии уже нет (возможно, был сделан откат).")
            return
        m = re.search(r"rows=(\d+)", out)
        rows = m.group(1) if m else "?"
        tg("editMessageText", chat_id=chat_id, message_id=msg_id,
           text=f"⚠️ Применена новая версия каталога ({rows} товаров). Сайт обновится за минуту.")

    elif data == "files":
        files = sorted(glob.glob(str(LAST_BATCH_DIR / "*.xlsx")))
        if not files:
            send("Загруженные файлы не найдены (возможно, уже удалены).")
            return
        send(f"Загруженные файлы последней партии ({len(files)} шт.):")
        for fp in files:
            send_document(Path(fp))


def handle_message(m: dict) -> None:
    chat_id = m.get("chat", {}).get("id")
    user_id = m.get("from", {}).get("id")
    text = (m.get("text") or "").strip().lower()

    if OWNER_ID == 0:
        tg("sendMessage", chat_id=chat_id,
           text=f"Бот настраивается. Ваш Telegram-id: {user_id}")
        log.info("OWNER_ID не задан. Отправитель id=%s", user_id)
        return
    if user_id != OWNER_ID:
        return
    if text in ("/start", "/help"):
        send("Бот-администратор каталога готов. Я пишу сюда об итогах обновления "
             "и присылаю кнопки решения при проблемах.")


def main() -> None:
    if not TOKEN:
        log.error("Не задан TELEGRAM_TOKEN. См. uploader/.env")
        sys.exit(1)
    me = tg("getMe")
    log.info("Admin-бот запущен: @%s, владелец id=%s", me.get("username", "?"),
             OWNER_ID or "(не задан)")

    offset = None
    while True:
        try:
            params = {"timeout": 50, "allowed_updates": ["message", "callback_query"]}
            if offset is not None:
                params["offset"] = offset
            r = requests.get(f"{API}/getUpdates", params=params, timeout=70, proxies=PROXIES)
            updates = r.json().get("result", [])
        except requests.RequestException as e:
            log.warning("getUpdates сбой, повтор через 5с: %s", e)
            time.sleep(5)
            continue

        for upd in updates:
            offset = upd["update_id"] + 1
            try:
                if "callback_query" in upd:
                    handle_callback(upd["callback_query"])
                elif "message" in upd:
                    handle_message(upd["message"])
            except Exception as e:
                log.exception("Ошибка обработки апдейта: %s", e)


if __name__ == "__main__":
    main()
