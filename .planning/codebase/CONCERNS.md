# Codebase Concerns

**Analysis Date:** 2026-06-06

---

## Tech Debt

**Деструктивная запись Google Sheet при каждом обновлении:**
- Issue: `upload_to_google_sheet()` в `scripts/upload.py` (строки 586-600) полностью очищает лист «Товары» (`worksheet.clear()`) перед записью новых данных — без транзакционной атомарности. Если скрипт упадёт после очистки, но до завершения записи, каталог окажется пустым.
- Files: `scripts/upload.py`, `scripts/sheet_tool.py`, `uploader/app.py`
- Impact: При сбое сети или таймауте во время `worksheet.update()` каталог обнуляется до следующего успешного запуска.
- Fix approach: Бэкап перед очисткой уже реализован в `uploader/app.py` через `sheet_tool.py backup`. Для скрипта, запускаемого вручную (`python scripts/upload.py`), бэкап НЕ выполняется — нужно либо добавить `sheet_tool backup` в `upload.py` напрямую, либо фиксировать в README что ручной запуск не подстрахован.

**Конфликтующие директивы кэша в API-маршруте:**
- Issue: `app/api/products/route.ts` одновременно экспортирует `dynamic = 'force-dynamic'` (отключает весь кэш) и `revalidate = 300` (ISR 5 мин). В Next.js 14 при `force-dynamic` директива `revalidate` игнорируется, но оба остаются в коде и вводят в заблуждение.
- Files: `app/api/products/route.ts`
- Impact: Нет функционального ущерба, но создаёт путаницу при диагностике задержек обновления каталога.
- Fix approach: Убрать одну из директив. Если нужен ISR — оставить `revalidate = 300` и убрать `force-dynamic`. Если нужно всегда свежие данные — оставить `force-dynamic`.

**Новый формат 1С: код добавлен, НЕ протестирован и НЕ задеплоен:**
- Issue: Функции `parse_new_format()`, `is_new_format()`, `find_header_cols()`, `load_current_groups()` и весь блок `new_format_used` в `main()` добавлены в `scripts/upload.py` (строки 170-689), но ни разу не запускались на реальных данных. Определение «нового формата» опирается на хрупкую эвристику: `price_col >= 5` (цена в 6-й колонке и правее). Если у старого формата появится непредвиденная колонка левее, детектор даст ложноположительный результат.
- Files: `scripts/upload.py` (строки 170-243, 245-291, 653-689)
- Impact: При первом запуске на реальном 1С-файле возможна неверная классификация товаров (все уйдут в «Новинки») или полная потеря групп при сбое `load_current_groups()`.
- Fix approach: Прогнать `--dry-run` с реальным 1С-файлом перед первым продакшн-запуском. Рассмотреть явный флаг `--new-format` вместо автодетекции по номеру колонки.

**Категоризация товаров нового формата 1С зависит от точного совпадения строк:**
- Issue: `load_current_groups()` читает текущий каталог из Google Sheet и строит маппинг `{normalize_name(name): group}`. Сопоставление нового товара происходит через `normalize_name()` — простой `lower()` + удаление суффикса `, <ед.>`. Если название в 1С-файле отличается даже на одно слово (аббревиатура, артикль, доп.вес), товар не найдёт группу и попадёт в «Новинки».
- Files: `scripts/upload.py` (строки 204-207, 680-688)
- Impact: При первом запуске может возникнуть большое количество ложных «Новинок», загрязняя фильтр «Новинки» реального каталога.
- Fix approach: Добавить порог схожести (например, `difflib.SequenceMatcher`) или ручную таблицу переименований аналогично `PRODUCT_OVERRIDES`.

**`@anthropic-ai/sdk` установлен в зависимостях, но не используется:**
- Issue: `package.json` содержит `"@anthropic-ai/sdk": "^0.82.0"` в `dependencies`. В Next.js/bot-коде нет ни одного `import` из `@anthropic-ai/sdk`. SDK используется только в Python-скрипте `scripts/extract_photos.py` (через `pip install anthropic`).
- Files: `package.json`
- Impact: Лишние ~5 МБ в `node_modules`, увеличивает размер бандла на Vercel, затрудняет понимание зависимостей.
- Fix approach: Убрать из `package.json`. Python-зависимость `anthropic` остаётся в `scripts/requirements.txt`.

**Жёсткий хардкод пути к Excel-файлам:**
- Issue: `DEFAULT_EXCEL_DIR = r"C:\price"` в `scripts/upload.py` (строка 40) и то же значение в `scripts/auto_match_photos.py` (строка 17) — Windows-специфичные абсолютные пути.
- Files: `scripts/upload.py`, `scripts/auto_match_photos.py`
- Impact: Скрипт не работает без изменений на Linux-сервере или при переезде папки.
- Fix approach: Уже обходится через `--path` и переменную `EXCEL_DIR` в `.env`. Для `auto_match_photos.py` — аналогично добавить аргумент.

---

## Known Bugs

**Несогласованный порог остатка между компонентами:**
- Symptoms: Товары с `stock == 1` скрыты в списке каталога (`CatalogView.tsx`, строка 54: `p.stock > 1`), но `ProductCard.tsx` (строка 81) и `AddToCartButton.tsx` (строка 15) считают тот же товар «в наличии» (`stock > 0`). Если такой товар каким-то образом попадает в отрендеренный список, кнопка «В корзину» активна, но добавление не выполняется (`useCart.ts` строка 54: `if (product.stock <= 0) return`).
- Files: `components/CatalogView.tsx:54`, `components/ProductCard.tsx:81`, `components/AddToCartButton.tsx:15`, `lib/useCart.ts:54`
- Trigger: Теоретически не воспроизводится, так как `CatalogView` фильтрует до рендеринга. Но если фильтрация обходится (например, через прямую ссылку или будущий рефакторинг), компоненты будут давать разное поведение.
- Workaround: Нет; три разных порога сосуществуют молча.

**Группы «Коробочные конфеты», «Прикассовое», «Стоевъ и Сэнсой» не включены в `GROUP_ORDER`:**
- Symptoms: Группы, реально присутствующие в данных и обрабатываемые в `packaging.ts`, отсутствуют в массиве `GROUP_ORDER` в `CatalogView.tsx` (строки 18-31). Эти группы сортируются с индексом 999 и отображаются в произвольном порядке в конце фильтра.
- Files: `components/CatalogView.tsx:18-31`, `lib/packaging.ts:61-63`
- Trigger: Всегда, когда эти группы присутствуют в каталоге.
- Workaround: Нет функционального ущерба, только нестабильный порядок отображения.

**Системный промпт ИИ-бота обрезает каталог до 200 первых товаров:**
- Symptoms: `bot/ai/system-prompt.ts` (строка 7: `products.slice(0, 200)`) передаёт Gemini только первые 200 из ~935 товаров. ИИ не знает об остальных 735 и будет отвечать «такого товара нет», даже если он существует.
- Files: `bot/ai/system-prompt.ts`
- Trigger: Любой запрос в боте о товаре, не попавшем в первые 200 строк каталога.
- Workaround: Пользователь может использовать function call `search_products`, который ищет по всему каталогу, но только если задаёт конкретный запрос.

---

## Security Considerations

**Telegram Bot Token: рекомендация ротации:**
- Risk: По имеющимся сведениям, токен был однажды вставлен в чат. Даже если чат приватный, токен мог попасть в логи, историю чата или буфер обмена.
- Files: `uploader/.env` (секрет хранится вне git — хорошо), `admin_bot/admin_bot.py`
- Current mitigation: Токен не в git (`.gitignore` корректен). `admin_bot.py` проверяет `OWNER_ID` перед выполнением команд.
- Recommendations: Сгенерировать новый токен через `@BotFather` командой `/revoke`, обновить в `uploader/.env` и перезапустить `admin_bot`. Старый токен после ротации перестаёт работать автоматически.

**`credentials.json` лежит в `scripts/` — попадает в git при ошибке:**
- Risk: Файл `scripts/credentials.json` (ключ Google Service Account) исключён из git через `.gitignore` (строка `credentials.json`). Однако правило глобальное: если кто-то создаст файл с таким именем в другой папке, он не будет исключён. Кроме того, `credentials.json` находится в папке `scripts/`, которая коммитится — ошибка в `.gitignore` или `git add -f` немедленно опубликуют ключ.
- Files: `scripts/credentials.json`, `.gitignore`
- Current mitigation: `.gitignore` содержит `credentials.json`. Файл не отслеживается.
- Recommendations: Добавить `scripts/credentials.json` явно в `.gitignore` (или `**/credentials.json`). Периодически проверять `git status` перед коммитами.

**API-ключ Google Sheets доступен публично через `?key=` в URL:**
- Risk: `lib/sheets.ts` (строка 17) формирует URL вида `https://sheets.googleapis.com/...?key=<API_KEY>`. Этот ключ (`GOOGLE_API_KEY`) используется в браузерных запросах (через Next.js server-side fetch), но если когда-либо попадёт в клиентский JS — будет виден всем.
- Files: `lib/sheets.ts`
- Current mitigation: Запрос выполняется сервер-сайд в Next.js (не в браузере). Ключ хранится в `.env.local` (вне git).
- Recommendations: Убедиться, что `GOOGLE_API_KEY` не попадает в переменные с префиксом `NEXT_PUBLIC_`. Ограничить ключ в Google Cloud Console по реферерам и API (только Sheets v4 read-only).

**Отсутствует rate limiting на API-эндпоинты веб-загрузчика:**
- Risk: `uploader/app.py` не имеет rate limiting. Злоумышленник, знающий `APP_SECRET`, может многократно вызывать `/update`, запуская `upload.py` параллельно и перегружая Google Sheets API квотами.
- Files: `uploader/app.py`
- Current mitigation: Один gunicorn-воркер (`-w 1`) делает параллельный запуск невозможным в рамках одного процесса.
- Recommendations: Текущей защиты через single worker достаточно для небольшой нагрузки. При масштабировании добавить флаг «обновление в процессе».

---

## Performance Bottlenecks

**`getProducts()` в боте использует модульный кэш — сбрасывается при каждом cold start:**
- Problem: `bot/services/products.ts` (строки 8-9) хранит кэш в module-level переменных `cachedProducts` и `cacheTimestamp`. На Vercel каждый serverless-вызов может быть новым cold start — модуль переинициализируется, кэш пуст, и немедленно идёт запрос к Google Sheets.
- Files: `bot/services/products.ts`
- Cause: Serverless-среда не гарантирует сохранение состояния между вызовами.
- Improvement path: Перенести кэш в Vercel KV (уже используется для корзины) или использовать `revalidate` в fetch-запросе, как сделано в `lib/sheets.ts`.

**`_find_photo_entry()` — полный перебор при каждом товаре:**
- Problem: `scripts/upload.py` (строки 444-452): для каждого из ~935 товаров выполняется линейный перебор всего `photo_data` (до 1438 записей) с проверкой двухстороннего частичного вхождения строк.
- Files: `scripts/upload.py:444-452`
- Cause: O(N×M) сложность при каждом вызове `get_photo_url()` и `get_photo_description()`.
- Improvement path: Заменить на заранее построенный точный словарь. Частичный поиск приводит к ложным совпадениям (см. раздел «Fragile Areas»).

---

## Fragile Areas

**Автодетекция нового формата 1С по номеру колонки:**
- Files: `scripts/upload.py:194-196`
- Why fragile: `is_new_format()` считает формат «новым», если колонка «Цена» имеет индекс ≥ 5. Если поставщик добавит промежуточные колонки в старый формат или изменит структуру, детектор даст ошибочный результат без единого предупреждения.
- Safe modification: Добавить явный CLI-флаг `--new-format` или проверку по имени листа/наличию специфичных заголовков.
- Test coverage: Нет тестов.

**Двухстороннее частичное совпадение в `_find_photo_entry()`:**
- Files: `scripts/upload.py:449-452`
- Why fragile: Условие `photo_name in name_lower or name_lower in photo_name` может дать ложное совпадение. Например, «Сок» найдёт «Добрый Сок Апельсин», а «кофе» — «кофейный батончик». Порядок перебора `photo_data.items()` недетерминирован в Python < 3.7 (в 3.7+ детерминирован, но зависит от порядка загрузки).
- Safe modification: Использовать точное совпадение для `photo_overrides.json` (уже ключевой словарь) и частичное только для `photo_map.json`-автоматики с логированием совпадений.
- Test coverage: Нет тестов.

**`packaging.ts` — длинный if/switch без тестов и с дублирующимися группами:**
- Files: `lib/packaging.ts`
- Why fragile: Около 40 жёстко прописанных правил. Функция знает о группах «Соусы и специи» И «Соусы и приправы» (строки 59-60) — два разных названия одной группы в данных. При переименовании группы в `category_map.json` функция молча вернёт пустую строку фасовки.
- Safe modification: При добавлении правила всегда проверять, совпадает ли строка группы с тем, что реально приходит из Google Sheet.
- Test coverage: Нет тестов.

**`PRODUCT_OVERRIDES` в `upload.py` — хардкодные строки на русском:**
- Files: `scripts/upload.py:295-319`
- Why fragile: Словарь `PRODUCT_OVERRIDES` и список `PRODUCT_CONTAINS_OVERRIDES` — захардкоженные строки с русскими буквами в Python-коде. Любое изменение требует редактирования кода и деплоя. Если поставщик переименует товар (например, «Соус POMATO» → «Соус Помато»), правило молча перестаёт работать.
- Safe modification: Вынести в отдельный JSON-файл (по аналогии с `badges.json` и `category_map.json`).
- Test coverage: Нет тестов.

**`GROUP_ORDER` в `CatalogView.tsx` — неполный список групп:**
- Files: `components/CatalogView.tsx:18-31`
- Why fragile: Группы «Коробочные конфеты», «Прикассовое», «Стоевъ и Сэнсой», «Новинки», «Другое» не включены в `GROUP_ORDER`. При добавлении новой группы через `category_map.json` она автоматически попадёт в конец в произвольном порядке без явного указания.
- Safe modification: Добавить все актуальные группы в массив; рассмотреть хранение порядка в `category_map.json` или отдельном конфиге.
- Test coverage: Нет тестов.

---

## Scaling Limits

**Один gunicorn-воркер — единственный поток обработки загрузчика:**
- Current capacity: 1 параллельный HTTP-запрос. Запуск `upload.py` блокирует все остальные запросы на `UPLOAD_TIMEOUT` секунд (по умолчанию 600).
- Limit: Если оператор случайно нажмёт «Обновить» дважды или параллельно откроет страницу — второй запрос зависнет до освершения первого.
- Scaling path: Один воркер — сознательный выбор (предотвращает параллельную запись в Sheet). Для UX добавить флаг «обновление выполняется» в shared-state или файл-lock.

**Google Sheets API — лимит бесплатного тарифа:**
- Current capacity: Без кэша каждый запрос к каталогу — это запрос к Sheets API. Каталог кэшируется 5 мин в Next.js, но при множестве пользователей возможны всплески.
- Limit: Google Sheets API бесплатного тарифа: 300 запросов/мин на проект. При высоком трафике (маловероятном на текущем масштабе) возможна ошибка 429.
- Scaling path: Уже есть ISR 5 мин. При росте нагрузки — перейти на Vercel KV или static JSON-файл, генерируемый при каждом `upload.py`.

**Bot cache сбрасывается на каждый cold start (повторно):**
- Current capacity: При интенсивном использовании бота каждый новый serverless-экземпляр делает полный запрос к Sheets API (~50 мс + сетевые задержки).
- Limit: Накапливается на Sheets API квотах при параллельных пользователях.
- Scaling path: Перенести кэш продуктов в Vercel KV (уже используется для корзины).

---

## Dependencies at Risk

**`gspread` и `google-auth` не указаны в `scripts/requirements.txt` явно с версиями:**
- Risk: `requirements.txt` может указывать зависимости без pin версий (или вообще их не иметь). Обновление `gspread` 6.x изменило API (`.update()` принимает 2D-массив иначе).
- Impact: `upload.py` может сломаться при `pip install -r requirements.txt` после мажорного обновления gspread.
- Migration plan: Проверить `scripts/requirements.txt` и зафиксировать версии `gspread>=6` и `google-auth>=2`.

**`grammy` v1.41 — бот-библиотека:**
- Risk: grammY активно развивается; webhook callback API менялся между минорными версиями.
- Impact: `bot/index.ts` использует `webhookCallback` — при обновлении grammY сигнатура может измениться.
- Migration plan: Зафиксировать версию в `package.json` (`"grammy": "1.41.1"` без `^`).

---

## Missing Critical Features

**Нет автоматических тестов ни в одной части системы:**
- Problem: Ни Python-скрипты (`scripts/`), ни Next.js-компоненты (`components/`, `lib/`), ни Telegram-бот (`bot/`) не имеют ни одного test/spec файла. `find . -name "*.test.*"` возвращает пустой результат.
- Blocks: Нельзя безопасно рефакторить `upload.py`, `packaging.ts`, `_find_photo_entry()`, новый 1С-парсер.
- Priority: High — особенно критично для `upload.py` перед запуском нового 1С-формата в продакшн.

**Нет описаний товаров (поле `description`) — колонка пуста:**
- Problem: `photo_manual.xlsx` содержит колонку D для описаний, но CLAUDE.md фиксирует: «Заполнить описания товаров в photo_manual.xlsx» как невыполненное. Бот передаёт описания в системный промпт Gemini, но для большинства товаров там пусто.
- Blocks: Полноценная работа ИИ-консультанта в боте.

**Не задеплоен Telegram-бот:**
- Problem: Код бота (`bot/`, `app/api/bot/route.ts`) написан, но webhook не настроен (скрипт `scripts/setup-webhook.ts` есть, но нет признаков что он запускался). `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`, `KV_REST_API_URL` не описаны в `.env.local.example`.
- Blocks: Весь функционал бота.

---

## Test Coverage Gaps

**Парсер Excel (обоих форматов):**
- What's not tested: `parse_excel_file()`, `parse_new_format()`, `is_new_format()`, `find_header_cols()`, `is_category_row()`, `is_header_row()`, `strip_category_prefix()`
- Files: `scripts/upload.py:95-167`, `scripts/upload.py:177-243`
- Risk: Тихая потеря товаров при нестандартных структурах Excel. Особенно критично для нового 1С-формата.
- Priority: High

**Маппинг фото (`_find_photo_entry`, `load_photo_data`):**
- What's not tested: Логика частичного совпадения, приоритет `photo_overrides` над `photo_map`, обработка отсутствующих файлов.
- Files: `scripts/upload.py:389-464`
- Risk: Неверные фото у товаров при ошибке в маппинге — незаметно при отсутствии тестов.
- Priority: Medium

**`getPackaging()` — правила фасовки:**
- What's not tested: Ни одно из ~40 правил не покрыто тестами.
- Files: `lib/packaging.ts`
- Risk: Регрессия при добавлении новых правил, ломающая существующие совпадения.
- Priority: Medium

**Бэкап/откат каталога (`sheet_tool.py`):**
- What's not tested: Сценарии `backup`, `rollback`, `stash_new`, `apply_new`, `drop_new` — нет ни unit, ни integration тестов.
- Files: `scripts/sheet_tool.py`
- Risk: Ошибка в логике отката не выявится до момента реальной аварии.
- Priority: High

---

## Telegram Connectivity Single Point of Failure

**`admin_bot.py` использует SOCKS-прокси как единственный путь к Telegram:**
- Files: `admin_bot/admin_bot.py:70`, `scripts/notify_tg.py:70`
- Why fragile: `TG_PROXY` — единственный прокси. При недоступности прокси-сервера `getUpdates` и `sendMessage` падают с `requests.RequestException`. Бот уходит в `time.sleep(5)` и повторяет — но если прокси недоступен постоянно, уведомления о критическом сбое каталога не дойдут до владельца.
- Safe modification: Добавить fallback (второй прокси или попытку прямого подключения при ошибке прокси). Мониторинг uptime самого бота отсутствует.
- Test coverage: Нет тестов.

---

*Concerns audit: 2026-06-06*
