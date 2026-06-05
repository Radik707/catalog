r"""
vk_bot.py — VK-бот обновления каталога.

Назначение: принимает от владельца 3 Excel-файла (прайсы), складывает их в папку,
и по нажатию кнопки «Обновить каталог» запускает scripts/upload.py, который
заливает данные в Google Sheet. Сайт на Vercel читает таблицу вживую и
обновляется сам.

Доступ строго у одного человека — проверка по VK from_id (белый список).

Запуск:
    python vk_bot.py

Настройка — через переменные окружения (.env рядом со скриптом или системные):
    VK_GROUP_TOKEN   — ключ доступа сообщества VK (секрет!)
    ALLOWED_VK_ID    — числовой VK-id владельца (кто может управлять ботом).
                       Если не задан (0) — бот никого не пускает, но в ответ
                       сообщает отправителю его id (чтобы узнать свой id при настройке).
    INCOMING_DIR     — папка для входящих .xlsx (по умолч. ./price)
    UPLOAD_SCRIPT    — путь к upload.py (по умолч. ../scripts/upload.py относительно бота)
    PYTHON_BIN       — интерпретатор для запуска upload.py (по умолч. текущий)
    UPLOAD_TIMEOUT   — таймаут запуска upload.py в секундах (по умолч. 600)
"""

import os
import re
import sys
import glob
import logging
import subprocess
from pathlib import Path

import requests
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id

# --- Логирование ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("vk_bot")

# --- Пути ---
SCRIPT_DIR = Path(__file__).resolve().parent


def load_env() -> None:
    """Простая загрузка .env (без сторонних пакетов): ключ=значение построчно."""
    env_path = SCRIPT_DIR / ".env"
    if not env_path.exists():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


load_env()

VK_GROUP_TOKEN = os.environ.get("VK_GROUP_TOKEN", "")
ALLOWED_VK_ID = int(os.environ.get("ALLOWED_VK_ID", "0") or "0")
INCOMING_DIR = Path(os.environ.get("INCOMING_DIR", str(SCRIPT_DIR / "price")))
UPLOAD_SCRIPT = Path(
    os.environ.get("UPLOAD_SCRIPT", str(SCRIPT_DIR.parent / "scripts" / "upload.py"))
)
PYTHON_BIN = os.environ.get("PYTHON_BIN", sys.executable)
UPLOAD_TIMEOUT = int(os.environ.get("UPLOAD_TIMEOUT", "600"))


def sanitize_filename(name: str) -> str:
    """Убрать из имени файла всё лишнее, оставить безопасное имя .xlsx."""
    name = os.path.basename(name or "file.xlsx")
    name = re.sub(r"[^\w.\-() ]+", "_", name, flags=re.UNICODE).strip()
    if not name.lower().endswith(".xlsx"):
        name += ".xlsx"
    return name or "file.xlsx"


def unique_path(folder: Path, filename: str) -> Path:
    """Вернуть несуществующий путь, добавляя (1), (2)… при совпадении имён."""
    candidate = folder / filename
    if not candidate.exists():
        return candidate
    stem, ext = os.path.splitext(filename)
    i = 1
    while (folder / f"{stem} ({i}){ext}").exists():
        i += 1
    return folder / f"{stem} ({i}){ext}"


def build_keyboard() -> str:
    """Клавиатура с кнопками «Обновить каталог» и «Очистить»."""
    kb = VkKeyboard(one_time=False)
    kb.add_button("🔄 Обновить каталог", color=VkKeyboardColor.POSITIVE,
                  payload={"cmd": "update"})
    kb.add_line()
    kb.add_button("🗑 Очистить", color=VkKeyboardColor.NEGATIVE,
                  payload={"cmd": "clear"})
    return kb.get_keyboard()


def list_xlsx() -> list[Path]:
    """Список .xlsx в папке входящих."""
    return [Path(p) for p in sorted(glob.glob(str(INCOMING_DIR / "*.xlsx")))]


def clear_incoming() -> int:
    """Удалить все .xlsx из папки входящих. Вернуть число удалённых."""
    files = list_xlsx()
    for f in files:
        try:
            f.unlink()
        except OSError as e:
            log.warning("Не удалось удалить %s: %s", f, e)
    return len(files)


def run_upload() -> tuple[bool, str]:
    """Запустить upload.py на папке входящих. Вернуть (успех, текст_ответа)."""
    if not UPLOAD_SCRIPT.exists():
        return False, f"Скрипт не найден: {UPLOAD_SCRIPT}"

    log.info("Запуск upload.py на папке %s", INCOMING_DIR)
    try:
        proc = subprocess.run(
            [PYTHON_BIN, str(UPLOAD_SCRIPT), "--path", str(INCOMING_DIR)],
            cwd=str(UPLOAD_SCRIPT.parent),  # чтобы нашлись category_map.json и т.п.
            capture_output=True,
            text=True,
            timeout=UPLOAD_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return False, "Обновление прервано по таймауту."

    output = (proc.stdout or "") + (proc.stderr or "")

    if proc.returncode != 0:
        tail = "\n".join(output.strip().splitlines()[-8:])
        return False, f"Ошибка при обновлении:\n{tail}"

    # Пытаемся вытащить число загруженных товаров из лога upload.py
    m = re.search(r"Загружено (\d+) товаров", output)
    count = m.group(1) if m else "?"
    return True, f"Готово ✅ Загружено товаров: {count}. Сайт обновится за минуту."


class Bot:
    """Обёртка VK-бота: один владелец, приём .xlsx, запуск обновления по кнопке."""

    def __init__(self, token: str):
        self.session = vk_api.VkApi(token=token)
        self.api = self.session.get_api()
        # Узнаём id своего сообщества по токену
        self.group_id = self.api.groups.getById()[0]["id"]
        self.longpoll = VkBotLongPoll(self.session, self.group_id)
        INCOMING_DIR.mkdir(parents=True, exist_ok=True)

    def send(self, peer_id: int, text: str, with_keyboard: bool = True) -> None:
        params = {"peer_id": peer_id, "message": text, "random_id": get_random_id()}
        if with_keyboard:
            params["keyboard"] = build_keyboard()
        self.api.messages.send(**params)

    def download_doc(self, doc: dict) -> Path | None:
        """Скачать документ-вложение в папку входящих. Вернуть путь или None."""
        url = doc.get("url")
        title = sanitize_filename(doc.get("title", "file.xlsx"))
        ext = (doc.get("ext") or "").lower()
        if ext and ext != "xlsx":
            return None  # принимаем только Excel .xlsx
        if not url:
            return None
        dest = unique_path(INCOMING_DIR, title)
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        dest.write_bytes(r.content)
        log.info("Сохранён файл: %s (%d байт)", dest.name, len(r.content))
        return dest

    def handle_message(self, message: dict) -> None:
        from_id = message.get("from_id")
        text = (message.get("text") or "").strip().lower()
        payload = message.get("payload")  # JSON-строка от кнопки
        attachments = message.get("attachments", []) or []

        # --- Белый список: реагируем только на владельца ---
        if ALLOWED_VK_ID == 0:
            # id ещё не настроен — помогаем узнать свой id
            self.send(from_id, f"Бот ещё настраивается. Твой VK-id: {from_id}",
                      with_keyboard=False)
            log.info("ALLOWED_VK_ID не задан. Отправитель from_id=%s", from_id)
            return
        if from_id != ALLOWED_VK_ID:
            self.send(from_id, "Этот бот приватный.", with_keyboard=False)
            return

        # --- Команда из payload кнопки или текста ---
        cmd = ""
        if payload:
            try:
                import json
                cmd = (json.loads(payload) or {}).get("cmd", "")
            except (ValueError, TypeError):
                cmd = ""
        if not cmd:
            if "обнов" in text:
                cmd = "update"
            elif "очист" in text:
                cmd = "clear"

        if cmd == "update":
            files = list_xlsx()
            if not files:
                self.send(from_id, "Нет файлов для обновления. Пришли Excel-прайсы.")
                return
            self.send(from_id, f"Запускаю обновление по {len(files)} файлам…",
                      with_keyboard=False)
            ok, reply = run_upload()
            if ok:
                clear_incoming()  # после успешного прогона чистим папку для нового набора
            self.send(from_id, reply)
            return

        if cmd == "clear":
            n = clear_incoming()
            self.send(from_id, f"Очищено файлов: {n}.")
            return

        # --- Приём файлов-вложений ---
        saved, skipped = 0, 0
        for att in attachments:
            if att.get("type") == "doc" and att.get("doc"):
                try:
                    if self.download_doc(att["doc"]):
                        saved += 1
                    else:
                        skipped += 1
                except requests.RequestException as e:
                    log.warning("Ошибка скачивания файла: %s", e)
                    skipped += 1

        if saved:
            queue = len(list_xlsx())
            msg = f"Принял файлов: {saved}. Всего в очереди: {queue}.\n"
            if skipped:
                msg += f"Пропущено (не .xlsx): {skipped}.\n"
            msg += "Когда пришлёшь все — нажми «Обновить каталог»."
            self.send(from_id, msg)
        elif attachments:
            self.send(from_id, "Не нашёл .xlsx во вложениях. Пришли Excel-файл (.xlsx).")
        else:
            # Просто текст без команды — показываем подсказку с кнопками
            self.send(
                from_id,
                "Пришли Excel-прайсы (.xlsx), затем нажми «Обновить каталог».",
            )

    def run(self) -> None:
        log.info("Бот запущен. Сообщество id=%s, владелец id=%s, папка=%s",
                 self.group_id, ALLOWED_VK_ID or "(не задан)", INCOMING_DIR)
        for event in self.longpoll.listen():
            if event.type != VkBotEventType.MESSAGE_NEW:
                continue
            # Достаём сообщение надёжно: в API 5.103+ оно вложено в object.message
            obj = event.raw.get("object", {})
            message = obj.get("message", obj)
            try:
                self.handle_message(message)
            except Exception as e:  # бот не должен падать из-за одной ошибки
                log.exception("Ошибка обработки сообщения: %s", e)


def main() -> None:
    if not VK_GROUP_TOKEN:
        log.error("Не задан VK_GROUP_TOKEN (ключ доступа сообщества). См. .env")
        sys.exit(1)
    while True:
        try:
            Bot(VK_GROUP_TOKEN).run()
        except Exception as e:
            # Перезапуск цикла при обрыве long poll / сети
            log.exception("Сбой long poll, перезапуск через 5 c: %s", e)
            import time
            time.sleep(5)


if __name__ == "__main__":
    main()
