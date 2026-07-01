r"""
max_bot.py — Blueprint интеграции с мессенджером MAX (Модель A: приём заказов).

Поток:
    1. Покупатель в корзине жмёт «Отправить заказ в MAX».
    2. Витрина шлёт POST /max/order {text, catalog_url} → получает короткий id.
    3. Витрина открывает чат с ботом: https://max.ru/<bot>?start=<id>
    4. MAX присылает боту bot_started с payload=<id> на /max/webhook.
    5. Бот пересылает заказ ВЛАДЕЛЬЦУ (с контактом покупателя) и отвечает покупателю
       подтверждением с инлайн-кнопками: Редактировать / Отменить / Написать агенту / В каталог.
    6. Нажатия на кнопки приходят событием message_callback → обрабатываем
       (отмена с подтверждением, уведомление владельцу).

Мост прайсов: оператор из allowlist (MAX_UPLOAD_CHAT_IDS) шлёт боту .xlsx →
бот скачивает их в очередь загрузчика и показывает кнопку «Обновить каталог» →
по нажатию запускается ТОТ ЖЕ безопасный конвейер, что и на сайте (app.py:
бэкап → upload.py → откат при подозрительно малом числе товаров), итог уходит
оператору в MAX. Приём файлов от посторонних отклоняется.

Почему короткий id, а не весь заказ в ссылке: в диплинк ?start= помещается лишь
128 символов. Заказ лежит на сервере (живёт MAX_ORDER_TTL секунд), боту идёт только id.

Эндпоинты (публичные, вне секретного сегмента загрузчика):
    POST /max/order    — приём заказа от витрины (CORS), возвращает {id}
    POST /max/webhook  — приём событий MAX (bot_started / message_created / message_callback)

Переменные окружения (uploader/.env):
    MAX_BOT_TOKEN          — токен бота MAX (заголовок Authorization). Обязателен.
    MAX_OWNER_CHAT_ID      — chat_id владельца с ботом (куда слать заказы).
    MAX_OWNER_PROFILE_URL  — ссылка на профиль владельца в MAX (для кнопки «Написать агенту»).
                             Если пусто — кнопка не показывается.
    MAX_API_BASE           — база API (по умолч. https://platform-api2.max.ru).
    MAX_WEBHOOK_SECRET     — секрет вебхука (сверяется с X-Max-Bot-Api-Secret).
    MAX_CORS_ORIGIN        — разрешённые origin витрины через запятую (по умолч. *).
    MAX_UPLOAD_CHAT_IDS    — chat_id операторов, кому разрешено слать прайсы (через запятую).
                             Владелец (MAX_OWNER_CHAT_ID) разрешён всегда.
    MAX_ORDER_TTL          — время жизни заказа в секундах (по умолч. 86400 — сутки,
                             чтобы кнопка «Отменить» работала какое-то время).
    MAX_CA_BUNDLE          — путь к доверенному CA (Минцифры) для TLS к API, если нужно.
"""

import os
import time
import json
import hmac
import sqlite3
import logging
import secrets
import threading
from pathlib import Path

import requests
from flask import Blueprint, request, jsonify, make_response

log = logging.getLogger("max_bot")

max_bp = Blueprint("max_bot", __name__)

# ── Конфигурация из окружения ──
MAX_BOT_TOKEN = os.environ.get("MAX_BOT_TOKEN", "")
MAX_OWNER_CHAT_ID = os.environ.get("MAX_OWNER_CHAT_ID", "")
MAX_OWNER_PROFILE_URL = os.environ.get("MAX_OWNER_PROFILE_URL", "").strip()
MAX_API_BASE = os.environ.get("MAX_API_BASE", "https://platform-api2.max.ru").rstrip("/")
MAX_WEBHOOK_SECRET = os.environ.get("MAX_WEBHOOK_SECRET", "")
MAX_CORS_ORIGIN = os.environ.get("MAX_CORS_ORIGIN", "*")
MAX_ORDER_TTL = int(os.environ.get("MAX_ORDER_TTL", "86400"))
MAX_CA_BUNDLE = os.environ.get("MAX_CA_BUNDLE", "")
_VERIFY = MAX_CA_BUNDLE if MAX_CA_BUNDLE else True

_ALLOWED_ORIGINS = [o.strip() for o in MAX_CORS_ORIGIN.split(",") if o.strip()]

# Кто может присылать боту прайсы (запускать обновление каталога) — allowlist chat_id.
# Владелец разрешён всегда; операторов добавляем в MAX_UPLOAD_CHAT_IDS (через запятую).
MAX_UPLOAD_CHAT_IDS = {x.strip() for x in os.environ.get("MAX_UPLOAD_CHAT_IDS", "").split(",") if x.strip()}
if MAX_OWNER_CHAT_ID:
    MAX_UPLOAD_CHAT_IDS.add(MAX_OWNER_CHAT_ID)

# ── Хранилище заказов (SQLite на диске) ──
# Постоянное хранилище: заказ переживает перезапуск службы и перезагрузку сервера
# (раньше был dict в памяти — рестарт терял заказы, и старт со старым id давал
# «ссылка устарела»). Заказ хранится со статусом для «Отменить» и однократной
# доставки владельцу. state: "pending" → "delivered" → "cancelled".
MAX_DB_PATH = os.environ.get("MAX_DB_PATH", str(Path(__file__).resolve().parent / "max_orders.db"))
_db_lock = threading.Lock()  # сериализуем запись (gunicorn -w 1, но потоки)


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(MAX_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _db_lock, _db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                text TEXT,
                catalog_url TEXT,
                customer_chat_id TEXT,
                customer_name TEXT,
                state TEXT,
                expires REAL
            )"""
        )


_init_db()


def _store_order(text: str, catalog_url: str) -> str:
    """Сохранить заказ, вернуть короткий id (помещается в ?start=)."""
    order_id = secrets.token_urlsafe(8)
    with _db_lock, _db() as conn:
        conn.execute("DELETE FROM orders WHERE expires < ?", (time.time(),))  # чистка просроченных
        conn.execute(
            "INSERT INTO orders (id, text, catalog_url, customer_chat_id, customer_name, state, expires) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (order_id, text, catalog_url, None, None, "pending", time.time() + MAX_ORDER_TTL),
        )
    return order_id


def _get_order(order_id: str) -> "dict | None":
    with _db_lock, _db() as conn:
        conn.execute("DELETE FROM orders WHERE expires < ?", (time.time(),))
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    return dict(row) if row else None


def _update_order(order_id: str, **fields) -> None:
    """Обновить поля заказа (state, customer_*). Без полей — ничего не делает."""
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    with _db_lock, _db() as conn:
        conn.execute(f"UPDATE orders SET {cols} WHERE id = ?", (*fields.values(), order_id))


# ── Сборка инлайн-клавиатур ──

def _btn_link(text: str, url: str) -> dict:
    return {"type": "link", "text": text, "url": url}


def _btn_cb(text: str, payload: str) -> dict:
    return {"type": "callback", "text": text, "payload": payload}


def _kb(rows: list) -> dict:
    """Вложение-клавиатура MAX: type=inline_keyboard, payload.buttons = 2D-массив."""
    return {"type": "inline_keyboard", "payload": {"buttons": rows}}


def _order_keyboard(order_id: str, order: dict) -> dict:
    """Клавиатура под подтверждением заказа покупателю."""
    catalog_url = (order.get("catalog_url") or "").rstrip("/")
    cart_url = f"{catalog_url}/cart" if catalog_url else ""

    # Первый ряд: Редактировать (ссылка на корзину) + Отменить (callback)
    row1 = []
    if cart_url:
        row1.append(_btn_link("✏️ Редактировать", cart_url))
    row1.append(_btn_cb("🗑 Отменить", f"cancel:{order_id}"))

    # Второй ряд: Написать агенту (если задан профиль) + В каталог
    row2 = []
    if MAX_OWNER_PROFILE_URL:
        row2.append(_btn_link("💬 Написать агенту", MAX_OWNER_PROFILE_URL))
    if catalog_url:
        row2.append(_btn_link("🛍 В каталог", catalog_url))

    rows = [row1]
    if row2:
        rows.append(row2)
    return _kb(rows)


def _cancel_confirm_keyboard(order_id: str) -> dict:
    """Клавиатура подтверждения отмены заказа."""
    return _kb([[
        _btn_cb("✅ Да, отменить", f"cancelyes:{order_id}"),
        _btn_cb("↩️ Нет, оставить", f"cancelno:{order_id}"),
    ]])


# ── Вызовы MAX Bot API ──

def max_send(chat_id, text: str, attachments: "list | None" = None) -> bool:
    """Отправить сообщение в чат MAX (с опциональными вложениями — клавиатурой)."""
    if not MAX_BOT_TOKEN:
        log.error("MAX_BOT_TOKEN не задан — отправка невозможна")
        return False
    body: dict = {"text": text}
    if attachments:
        body["attachments"] = attachments
    try:
        resp = requests.post(
            f"{MAX_API_BASE}/messages",
            params={"chat_id": chat_id, "access_token": MAX_BOT_TOKEN},
            headers={"Authorization": MAX_BOT_TOKEN},
            json=body, timeout=20, verify=_VERIFY,
        )
        if resp.status_code // 100 != 2:
            log.warning("MAX /messages вернул %s: %s", resp.status_code, resp.text[:300])
            return False
        return True
    except requests.RequestException as e:
        log.warning("Ошибка отправки в MAX: %s", e)
        return False


def max_answer(callback_id: str, text: "str | None" = None,
               attachments: "list | None" = None,
               notification: "str | None" = None) -> bool:
    """Ответ на нажатие инлайн-кнопки (POST /answers).

    Если передан text/attachments — сообщение с кнопкой будет заменено (отредактировано).
    notification — всплывающее уведомление у нажавшего.
    """
    if not MAX_BOT_TOKEN:
        return False
    body: dict = {}
    if text is not None or attachments is not None:
        msg: dict = {"text": text or ""}
        if attachments is not None:
            msg["attachments"] = attachments
        body["message"] = msg
    if notification:
        body["notification"] = notification
    try:
        resp = requests.post(
            f"{MAX_API_BASE}/answers",
            params={"callback_id": callback_id, "access_token": MAX_BOT_TOKEN},
            headers={"Authorization": MAX_BOT_TOKEN},
            json=body, timeout=20, verify=_VERIFY,
        )
        if resp.status_code // 100 != 2:
            log.warning("MAX /answers вернул %s: %s", resp.status_code, resp.text[:300])
            return False
        return True
    except requests.RequestException as e:
        log.warning("Ошибка ответа на callback MAX: %s", e)
        return False


# ── Приём прайсов от оператора (мост загрузки каталога) ──

# Дебаунс: оператор обычно кидает 3 прайса подряд, каждый приходит отдельным
# событием. Копим пачку и через паузу шлём ОДИН ответ с одной кнопкой — иначе
# оператор видит три кнопки и путается, какую жать.
_PRICE_DEBOUNCE_SECS = float(os.environ.get("MAX_PRICE_DEBOUNCE", "5"))
_price_pending: dict = {}          # chat_id -> {saved, bad, failed, timer}
_price_lock = threading.Lock()


def _raw_filename(att: dict) -> str:
    payload = att.get("payload") or {}
    return (att.get("filename") or payload.get("filename") or att.get("name") or "").strip()


def _att_log(att: dict) -> str:
    """Краткое БЕЗОПАСНОЕ описание вложения для лога — без подписанного url и токена."""
    payload = att.get("payload") or {}
    url = payload.get("url") or ""
    return json.dumps({
        "type": att.get("type"),
        "filename": att.get("filename"),
        "size": att.get("size"),
        "fileId": payload.get("fileId"),
        "url_host": url.split("?", 1)[0] if url else "",
        "has_token": bool(payload.get("token")),
    }, ensure_ascii=False)


def _download_max_file(att: dict) -> "bytes | None":
    """Скачать присланный боту файл. Ссылка обычно в attachment.payload.url."""
    payload = att.get("payload") or {}
    url = payload.get("url") or att.get("url")
    if not url:
        log.warning("У вложения нет url для скачивания: %s", _att_log(att))
        return None
    last = None
    for params in ({}, {"access_token": MAX_BOT_TOKEN}):  # вторая попытка — с токеном
        try:
            # ВАЖНО: файловый CDN MAX (fd.oneme.ru) проверяется системным/`certifi`
            # набором CA, а НЕ бандлом Минцифры (тот нужен только для platform-api2.max.ru).
            # Поэтому здесь verify=True, иначе TLS падает с CERTIFICATE_VERIFY_FAILED.
            r = requests.get(url, params=params, timeout=60, verify=True)
            last = r.status_code
            if r.status_code // 100 == 2:
                return r.content
        except requests.RequestException as e:
            log.warning("Ошибка скачивания файла MAX: %s", e)
            return None
    log.warning("Скачивание файла MAX не удалось (код %s)", last)
    return None


def _price_keyboard(n: int) -> dict:
    """Кнопки под очередью прайсов: обновить каталог / очистить очередь."""
    return _kb([[
        _btn_cb(f"✅ Обновить каталог ({n})", "priceupdate"),
        _btn_cb("🗑 Очистить очередь", "priceclear"),
    ]])


def _flush_price(chat_id) -> None:
    """Отправить ОДИН итог по накопленной пачке прайсов (после паузы дебаунса)."""
    with _price_lock:
        st = _price_pending.pop(chat_id, None)
    if not st:
        return
    saved, bad_format, dl_failed = st["saved"], st["bad"], st["failed"]

    if saved == 0:
        reasons = []
        if bad_format:
            reasons.append(f"{bad_format} не в формате .xlsx")
        if dl_failed:
            reasons.append(f"{dl_failed} не удалось скачать")
        reason = "; ".join(reasons) or "неизвестная причина"
        max_send(chat_id, f"Не принял ни одного файла ({reason}). Пришлите прайсы .xlsx ещё раз.")
        return

    from app import list_files
    queue = list_files()
    note = f"Принял {saved} файл(ов). В очереди: {len(queue)}."
    extra = []
    if bad_format:
        extra.append(f"{bad_format} не .xlsx")
    if dl_failed:
        extra.append(f"{dl_failed} не скачались")
    if extra:
        note += " Пропущено: " + ", ".join(extra) + "."
    note += "\nКогда пришлёте все прайсы — нажмите «Обновить каталог»."
    max_send(chat_id, note, attachments=[_price_keyboard(len(queue))])


def _handle_price_files(chat_id, file_atts: list) -> None:
    """Приём прайсов: скачать в очередь; итоговый ответ с кнопкой — один на пачку (дебаунс)."""
    if str(chat_id) not in MAX_UPLOAD_CHAT_IDS:
        max_send(chat_id, "Извините, приём прайсов доступен только оператору каталога.")
        log.warning("Отклонён файл от chat_id=%s (не в allowlist загрузки)", chat_id)
        return

    # Ленивый импорт — избегаем циклической зависимости с app.py
    from app import INCOMING_DIR, sanitize_filename, unique_path

    INCOMING_DIR.mkdir(parents=True, exist_ok=True)
    saved, bad_format, dl_failed = 0, 0, 0
    for att in file_atts:
        log.info("Входящий файл MAX: %s", _att_log(att))
        fname = _raw_filename(att) or "price.xlsx"
        if not fname.lower().endswith(".xlsx"):
            bad_format += 1
            continue
        data = _download_max_file(att)
        if not data:
            dl_failed += 1
            continue
        dest = unique_path(INCOMING_DIR, sanitize_filename(fname))
        try:
            with open(dest, "wb") as f:
                f.write(data)
            saved += 1
            log.info("MAX: сохранён прайс %s (%d байт)", dest.name, len(data))
        except OSError as e:
            log.warning("Не удалось сохранить файл MAX %s: %s", fname, e)
            dl_failed += 1

    # Накопить пачку и перезапустить таймер — итог уйдёт ОДНИМ сообщением через паузу.
    # Каждый новый файл сбрасывает таймер, поэтому 3 файла подряд дадут один ответ.
    with _price_lock:
        st = _price_pending.get(chat_id)
        if st and st.get("timer"):
            st["timer"].cancel()
        if not st:
            st = {"saved": 0, "bad": 0, "failed": 0, "timer": None}
            _price_pending[chat_id] = st
        st["saved"] += saved
        st["bad"] += bad_format
        st["failed"] += dl_failed
        timer = threading.Timer(_PRICE_DEBOUNCE_SECS, _flush_price, args=[chat_id])
        timer.daemon = True
        st["timer"] = timer
        timer.start()


# ── CORS ──

def _cors_origin() -> str:
    origin = request.headers.get("Origin", "")
    if "*" in _ALLOWED_ORIGINS:
        return "*"
    if origin in _ALLOWED_ORIGINS:
        return origin
    return _ALLOWED_ORIGINS[0] if _ALLOWED_ORIGINS else "*"


@max_bp.after_request
def _add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = _cors_origin()
    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Max-Age"] = "86400"
    return resp


# ── Маршрут приёма заказа от витрины ──

@max_bp.route("/max/order", methods=["POST", "OPTIONS"])
def max_order():
    if request.method == "OPTIONS":
        return make_response("", 204)

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    catalog_url = (data.get("catalog_url") or "").strip()
    if not text:
        return jsonify(ok=False, message="Пустой заказ"), 400
    if len(text) > 4000:
        text = text[:4000]
    # Принимаем только http(s)-ссылку каталога (защита от мусора в кнопках)
    if catalog_url and not catalog_url.startswith(("http://", "https://")):
        catalog_url = ""

    order_id = _store_order(text, catalog_url)
    log.info("Принят заказ MAX id=%s (%d симв.)", order_id, len(text))
    return jsonify(ok=True, id=order_id)


# ── Логика событий ──

def _verify_secret() -> bool:
    if not MAX_WEBHOOK_SECRET:
        return True
    return hmac.compare_digest(request.headers.get("X-Max-Bot-Api-Secret", ""), MAX_WEBHOOK_SECRET)


def _format_customer(user: dict) -> str:
    """Строка с контактом покупателя для владельца: имя + ссылка/username/id."""
    name = (user.get("name") or "без имени").strip()
    username = user.get("username")
    if username:
        return f"👤 Покупатель: {name}\nhttps://max.ru/{username}"
    return f"👤 Покупатель: {name} (id: {user.get('user_id', '—')})"


def _handle_started(chat_id, user: dict, payload: str) -> None:
    """Вход покупателя по диплинку: доставить заказ владельцу + подтверждение с кнопками."""
    log.info(
        "bot_started chat_id=%s user_id=%s name=%r payload=%r",
        chat_id, user.get("user_id"), user.get("name"), payload,
    )

    if not payload:
        max_send(chat_id, "Здравствуйте! Это бот каталога «Вкусный Дом». "
                          "Соберите корзину на сайте и нажмите «Отправить заказ в MAX».")
        return

    order = _get_order(payload)
    if not order:
        max_send(chat_id, "Ссылка на заказ устарела. Откройте корзину на сайте "
                          "и отправьте заказ заново — мы всё получим.")
        return

    # Доставка владельцу — однократно (защита от повторного bot_started)
    if order["state"] == "pending":
        _update_order(
            payload,
            customer_chat_id=str(chat_id),
            customer_name=(user.get("name") or "").strip(),
            state="delivered",
        )
        if MAX_OWNER_CHAT_ID:
            owner_msg = f"🛒 Новый заказ через MAX\n\n{order['text']}\n\n{_format_customer(user)}"
            if not max_send(MAX_OWNER_CHAT_ID, owner_msg):
                log.error("Не удалось доставить заказ владельцу (chat_id=%s)", MAX_OWNER_CHAT_ID)
        else:
            log.error("MAX_OWNER_CHAT_ID не задан — заказ %s некуда переслать", payload)

    # Подтверждение покупателю с кнопками управления заказом
    max_send(
        chat_id,
        "Спасибо! Ваш заказ принят 🙌 Скоро свяжемся с вами.",
        attachments=[_order_keyboard(payload, order)],
    )


def _handle_callback(callback_id: str, payload: str, chat_id=None) -> None:
    """Обработка нажатия инлайн-кнопки."""
    action, _, order_id = payload.partition(":")

    # Кнопки прайсов (только для доверенных отправителей)
    if action in ("priceupdate", "priceclear"):
        if str(chat_id) not in MAX_UPLOAD_CHAT_IDS:
            max_answer(callback_id, notification="Недоступно")
            return
        if action == "priceupdate":
            from app import start_update_from_max
            ok, msg = start_update_from_max(chat_id)
            # Итог обработки уедет отдельным сообщением по завершении (_notify_max)
            max_answer(callback_id, text=("🔄 " + msg) if ok else msg, notification=msg)
        else:  # priceclear
            from app import clear_incoming
            n = clear_incoming()
            max_answer(callback_id, text=f"Очередь очищена (удалено файлов: {n}).", notification="Очищено")
        return

    order = _get_order(order_id)

    if action == "cancel":
        # Первый шаг отмены — спрашиваем подтверждение
        max_answer(
            callback_id,
            text="Уверены, что хотите отменить заказ?",
            attachments=[_cancel_confirm_keyboard(order_id)],
        )

    elif action == "cancelyes":
        if not order or order.get("state") == "cancelled":
            max_answer(callback_id, text="Заказ уже неактуален.", notification="Заказ не найден")
            return
        _update_order(order_id, state="cancelled")
        # Уведомляем владельца
        if MAX_OWNER_CHAT_ID:
            short = (order.get("text") or "")[:200]
            who = order.get("customer_name") or "покупатель"
            max_send(MAX_OWNER_CHAT_ID, f"❌ Покупатель ({who}) отменил заказ:\n\n{short}")
        # Правим сообщение покупателя — кнопки убираем
        max_answer(callback_id, text="Заказ отменён ✓", notification="Заказ отменён")

    elif action == "cancelno":
        # Отмена отменена — возвращаем исходное подтверждение с кнопками
        if order:
            max_answer(
                callback_id,
                text="Заказ в силе ✅",
                attachments=[_order_keyboard(order_id, order)],
                notification="Оставляем заказ",
            )
        else:
            max_answer(callback_id, text="Заказ в силе ✅", notification="Оставляем заказ")


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
        elif utype == "message_callback":
            cb = update.get("callback") or {}
            callback_id = cb.get("callback_id")
            payload = (cb.get("payload") or "").strip()
            chat_id = (update.get("message") or {}).get("recipient", {}).get("chat_id")
            if callback_id and payload:
                _handle_callback(callback_id, payload, chat_id)
        elif utype == "message_created":
            msg = update.get("message") or {}
            body = msg.get("body") or {}
            text = (body.get("text") or "").strip()
            sender = msg.get("sender") or {}
            chat_id = (msg.get("recipient") or {}).get("chat_id")
            attachments = body.get("attachments") or msg.get("attachments") or []
            # Прайсы (файлы .xlsx) от оператора → мост загрузки каталога
            file_atts = [a for a in attachments
                         if a.get("type") == "file" or _raw_filename(a).lower().endswith(".xlsx")]
            if file_atts:
                _handle_price_files(chat_id, file_atts)
            elif text.startswith("/start"):
                # Запасной разбор старта по диплинку через сообщение «/start <id>».
                parts = text.split(maxsplit=1)
                payload = parts[1].strip() if len(parts) > 1 else ""
                _handle_started(chat_id, sender, payload)
    except Exception as e:  # noqa: BLE001 — вебхук всегда отвечает 200
        log.exception("Ошибка обработки вебхука MAX: %s", e)

    return jsonify(ok=True)
