# VK-бот обновления каталога

Принимает Excel-прайсы в личке VK-сообщества от владельца и по кнопке
«Обновить каталог» запускает `scripts/upload.py` (заливка в Google Sheet).
Сайт на Vercel читает таблицу вживую и обновляется сам.

## Как это работает
1. Владелец шлёт боту 1–3 файла `.xlsx`.
2. Бот проверяет, что отправитель — это владелец (по VK `from_id`), и сохраняет файлы в `INCOMING_DIR`.
3. Владелец жмёт кнопку **«Обновить каталог»**.
4. Бот запускает `upload.py --path INCOMING_DIR`, отвечает результатом и очищает папку при успехе.

## Что нужно от владельца (настройка VK)
1. Создать VK-сообщество (можно приватное).
2. Управление → Настройки → **Сообщения** → включить сообщения сообщества.
3. Управление → Настройки → **Работа с API**:
   - **Ключи доступа** → создать ключ с правами: управление, сообщения, документы → это `VK_GROUP_TOKEN`.
   - **Long Poll API** → включить, выбрать последнюю версию; в «Типы событий» включить **«Входящие сообщения»**.
4. Узнать свой числовой VK-id: запустить бота с `ALLOWED_VK_ID=0`, написать боту сообщение — он ответит твоим id; вписать его в `.env`.

## Развёртывание на сервере (для @sysadmin)
Связь — **VK Bots Long Poll** (исходящие запросы, публичный endpoint НЕ нужен).

```bash
# 1. Клонировать репозиторий (в нём bot/ и scripts/ с JSON-привязками)
git clone <repo> /srv/catalog
cd /srv/catalog

# 2. Виртуальное окружение и зависимости
python3 -m venv .venv
.venv/bin/pip install -r bot/requirements.txt

# 3. Секреты — ВРУЧНУЮ, не из git:
#    - bot/.env       (из bot/.env.example, заполнить VK_GROUP_TOKEN, ALLOWED_VK_ID)
#    - scripts/.env   (GOOGLE_SHEETS_ID, GOOGLE_CREDENTIALS_PATH)
#    - scripts/credentials.json  (ключ сервисного аккаунта Google)

# 4. Проверить запуск
.venv/bin/python bot/vk_bot.py
```

В `bot/.env` указать `PYTHON_BIN=/srv/catalog/.venv/bin/python`, чтобы upload.py
запускался в том же окружении (с openpyxl/gspread/google-auth).

### systemd-служба (автозапуск 24/7)
`/etc/systemd/system/catalog-bot.service`:
```ini
[Unit]
Description=VK catalog update bot
After=network-online.target

[Service]
WorkingDirectory=/srv/catalog/bot
ExecStart=/srv/catalog/.venv/bin/python /srv/catalog/bot/vk_bot.py
Restart=always
RestartSec=5
User=catalog

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now catalog-bot
journalctl -u catalog-bot -f   # логи
```

## Обновление JSON-привязок / кода
Когда меняются `scripts/*.json` или код бота — на сервере `git pull` и
`sudo systemctl restart catalog-bot`.

## Безопасность
- Бот реагирует только на `ALLOWED_VK_ID`. Остальным отвечает «приватный».
- Секреты (`.env`, `credentials.json`) — только на сервере, не в git.
