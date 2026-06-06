r"""
app.py — Веб-страница загрузки прайсов и обновления каталога.

Назначение: оператор открывает секретную ссылку, загружает Excel-файлы
(по одному или вместе), затем жмёт «Обновить каталог». Сервер запускает
scripts/upload.py, который заливает данные в Google Sheet. Сайт на Vercel
читает таблицу вживую и обновляется сам.

Доступ — по секретной ссылке (длинный случайный путь в URL).

Запуск (для разработки):
    python app.py
В продакшене — через gunicorn + nginx (HTTPS), см. README.md.

Настройка — через переменные окружения (.env рядом со скриптом или системные):
    APP_SECRET       — секретный сегмент в URL (длинная случайная строка). Обязателен.
    INCOMING_DIR     — папка для входящих .xlsx (по умолч. ./price)
    UPLOAD_SCRIPT    — путь к upload.py (по умолч. ../scripts/upload.py)
    PYTHON_BIN       — интерпретатор для запуска upload.py (по умолч. текущий)
    UPLOAD_TIMEOUT   — таймаут запуска upload.py в секундах (по умолч. 600)
    HOST, PORT       — адрес/порт для встроенного сервера (по умолч. 127.0.0.1:8000)
"""

import os
import re
import sys
import glob
import logging
import subprocess
from pathlib import Path

from flask import Flask, request, jsonify, abort

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("uploader")

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

APP_SECRET = os.environ.get("APP_SECRET", "")
INCOMING_DIR = Path(os.environ.get("INCOMING_DIR", str(SCRIPT_DIR / "price")))
UPLOAD_SCRIPT = Path(
    os.environ.get("UPLOAD_SCRIPT", str(SCRIPT_DIR.parent / "scripts" / "upload.py"))
)
SHEET_TOOL = UPLOAD_SCRIPT.parent / "sheet_tool.py"  # бэкап/откат каталога
PYTHON_BIN = os.environ.get("PYTHON_BIN", sys.executable)
UPLOAD_TIMEOUT = int(os.environ.get("UPLOAD_TIMEOUT", "600"))
# Архив последней партии файлов (чтобы админ мог их посмотреть в Telegram)
LAST_BATCH_DIR = Path(os.environ.get("LAST_BATCH_DIR", str(SCRIPT_DIR / "last_batch")))
NOTIFY_SCRIPT = UPLOAD_SCRIPT.parent / "notify_tg.py"  # отправка уведомлений в Telegram
WARN_RATIO = float(os.environ.get("WARN_RATIO", "0.5"))  # порог «подозрительно мало»

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # лимит загрузки 50 МБ


# ── Работа с файлами ──

def sanitize_filename(name: str) -> str:
    """Безопасное имя файла с расширением .xlsx (кириллица сохраняется)."""
    name = os.path.basename(name or "file.xlsx")
    name = re.sub(r"[^\w.\-() ]+", "_", name, flags=re.UNICODE).strip()
    if not name.lower().endswith(".xlsx"):
        name += ".xlsx"
    return name or "file.xlsx"


def unique_path(folder: Path, filename: str) -> Path:
    candidate = folder / filename
    if not candidate.exists():
        return candidate
    stem, ext = os.path.splitext(filename)
    i = 1
    while (folder / f"{stem} ({i}){ext}").exists():
        i += 1
    return folder / f"{stem} ({i}){ext}"


def list_files() -> list[str]:
    return [Path(p).name for p in sorted(glob.glob(str(INCOMING_DIR / "*.xlsx")))]


def clear_incoming() -> int:
    files = glob.glob(str(INCOMING_DIR / "*.xlsx"))
    for f in files:
        try:
            os.remove(f)
        except OSError as e:
            log.warning("Не удалось удалить %s: %s", f, e)
    return len(files)


def _run_py(script: Path, *args) -> tuple[int, str]:
    """Запустить python-скрипт, вернуть (код возврата, объединённый вывод)."""
    proc = subprocess.run(
        [PYTHON_BIN, str(script), *args],
        cwd=str(script.parent),  # чтобы нашлись category_map.json, .env и т.п.
        capture_output=True,
        text=True,
        timeout=UPLOAD_TIMEOUT,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def backup_catalog() -> tuple[bool, int | None]:
    """Резервная копия текущего каталога перед обновлением. (успех, число_строк)."""
    if not SHEET_TOOL.exists():
        return False, None
    try:
        rc, out = _run_py(SHEET_TOOL, "backup")
    except subprocess.TimeoutExpired:
        return False, None
    if rc != 0:
        log.warning("Бэкап не удался: %s", out.strip()[-300:])
        return False, None
    m = re.search(r"rows=(\d+)", out)
    return True, (int(m.group(1)) if m else None)


def rollback_catalog() -> tuple[bool, str]:
    """Откат каталога к резервной копии."""
    if not SHEET_TOOL.exists():
        return False, "Инструмент отката не найден на сервере."
    try:
        rc, out = _run_py(SHEET_TOOL, "rollback")
    except subprocess.TimeoutExpired:
        return False, "Откат прерван по таймауту."
    if "NO_BACKUP" in out:
        return False, "Нет резервной копии — откатывать не к чему (обновление ещё не делалось)."
    if rc != 0:
        tail = "\n".join(out.strip().splitlines()[-6:])
        return False, f"Ошибка отката:\n{tail}"
    m = re.search(r"rows=(\d+)", out)
    rows = m.group(1) if m else "?"
    return True, (f"Откат выполнен ✅ Восстановлена прошлая версия каталога "
                  f"({rows} товаров). Сайт вернётся к ней за минуту.")


def run_upload() -> tuple[bool, str, int | None]:
    """Запустить upload.py на папке входящих. Вернуть (успех, текст_ошибки, число_товаров)."""
    if not UPLOAD_SCRIPT.exists():
        return False, f"Скрипт не найден: {UPLOAD_SCRIPT}", None

    log.info("Запуск upload.py на папке %s", INCOMING_DIR)
    try:
        rc, output = _run_py(UPLOAD_SCRIPT, "--path", str(INCOMING_DIR))
    except subprocess.TimeoutExpired:
        return False, "Обновление прервано по таймауту.", None

    if rc != 0:
        tail = "\n".join(output.strip().splitlines()[-8:])
        return False, f"Ошибка при обновлении:\n{tail}", None

    m = re.search(r"Загружено (\d+) товаров", output)
    count = int(m.group(1)) if m else None
    return True, "", count


def stash_new() -> bool:
    """Отложить текущую (подозрительную) версию в Товары_NEW для возможного применения."""
    if not SHEET_TOOL.exists():
        return False
    try:
        rc, _ = _run_py(SHEET_TOOL, "stash_new")
        return rc == 0
    except subprocess.TimeoutExpired:
        return False


def archive_incoming() -> list[str]:
    """Переместить загруженные файлы в архив последней партии (для проверки админом).

    Очищает INCOMING_DIR (очередь) и сохраняет файлы в LAST_BATCH_DIR.
    """
    LAST_BATCH_DIR.mkdir(parents=True, exist_ok=True)
    for old in glob.glob(str(LAST_BATCH_DIR / "*.xlsx")):
        try:
            os.remove(old)
        except OSError:
            pass
    moved = []
    for f in glob.glob(str(INCOMING_DIR / "*.xlsx")):
        dest = LAST_BATCH_DIR / Path(f).name
        try:
            os.replace(f, dest)
            moved.append(dest.name)
        except OSError as e:
            log.warning("Не удалось переместить в архив %s: %s", f, e)
    return moved


def notify(mode: str, text: str) -> None:
    """Уведомление администратору в Telegram (scripts/notify_tg.py). Ошибки не критичны."""
    if not NOTIFY_SCRIPT.exists():
        return
    try:
        subprocess.run(
            [PYTHON_BIN, str(NOTIFY_SCRIPT), mode, text],
            cwd=str(NOTIFY_SCRIPT.parent),
            capture_output=True, text=True, timeout=60,
        )
    except Exception as e:  # noqa: BLE001 — уведомление не должно ронять обновление
        log.warning("Уведомление не отправлено: %s", e)


# ── Маршруты (всё под секретным сегментом /<token>) ──

def check(token: str) -> None:
    if not APP_SECRET or token != APP_SECRET:
        abort(404)


@app.get("/<token>")
def index(token: str):
    check(token)
    INCOMING_DIR.mkdir(parents=True, exist_ok=True)
    return PAGE.replace("__TOKEN__", token)


@app.get("/<token>/files")
def files(token: str):
    check(token)
    return jsonify(files=list_files())


@app.post("/<token>/upload")
def upload(token: str):
    check(token)
    INCOMING_DIR.mkdir(parents=True, exist_ok=True)
    saved, skipped = [], []
    for f in request.files.getlist("files"):
        if not f.filename:
            continue
        if not f.filename.lower().endswith(".xlsx"):
            skipped.append(f.filename)
            continue
        dest = unique_path(INCOMING_DIR, sanitize_filename(f.filename))
        f.save(str(dest))
        saved.append(dest.name)
        log.info("Загружен файл: %s", dest.name)
    return jsonify(ok=True, saved=saved, skipped=skipped, files=list_files())


@app.post("/<token>/delete")
def delete(token: str):
    check(token)
    name = sanitize_filename((request.json or {}).get("name", ""))
    target = INCOMING_DIR / name
    if target.exists():
        try:
            target.unlink()
        except OSError as e:
            return jsonify(ok=False, message=str(e)), 500
    return jsonify(ok=True, files=list_files())


@app.post("/<token>/clear")
def clear(token: str):
    check(token)
    n = clear_incoming()
    return jsonify(ok=True, message=f"Очищено файлов: {n}", files=list_files())


@app.post("/<token>/update")
def update(token: str):
    check(token)
    if not list_files():
        return jsonify(ok=False, message="Нет файлов для обновления.")

    # 1. Резервная копия ДО обновления — без страховки не рискуем.
    b_ok, b_rows = backup_catalog()
    if not b_ok:
        return jsonify(ok=False, files=list_files(), message=(
            "Не удалось сохранить резервную копию каталога — обновление отменено "
            "ради безопасности. Попробуйте ещё раз; если повторяется — сообщите."
        ))

    # 2. Само обновление.
    ok, err, count = run_upload()

    if not ok:
        # Ошибка разбора/записи: возвращаем рабочую версию, файлы — в архив для проверки.
        rollback_catalog()
        archive_incoming()
        notify("error", "❌ Обновление каталога не удалось — файлы не распознались.\n"
                        f"{err}\nВернул прошлую версию. Нажмите, чтобы посмотреть файлы.")
        return jsonify(ok=False, files=list_files(), message=(
            "Обновление не удалось — данные в файле не распознались. "
            "Каталог не изменён, администратор уведомлён."))

    # 3. Обновление прошло. Файлы — в архив (для возможной проверки админом).
    archive_incoming()
    warn = bool(count is not None and b_rows and count < b_rows * WARN_RATIO)

    if warn:
        # Подозрительно мало: откладываем новую, возвращаем прошлую, спрашиваем владельца.
        stash_new()          # Товары (новые) → Товары_NEW
        rollback_catalog()   # Товары_BACKUP (прошлые) → Товары  (на сайте — рабочая версия)
        notify("decision",
               f"⚠️ Загрузка дала {count} товаров, а было {b_rows} — это сильно меньше обычного.\n"
               "Я вернул прошлую версию каталога. Что делать?")
        return jsonify(ok=True, warn=True, files=list_files(), message=(
            f"Загрузка прошла, но товаров получилось мало ({count} вместо ~{b_rows}). "
            "На всякий случай вернул прошлую версию и отправил администратору на проверку."))

    # 4. Всё хорошо.
    notify("plain", f"✅ Каталог обновлён: {count} товаров.")
    return jsonify(ok=True, warn=False, files=list_files(), message=(
        f"Готово ✅ Загружено товаров: {count}. Прежняя версия сохранена для отката. "
        "Сайт обновится за минуту."))


@app.post("/<token>/rollback")
def rollback(token: str):
    check(token)
    ok, msg = rollback_catalog()
    return jsonify(ok=ok, message=msg, files=list_files())


# ── Страница (HTML + CSS + JS одним файлом) ──
PAGE = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Обновление каталога «Вкусный Дом»</title>
<style>
  * { box-sizing: border-box; }
  body { margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
         background:#f3f4f6; color:#111827; }
  .wrap { max-width:560px; margin:0 auto; padding:20px 16px 40px; }
  h1 { font-size:20px; margin:8px 0 4px; }
  p.sub { color:#6b7280; margin:0 0 20px; font-size:14px; }
  .drop { display:block; width:100%; margin-top:8px; border:2px dashed #9ca3af;
          border-radius:14px; background:#fff; padding:28px 16px; text-align:center;
          cursor:pointer; transition:.15s; }
  .drop.over { border-color:#2563eb; background:#eff6ff; }
  .drop strong { color:#2563eb; }
  .drop small { display:block; color:#9ca3af; margin-top:6px; }
  .files { list-style:none; padding:0; margin:16px 0; }
  .files li { display:flex; align-items:center; justify-content:space-between;
              background:#fff; border:1px solid #e5e7eb; border-radius:10px;
              padding:10px 12px; margin-bottom:8px; font-size:14px; }
  .files .x { color:#dc2626; cursor:pointer; border:none; background:none;
              font-size:18px; line-height:1; padding:0 4px; }
  .empty { color:#9ca3af; font-size:14px; text-align:center; margin:16px 0; }
  .btns { display:flex; gap:10px; margin-top:8px; }
  button.act { flex:1; border:none; border-radius:12px; padding:14px; font-size:16px;
               font-weight:600; cursor:pointer; }
  .primary { background:#2563eb; color:#fff; }
  .primary:disabled { background:#9ca3af; cursor:not-allowed; }
  .ghost { background:#fff; color:#374151; border:1px solid #d1d5db !important; flex:0 0 auto; }
  .status { margin-top:16px; padding:14px; border-radius:12px; font-size:14px;
            white-space:pre-wrap; display:none; }
  .status.ok { background:#ecfdf5; color:#065f46; display:block; }
  .status.err { background:#fef2f2; color:#991b1b; display:block; }
  .status.info { background:#eff6ff; color:#1e40af; display:block; }
  .rollback { margin-top:24px; padding-top:16px; border-top:1px solid #e5e7eb; text-align:center; }
  .rollback button { width:100%; }
  .rollback small { display:block; color:#9ca3af; margin-top:8px; font-size:13px; }
  .danger { background:#fff; color:#b91c1c; border:1px solid #fca5a5 !important; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Обновление каталога «Вкусный Дом»</h1>
  <p class="sub">Загрузите Excel-прайсы (.xlsx) — по одному или сразу несколько — и нажмите «Обновить каталог».</p>

  <label class="drop" id="drop">
    <strong>Нажмите, чтобы выбрать файлы</strong>
    <small>или перетащите .xlsx сюда</small>
    <input id="input" type="file" accept=".xlsx" multiple hidden>
  </label>

  <ul class="files" id="list"></ul>
  <div class="empty" id="empty">Файлы ещё не загружены</div>

  <div class="btns">
    <button class="act primary" id="update">Обновить каталог</button>
    <button class="act ghost" id="clear">Очистить</button>
  </div>

  <div class="status" id="status"></div>

  <div class="rollback">
    <button class="act danger" id="rollback">↩ Откатить к прошлой версии</button>
    <small>Если каталог обновился неправильно — вернуть как было до последней загрузки.</small>
  </div>
</div>

<script>
const TOKEN = "__TOKEN__";
const $ = (id) => document.getElementById(id);
const drop = $("drop"), input = $("input"), list = $("list"),
      empty = $("empty"), status = $("status"),
      updateBtn = $("update"), clearBtn = $("clear");

function show(kind, text) {
  status.className = "status " + kind;
  status.textContent = text;
}
function render(files) {
  list.innerHTML = "";
  empty.style.display = files.length ? "none" : "block";
  updateBtn.disabled = files.length === 0;
  files.forEach(name => {
    const li = document.createElement("li");
    const span = document.createElement("span");
    span.textContent = "📄 " + name;
    const x = document.createElement("button");
    x.className = "x"; x.textContent = "✕"; x.title = "Удалить";
    x.onclick = () => del(name);
    li.appendChild(span); li.appendChild(x);
    list.appendChild(li);
  });
}
async function refresh() {
  const r = await fetch(`/${TOKEN}/files`);
  render((await r.json()).files);
}
async function del(name) {
  const r = await fetch(`/${TOKEN}/delete`, {
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({name})
  });
  render((await r.json()).files);
}
async function uploadFiles(fileList) {
  if (!fileList.length) return;
  const fd = new FormData();
  for (const f of fileList) fd.append("files", f);
  show("info", "Загрузка файлов…");
  try {
    const r = await fetch(`/${TOKEN}/upload`, { method:"POST", body: fd });
    const d = await r.json();
    render(d.files);
    let msg = `Загружено: ${d.saved.length}.`;
    if (d.skipped.length) msg += ` Пропущено (не .xlsx): ${d.skipped.length}.`;
    show("info", msg);
  } catch (e) {
    show("err", "Ошибка загрузки. Попробуйте ещё раз.");
  }
}

input.onchange = () => { uploadFiles(input.files); input.value = ""; };
["dragenter","dragover"].forEach(ev => drop.addEventListener(ev, e => {
  e.preventDefault(); drop.classList.add("over");
}));
["dragleave","drop"].forEach(ev => drop.addEventListener(ev, e => {
  e.preventDefault(); drop.classList.remove("over");
}));
drop.addEventListener("drop", e => uploadFiles(e.dataTransfer.files));

updateBtn.onclick = async () => {
  updateBtn.disabled = true;
  show("info", "Обновляю каталог, подождите…");
  try {
    const r = await fetch(`/${TOKEN}/update`, { method:"POST" });
    const d = await r.json();
    // Если успех, но есть предупреждение (мало товаров) — показываем тревожным цветом
    show(d.ok ? (d.warn ? "err" : "ok") : "err", d.message);
    render(d.files);
  } catch (e) {
    show("err", "Не удалось запустить обновление.");
  }
  updateBtn.disabled = false;
};
$("rollback").onclick = async () => {
  if (!confirm("Откатить каталог к прошлой версии (до последней загрузки)?")) return;
  show("info", "Откатываю каталог…");
  try {
    const r = await fetch(`/${TOKEN}/rollback`, { method:"POST" });
    const d = await r.json();
    show(d.ok ? "ok" : "err", d.message);
    render(d.files);
  } catch (e) {
    show("err", "Не удалось выполнить откат.");
  }
};
clearBtn.onclick = async () => {
  const r = await fetch(`/${TOKEN}/clear`, { method:"POST" });
  const d = await r.json();
  render(d.files);
  show("info", d.message);
};

refresh();
</script>
</body>
</html>"""


def main() -> None:
    if not APP_SECRET:
        log.error("Не задан APP_SECRET (секрет в URL). См. .env")
        sys.exit(1)
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    INCOMING_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Страница загрузки: http://%s:%s/%s", host, port, APP_SECRET)
    app.run(host=host, port=port)


if __name__ == "__main__":
    main()
