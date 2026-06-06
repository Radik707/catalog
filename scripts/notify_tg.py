r"""
notify_tg.py — отправка уведомления администратору в Telegram.

Используется веб-загрузчиком: сообщает владельцу об итоге обновления каталога.
При проблеме отправляет сообщение с inline-кнопками решения.

Команды:
    python notify_tg.py plain "<текст>"      # просто сообщение (успех/ошибка)
    python notify_tg.py decision "<текст>"    # сообщение + кнопки:
                                              #   [Оставить прошлую] (callback keep)
                                              #   [Всё равно применить] (callback apply)

Настройки (env, обычно наследуются от app.py или из .env):
    TELEGRAM_TOKEN    — токен бота от @BotFather
    OWNER_CHAT_ID     — Telegram-id владельца (куда слать)
    TG_PROXY          — прокси для api.telegram.org (напр. socks5h://127.0.0.1:1080)

Если TELEGRAM_TOKEN или OWNER_CHAT_ID не заданы — тихо выходит (SKIP), не ошибка.
"""

import os
import sys
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent


def load_env() -> None:
    """Подхватить .env из корня / scripts/ / uploader/ (inherited env приоритетнее)."""
    for env_path in (PROJECT_ROOT / ".env", SCRIPT_DIR / ".env",
                     PROJECT_ROOT / "uploader" / ".env"):
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def main() -> None:
    load_env()
    mode = sys.argv[1] if len(sys.argv) > 1 else "plain"
    text = sys.argv[2] if len(sys.argv) > 2 else ""

    token = os.environ.get("TELEGRAM_TOKEN", "")
    owner = os.environ.get("OWNER_CHAT_ID", "")
    proxy = os.environ.get("TG_PROXY", "")

    if not token or not owner or owner == "0":
        print("SKIP: TELEGRAM_TOKEN/OWNER_CHAT_ID не заданы")
        return  # не ошибка — просто уведомления ещё не настроены

    params = {"chat_id": owner, "text": text}
    if mode == "decision":
        params["reply_markup"] = {"inline_keyboard": [
            [{"text": "✅ Оставить прошлую", "callback_data": "keep"},
             {"text": "⚠️ Всё равно применить", "callback_data": "apply"}],
            [{"text": "📎 Показать файлы", "callback_data": "files"}],
        ]}
    elif mode == "error":
        params["reply_markup"] = {"inline_keyboard": [
            [{"text": "📎 Показать загруженные файлы", "callback_data": "files"}],
        ]}

    proxies = {"https": proxy, "http": proxy} if proxy else None
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          json=params, timeout=30, proxies=proxies)
        if r.ok and r.json().get("ok"):
            print("SENT")
        else:
            print(f"TG_ERROR: {r.status_code} {r.text[:200]}")
            sys.exit(1)
    except requests.RequestException as e:
        print(f"TG_EXC: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
