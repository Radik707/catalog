# Telegram-бот администратора каталога

Уведомляет владельца об итогах обновления каталога и даёт кнопки решения при
проблемах. Работает в паре с веб-загрузчиком (`uploader/`).

## Что делает
- Веб-загрузчик (`uploader/app.py`) при обновлении сам отправляет владельцу
  сообщение через `scripts/notify_tg.py`:
  - ✅ успех: «Каталог обновлён: N товаров»;
  - ⚠️ подозрительно мало товаров: вернул прошлую версию + кнопки
    **[Оставить прошлую] [Всё равно применить] [Показать файлы]**;
  - ❌ ошибка разбора: вернул прошлую версию + кнопка **[Показать файлы]**.
- `admin_bot.py` (этот сервис) слушает нажатия кнопок (long polling) и выполняет:
  - keep → `sheet_tool.py drop_new` (оставить прошлую);
  - apply → `sheet_tool.py apply_new` (применить отложенную новую);
  - files → присылает .xlsx из `LAST_BATCH_DIR` в чат.
- Слушает только владельца (`OWNER_CHAT_ID`).

## Связь и прокси
- Telegram в РФ ограничен → и `admin_bot.py`, и `notify_tg.py` ходят к
  `api.telegram.org` через `TG_PROXY` (SOCKS, напр. `socks5h://127.0.0.1:1080`).
- Запросы к Google (sheet_tool) идут НАПРЯМУЮ (admin_bot снимает proxy-переменные
  перед запуском sheet_tool).
- Нужен `PySocks` в venv (уже в `uploader/requirements.txt`).

## Развёртывание (для @sysadmin)
Использует тот же venv и `uploader/.env`, что и загрузчик.

1. Зависимости (если ещё нет): `/opt/apps/catalog/.venv/bin/pip install -r uploader/requirements.txt` (добавился PySocks).
2. В `uploader/.env` заполнить: `TELEGRAM_TOKEN`, `TG_PROXY`, `LAST_BATCH_DIR`, `WARN_RATIO`, и `OWNER_CHAT_ID` (см. ниже).
3. Узнать `OWNER_CHAT_ID`: запустить бота с `OWNER_CHAT_ID=0`, владелец пишет боту `/start` → в логах/ответе появится его id → вписать в `.env` → перезапустить.

### systemd-служба
`/etc/systemd/system/catalog-admin-bot.service`:
```ini
[Unit]
Description=Catalog admin Telegram bot
After=network-online.target

[Service]
WorkingDirectory=/opt/apps/catalog/admin_bot
EnvironmentFile=/opt/apps/catalog/uploader/.env
ExecStart=/opt/apps/catalog/.venv/bin/python /opt/apps/catalog/admin_bot/admin_bot.py
Restart=always
RestartSec=5
User=admin

[Install]
WantedBy=multi-user.target
```
> ВАЖНО: НЕ задавать `https_proxy`/`http_proxy` в Environment этого юнита —
> иначе sheet_tool (Google) пойдёт через прокси и упадёт (Missing SOCKS / лишний хоп).
> Прокси к Telegram задаётся ТОЛЬКО через `TG_PROXY` и применяется в коде явно.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now catalog-admin-bot
journalctl -u catalog-admin-bot -f
```

## Обновление
`git pull` → `sudo systemctl restart catalog-admin-bot catalog-uploader`.
