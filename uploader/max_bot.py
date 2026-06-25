r"""
max_bot.py — Blueprint интеграции с мессенджером MAX (Модель A: приём заказов).

Поток (см. CLAUDE.md / задачу «второй канал связи MAX»):
    1. Покупатель в корзине жмёт «Отправить заказ в MAX».
    2. Витрина шлёт текст заказа POST /max/order → получает короткий id.
    3. Витрина открывает чат с ботом: https://max.ru/<bot>?start=<id>
    4. MAX присылает боту событие bot_started с payload=<id> на /max/webhook.
    5. Бот достаёт заказ по id, пересылает его ВЛАДЕЛЬЦУ (с контактом покупателя)
       и отвечает покупателю «заказ принят».

Почему короткий id, а не весь заказ в ссылке: в диплинк ?start= помещается
лишь 128 символов — заказ туда не влезает, поэтому он лежит на сервере,
а боту передаётся только id (живёт MAX_ORDER_TTL секунд).

Эндпоинты (публичные, вне секретного сегмента загрузчика):
    POST /max/order    — приём заказа от витрины (с CORS), возвращает {id}
    POST /max/webhook  — приём событий MAX (bot_started/message_created)

Переменные окружения (в uploader/.env):
    MAX_BOT_TOKEN       — токен бота MAX (заголовок Authorization). Обязателен.
    MAX_OWNER_CHAT_ID   — chat_id владельца с ботом (куда слать заказы).
                          Узнаётся из лога bot_started при первом /start владельца.
    MAX_API_BASE        — база API (по умолч. https://platform-api2.max.ru —
                          обязательная переадресация до 19.07.2026).
    MAX_WEBHOOK_SECRET  — секрет вебхука (сверяется с X-Max-Bot-Api-Secret).
    MAX_CORS_ORIGIN     — разрешённые origin витрины через запятую (по умолч. *).
    MAX_ORDER_TTL       — время жизни заказа в секундах (по умолч. 900).
    MAX_CA_BUNDLE       — путь к доверенному CA (Минцифры) для TLS к API, если нужно.
"""

import os
import time
import json
import hmac
import logging
import secrets
import threading

import requests
from flask import Blueprint, request, jsonify, make_response

log = logging.getLogger("max_bot")

max_bp = Blueprint("max_bot", __name__)

# ── Конфигурация из окружения ──
MAX_BOT_TOKEN = os.environ.get("MAX_BOT_TOKEN", "")
MAX_OWNER_CHAT_ID = os.environ.get("MAX_OWNER_CHAT_ID", "")
MAX_API_BASE = os.environ.get("MAX_API_BASE", "https://platform-api2.max.ru").rstrip("/")
MAX_WEBHOOK_SECRET = os.environ.get("MAX_WEBHOOK_SECRET", "")
MAX_CORS_ORIGIN = os.environ.get("MAX_CORS_ORIGIN", "*")
MAX_ORDER_TTL = int(os.environ.get("MAX_ORDER_TTL", "900"))
# Путь к доверенному сертификату для TLS к API MAX (Минцифры). Пусто → системный набор.
MAX_CA_BUNDLE = os.environ.get("MAX_CA_BUNDLE", "")
_VERIFY = MAX_CA_BUNDLE if MAX_CA_BUNDLE else True

# Разрешённые origin для CORS — список из запятой
_ALLOWED_ORIGINS = [o.strip() for o in MAX_CORS_ORIGIN.split(",") if o.strip()]

# ── Временное хранилище заказов (id → текст) ──
# В памяти процесса: сервис крутится под gunicorn -w 1 (один воркер, как и
# остальная часть app.py), поэтому общий dict корректен. Заказ живёт минуты,
# переживать рестарт не обязан (TTL короткий). Замок защищает от гонок потоков.
_orders: "dict[str, tuple[str, float]]" = {}
_orders_lock = threading.Lock()


def _prune_orders() -> None:
    """Удалить просроченные заказы (ленивая очистка при каждом обращении)."""
    now = time.time()
    expired = [k for k, (_, exp) in _orders.items() if exp < now]
    for k in expired:
        _orders.pop(k, None)


def _store_order(text: str) -> str:
    """Сохранить заказ, вернуть короткий id (помещается в ?start=, ≤128 симв.)."""
    order_id = secrets.token_urlsafe(8)  # ~11 символов
    with _orders_lock:
        _prune_orders()
        _orders[order_id] = (text, time.time() + MAX_ORDER_TTL)
    return order_id


def _pop_order(order_id: str) -> "str | None":
    """Забрать заказ по id (одноразово) и удалить его из хранилища."""
    with _orders_lock:
        _prune_orders()
        item = _orders.pop(order_id, None)
    return item[0] if item else None


# ── Вызовы MAX Bot API ──

def max_send(chat_id, text: str) -> bool:
    """Отправить текстовое сообщение в чат MAX. Возвращает True при успехе.

    Авторизация — токен в заголовке Authorization. Для совместимости с разными
    версиями API дублируем токен и в query-параметре access_token (лишний
    параметр безвреден, если сервер его игнорирует).
    """
    if not MAX_BOT_TOKEN:
        log.error("MAX_BOT_TOKEN не задан — отправка невозможна")
        return False
    url = f"{MAX_API_BASE}/messages"
    try:
        resp = requests.post(
            url,
            params={"chat_id": chat_id, "access_token": MAX_BOT_TOKEN},
            headers={"Authorization": MAX_BOT_TOKEN},
            json={"text": text},
            timeout=20,
            verify=_VERIFY,
        )
        if resp.status_code // 100 != 2:
            log.warning("MAX /messages вернул %s: %s", resp.status_code, resp.text[:300])
            return False
        return True
    except requests.RequestException as e:
        log.warning("Ошибка отправки в MAX: %s", e)
        return False


# ── CORS (витрина дёргает /max/order с другого домена) ──

def _cors_origin() -> str:
    """Подобрать значение заголовка Access-Control-Allow-Origin под запрос."""
    origin = request.headers.get("Origin", "")
    if "*" in _ALLOWED_ORIGINS:
        return "*"
    if origin in _ALLOWED_ORIGINS:
        return origin
    return _ALLOWED_ORIGINS[0] if _ALLOWED_ORIGINS else "*"


@max_bp.after_request
def _add_cors(resp):
    """Добавить CORS-заголовки ко всем ответам blueprint'а."""
    resp.headers["Access-Control-Allow-Origin"] = _cors_origin()
    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Max-Age"] = "86400"
    return resp


# ── Маршрут приёма заказа от витрины ──

@max_bp.route("/max/order", methods=["POST", "OPTIONS"])
def max_order():
    # Предзапрос CORS — браузер шлёт OPTIONS перед POST с JSON-телом
    if request.method == "OPTIONS":
        return make_response("", 204)

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify(ok=False, message="Пустой заказ"), 400
    # Защита от слишком больших тел (заказ — это короткий список позиций)
    if len(text) > 4000:
        text = text[:4000]

    order_id = _store_order(text)
    log.info("Принят заказ MAX id=%s (%d симв.)", order_id, len(text))
    return jsonify(ok=True, id=order_id)


# ── Маршрут вебхука MAX ──

def _verify_secret() -> bool:
    """Сверить секрет вебхука (если задан) с заголовком X-Max-Bot-Api-Secret."""
    if not MAX_WEBHOOK_SECRET:
        return True  # секрет не настроен — пропускаем (желательно настроить)
    got = request.headers.get("X-Max-Bot-Api-Secret", "")
    return hmac.compare_digest(got, MAX_WEBHOOK_SECRET)


def _format_customer(user: dict) -> str:
    """Строка с контактом покупателя для владельца: имя + ссылка/username/id."""
    name = (user.get("name") or "без имени").strip()
    username = user.get("username")
    if username:
        return f"👤 Покупатель: {name}\nhttps://max.ru/{username}"
    user_id = user.get("user_id", "—")
    return f"👤 Покупатель: {name} (id: {user_id})"


def _handle_started(chat_id, user: dict, payload: str) -> None:
    """Обработать вход покупателя по диплинку: доставить заказ владельцу."""
    # Лог для разовой настройки MAX_OWNER_CHAT_ID: владелец один раз жмёт /start,
    # из этого лога берём его chat_id и прописываем в окружение.
    log.info(
        "bot_started chat_id=%s user_id=%s name=%r payload=%r",
        chat_id, user.get("user_id"), user.get("name"), payload,
    )

    if not payload:
        # Вход без заказа (например, по плавающей иконке) — мягкое приветствие.
        max_send(chat_id, "Здравствуйте! Это бот каталога «Вкусный Дом». "
                          "Соберите корзину на сайте и нажмите «Отправить заказ в MAX».")
        return

    order_text = _pop_order(payload)
    if not order_text:
        # id неизвестен или заказ просрочен (TTL вышел)
        max_send(chat_id, "Ссылка на заказ устарела. Откройте корзину на сайте "
                          "и отправьте заказ заново — мы всё получим.")
        return

    # 1. Заказ владельцу — с контактом покупателя (Модель A: видим, кто заказал)
    if MAX_OWNER_CHAT_ID:
        owner_msg = f"🛒 Новый заказ через MAX\n\n{order_text}\n\n{_format_customer(user)}"
        if not max_send(MAX_OWNER_CHAT_ID, owner_msg):
            log.error("Не удалось доставить заказ владельцу (chat_id=%s)", MAX_OWNER_CHAT_ID)
    else:
        log.error("MAX_OWNER_CHAT_ID не задан — заказ %s некуда переслать", payload)

    # 2. Подтверждение покупателю
    max_send(chat_id, "Спасибо! Ваш заказ принят 🙌 Скоро свяжемся с вами.")


@max_bp.route("/max/webhook", methods=["POST", "OPTIONS"])
def max_webhook():
    if request.method == "OPTIONS":
        return make_response("", 204)

    if not _verify_secret():
        log.warning("Вебхук MAX: неверный секрет")
        return jsonify(ok=False), 403

    update = request.get_json(silent=True) or {}
    utype = update.get("update_type")

    try:
        if utype == "bot_started":
            _handle_started(
                update.get("chat_id"),
                update.get("user") or {},
                (update.get("payload") or "").strip(),
            )
        elif utype == "message_created":
            # Запасной разбор: иногда старт по диплинку приходит сообщением «/start <id>».
            msg = update.get("message") or {}
            body = msg.get("body") or {}
            text = (body.get("text") or "").strip()
            sender = (msg.get("sender") or {})
            recipient = (msg.get("recipient") or {})
            chat_id = recipient.get("chat_id")
            if text.startswith("/start"):
                parts = text.split(maxsplit=1)
                payload = parts[1].strip() if len(parts) > 1 else ""
                _handle_started(chat_id, sender, payload)
    except Exception as e:  # noqa: BLE001 — вебхук всегда отвечает 200, иначе MAX будет ретраить
        log.exception("Ошибка обработки вебхука MAX: %s", e)

    # MAX ждёт 200 в ответ, иначе повторяет доставку события
    return jsonify(ok=True)
