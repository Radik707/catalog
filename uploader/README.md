# Веб-загрузчик прайсов (обновление каталога)

Маленькое веб-приложение: оператор открывает секретную ссылку, загружает
Excel-прайсы (.xlsx) — по одному или вместе — и жмёт «Обновить каталог».
Сервер запускает `scripts/upload.py`, тот заливает данные в Google Sheet.
Сайт на Vercel читает таблицу вживую и обновляется сам.

## Как работает
1. Оператор открывает `https://<домен>/<APP_SECRET>`.
2. Загружает файлы (накапливаются на сервере; лишние можно удалить «✕»).
3. Жмёт **«Обновить каталог»** → запускается `upload.py` → показывается результат.
4. После успеха папка очищается под следующий набор.

Доступ — по секретной ссылке (длинный случайный `APP_SECRET` в URL). При желании
позже можно добавить пароль/Basic-Auth на nginx.

## Развёртывание на сервере (для @sysadmin)
Нужен публичный HTTPS на домене Олега → nginx (TLS) проксирует на gunicorn.

```bash
# 1. Клонировать репозиторий (в нём uploader/ и scripts/ с JSON-привязками)
git clone <repo> /srv/catalog
cd /srv/catalog

# 2. venv и зависимости
python3 -m venv .venv
.venv/bin/pip install -r uploader/requirements.txt

# 3. Секреты — ВРУЧНУЮ, не из git:
#    - uploader/.env  (из uploader/.env.example; задать APP_SECRET, пути)
#    - scripts/.env   (GOOGLE_SHEETS_ID, GOOGLE_CREDENTIALS_PATH)
#    - scripts/credentials.json  (ключ сервисного аккаунта Google)

# 4. Сгенерировать секрет:
python3 -c "import secrets; print(secrets.token_urlsafe(24))"

# 5. Проверить запуск
.venv/bin/python uploader/app.py   # отдаст ссылку http://127.0.0.1:8000/<secret>
```

### gunicorn + systemd
`/etc/systemd/system/catalog-uploader.service`:
```ini
[Unit]
Description=Catalog uploader (Flask)
After=network-online.target

[Service]
WorkingDirectory=/srv/catalog/uploader
EnvironmentFile=/srv/catalog/uploader/.env
ExecStart=/srv/catalog/.venv/bin/gunicorn -w 1 -b 127.0.0.1:8000 app:app
Restart=always
RestartSec=5
User=catalog

[Install]
WantedBy=multi-user.target
```
> `-w 1` (один воркер) — чтобы запуск upload.py не шёл параллельно сам с собой.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now catalog-uploader
journalctl -u catalog-uploader -f
```

### nginx (TLS, проксирование)
```nginx
server {
    listen 443 ssl;
    server_name uploader.example.com;        # домен Олега
    ssl_certificate     /path/fullchain.pem;
    ssl_certificate_key /path/privkey.pem;

    client_max_body_size 50m;                 # под загрузку файлов

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
    }
}
```

## Обновление кода / JSON-привязок
`git pull` на сервере → `sudo systemctl restart catalog-uploader`.

## Безопасность
- Доступ только по секретной ссылке (`APP_SECRET`). Ссылку давать оператору лично.
- Принимаются только `.xlsx`, лимит загрузки 50 МБ.
- Секреты (`.env`, `credentials.json`) — только на сервере, не в git.
- Опционально: добавить Basic-Auth на nginx как второй рубеж.
