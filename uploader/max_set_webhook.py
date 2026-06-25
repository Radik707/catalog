r"""
max_set_webhook.py — разовая настройка вебхука бота MAX.

Регистрирует у MAX подписку на события bot_started/message_created, чтобы они
прилетали на наш /max/webhook. Запускается один раз при развёртывании и при
смене адреса вебхука.

Использование (на сервере daniella, из папки uploader, .env подхватится):
    python max_set_webhook.py set https://uploader.zhukoleg.ru/max/webhook
    python max_set_webhook.py list      # показать текущие подписки
    python max_set_webhook.py delete https://uploader.zhukoleg.ru/max/webhook
    python max_set_webhook.py info       # сведения о боте (проверка токена)

Переменные окружения (uploader/.env):
    MAX_BOT_TOKEN       — токен бота (обязателен)
    MAX_API_BASE        — база API (по умолч. https://platform-api2.max.ru)
    MAX_WEBHOOK_SECRET  — секрет, который MAX будет слать в X-Max-Bot-Api-Secret
    MAX_CA_BUNDLE       — путь к доверенному CA (Минцифры) для TLS, если нужно
"""

import os
import sys

import requests


def load_env() -> None:
    """Простейшая загрузка .env рядом со скриптом (как в app.py)."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


load_env()

TOKEN = os.environ.get("MAX_BOT_TOKEN", "")
BASE = os.environ.get("MAX_API_BASE", "https://platform-api2.max.ru").rstrip("/")
SECRET = os.environ.get("MAX_WEBHOOK_SECRET", "")
CA = os.environ.get("MAX_CA_BUNDLE", "")
VERIFY = CA if CA else True

# Токен дублируем и в заголовке, и в query — для совместимости версий API
HEADERS = {"Authorization": TOKEN}
AUTH_PARAM = {"access_token": TOKEN}


def _check_token() -> None:
    if not TOKEN:
        print("Ошибка: не задан MAX_BOT_TOKEN (см. uploader/.env)")
        sys.exit(1)


def info() -> None:
    """Сведения о боте — заодно проверка валидности токена и доступности API."""
    r = requests.get(f"{BASE}/me", params=AUTH_PARAM, headers=HEADERS, timeout=20, verify=VERIFY)
    print(r.status_code, r.text)


def list_subs() -> None:
    r = requests.get(f"{BASE}/subscriptions", params=AUTH_PARAM, headers=HEADERS, timeout=20, verify=VERIFY)
    print(r.status_code, r.text)


def set_sub(url: str) -> None:
    body = {
        "url": url,
        "update_types": ["bot_started", "message_created", "message_callback"],
    }
    if SECRET:
        body["secret"] = SECRET
    r = requests.post(
        f"{BASE}/subscriptions", params=AUTH_PARAM, headers=HEADERS,
        json=body, timeout=20, verify=VERIFY,
    )
    print(r.status_code, r.text)


def delete_sub(url: str) -> None:
    r = requests.delete(
        f"{BASE}/subscriptions", params={**AUTH_PARAM, "url": url},
        headers=HEADERS, timeout=20, verify=VERIFY,
    )
    print(r.status_code, r.text)


def main() -> None:
    _check_token()
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)
    cmd = args[0]
    if cmd == "info":
        info()
    elif cmd == "list":
        list_subs()
    elif cmd == "set" and len(args) >= 2:
        set_sub(args[1])
    elif cmd == "delete" and len(args) >= 2:
        delete_sub(args[1])
    else:
        print("Неизвестная команда. См. справку:")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
