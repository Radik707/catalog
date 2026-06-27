---
phase: 10-sw-manifest
reviewed: 2026-06-12T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - app/sw.ts
  - app/manifest.ts
  - app/layout.tsx
  - next.config.mjs
  - scripts/generate_pwa_icons.py
  - package.json
  - .gitignore
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Этап 10: Отчёт код-ревью (PWA: Service Worker + Manifest + иконки)

**Проверено:** 2026-06-12
**Глубина:** standard
**Файлов проверено:** 7
**Статус:** issues_found

## Сводка

Проверены файлы PWA-фундамента: service worker (`app/sw.ts`), Web App Manifest
(`app/manifest.ts`), корневой layout, конфиг Next.js + Serwist, Python-генератор
иконок, `package.json` и `.gitignore`.

Что подтверждено как корректное (проверял исходники зависимостей, не верил на слово):
- `@serwist/next` по умолчанию `register: true` и `swUrl: "/sw.js"` — SW
  регистрируется автоматически, ручная регистрация в layout не нужна (не баг).
- Секрет в `start_url` — принятая модель безопасности проекта, не помечаю.
- Иконки сгенерированы корректно: обычные — с прозрачными скруглёнными углами,
  maskable — полностью залита (alpha 255), apple-touch — RGB без альфы 180×180.

**Главная проблема — CR-01:** регулярка matcher для `/api/products` в service
worker никогда не сработает, потому что Serwist тестирует regex против полного
`url.href` (`https://домен/api/products`), а не против pathname. NetworkFirst-кэш
API товаров фактически отключён. Это ядро всего этапа офлайн-каталога — без него
этап 11 (IndexedDB) встанет на нерабочий фундамент.

## Критические проблемы

### CR-01: NetworkFirst-стратегия для `/api/products` никогда не активируется (мёртвый matcher)

**Файл:** `app/sw.ts:46`
**Issue:** Matcher задан как `/^\/api\/products/`. Я проверил реализацию
`RegExpRoute` в `node_modules/serwist/dist/...`: matcher вызывается как
`regExp.exec(url.href)` — против **полного URL**, а не pathname. Для
same-origin запроса `url.href` равен, например,
`https://catalog.vercel.app/api/products`. Регулярка с якорем `^\/api\/products`
требует, чтобы строка **начиналась** с `/api`, но `href` начинается с
`https://`. Совпадения не будет никогда.

Для same-origin Serwist допускает частичное совпадение (без обязательного начала),
но именно якорь `^` ломает это: он привязывает к началу `href`. В итоге запросы
к API товаров не попадают в кэш `api-products`, а обрабатываются `defaultCache`
(или вообще проходят мимо), и офлайн-чтение каталога на этапе 11 работать не будет.

**Fix:** убрать якорь начала строки и/или матчить по pathname, чтобы совпадало
внутри полного href:
```ts
{
  // Совпадает внутри https://домен/api/products?... — без якоря ^
  matcher: /\/api\/products/,
  handler: new NetworkFirst({
    networkTimeoutSeconds: 5,
    cacheName: "api-products",
  }),
},
```
Аналогично безопаснее переписать через callback по pathname:
```ts
matcher: ({ url }) => url.pathname.startsWith("/api/products"),
```
После правки обязательно проверить в DevTools → Application → Cache Storage,
что кэш `api-products` наполняется после захода в каталог.

## Предупреждения

### WR-01: При незаданном `CATALOG_SECRET` манифест указывает start_url на страницу-404

**Файл:** `app/manifest.ts:17`
**Issue:** `start_url: \`/catalog/${process.env.CATALOG_SECRET ?? ""}\``. Fallback
на пустую строку даёт `start_url: "/catalog/"`. По описанию проекта `app/page.tsx`
и несекретные маршруты — заглушка-404. Если на сборке Vercel переменная окружения
не проброшена (частая ошибка: переменная задана для Production, но не для Preview,
или забыта при первом деплое), установленное на домашний экран PWA будет
открываться на 404. Хуже того — ошибка тихая: манифест соберётся без падения,
проблема всплывёт только когда пользователь нажмёт иконку.
**Fix:** провалить сборку при отсутствии секрета — это конфигурация, без которой
PWA бессмысленна:
```ts
const secret = process.env.CATALOG_SECRET;
if (!secret) {
  throw new Error("CATALOG_SECRET не задан — манифест PWA собрать нельзя");
}
// ...
start_url: `/catalog/${secret}`,
```

### WR-02: У манифеста нет `scope`, и start_url под секретным путём не входит в scope SW по умолчанию

**Файл:** `app/manifest.ts:8-54`
**Issue:** Поле `scope` не задано. По спецификации W3C, когда `scope` опущен, он
выводится из директории `start_url` — то есть станет `/catalog/<secret>/`. Это
сузит навигационную область PWA до секретной папки и может привести к тому, что
переходы на `/cart` или другие корневые пути будут открываться вне standalone-окна
(в браузере). При этом SW зарегистрирован со scope `/` (через
`Service-Worker-Allowed: /`), и возникает рассинхрон между scope манифеста и scope
SW. Для текущего каталога, где всё живёт под `/catalog/<secret>/`, это может не
проявиться, но это хрупкое допущение.
**Fix:** явно задать scope, согласованный с тем, что должно открываться в
standalone:
```ts
scope: `/catalog/${secret}/`,
```
Если в standalone должны открываться и корневые маршруты — задать `scope: "/"`,
но тогда start_url обязан быть внутри этого scope (он и так внутри).

### WR-03: Генератор иконок упадёт на любой машине без `C:/Windows/Fonts/arialbd.ttf`

**Файл:** `scripts/generate_pwa_icons.py:17,45,69,94`
**Issue:** Путь к шрифту захардкожен абсолютным Windows-путём. `ImageFont.truetype`
бросит `OSError`, если файл не найден (другая ОС, нестандартная установка Windows,
CI). Скрипт помечен как «запускать один раз», но при необходимости пересоздать
иконки на другой машине он просто упадёт без понятного сообщения.
**Fix:** добавить фолбэк и понятную ошибку:
```python
try:
    font = ImageFont.truetype(FONT_PATH, font_size)
except OSError:
    raise SystemExit(
        f"Шрифт не найден: {FONT_PATH}. Укажите путь к жирному TTF-шрифту."
    )
```

### WR-04: Maskable-иконка центрируется по bbox без учёта реального вертикального смещения глифа — риск обрезки в safe-zone

**Файл:** `scripts/generate_pwa_icons.py:97-103`
**Issue:** Текст центрируется через `textbbox((0,0), ...)`, но смещение `bbox[1]`
(верхний отступ глифа) у кириллицы в Arial Bold ненулевое, а вертикальное
центрирование `(size - text_h)//2 - bbox[1]` опирается только на bounding box без
учёта baseline/descent. Для maskable это критичнее, чем для обычной иконки: Android
обрезает всё за пределами центрального круга ~80%. При небольшом вертикальном
сдвиге «ВД» монограмма может оказаться смещена к краю safe-zone. Сейчас font_size
= 0.8*0.42 ≈ 33% — запас есть, но центровка по bbox делает результат
непредсказуемым между версиями шрифта.
**Fix:** использовать `anchor="mm"` (middle-middle) у Pillow для надёжного
центрирования вместо ручного расчёта по bbox:
```python
draw.text((size / 2, size / 2), text, fill=WHITE, font=font, anchor="mm")
```
Применить во всех трёх функциях отрисовки. Это устранит ручную арифметику со
смещениями и сделает центровку детерминированной.

## Info

### IN-01: Мёртвый параметр `safe_zone` в `draw_rounded_icon`

**Файл:** `scripts/generate_pwa_icons.py:24,44`
**Issue:** Параметр `safe_zone=1.0` объявлен и участвует в расчёте `font_size`, но
во всех вызовах (`draw_rounded_icon(192)`, `draw_rounded_icon(512)`) передаётся
значение по умолчанию — никогда не отличается от 1.0. Для maskable написана
отдельная функция `draw_maskable`. То есть параметр `safe_zone` в этой функции —
мёртвая абстракция, вводящая в заблуждение (комментарий упоминает «для maskable —
~0.5», но maskable эту функцию не использует).
**Fix:** убрать параметр `safe_zone` из `draw_rounded_icon` и упростить
`font_size = int(size * 0.52)`.

### IN-02: Неиспользуемый импорт `math`

**Файл:** `scripts/generate_pwa_icons.py:9`
**Issue:** `import math` присутствует, но `math` нигде не используется в файле.
**Fix:** удалить строку `import math`.

### IN-03: Дублирование `theme_color` в manifest и viewport без единого источника

**Файл:** `app/manifest.ts:26`, `app/layout.tsx:32`, `scripts/generate_pwa_icons.py:13`
**Issue:** Цвет `#2563eb` / `(37,99,235)` захардкожен в трёх местах
(manifest.theme_color, viewport.themeColor, BLUE в генераторе иконок). Это не баг
сейчас, но при смене фирменного цвета легко обновить одно место и забыть другое —
получится рассинхрон splash/иконок/статус-бара. Дублирование в TS-файлах и
Python-скрипте неустранимо полностью, но внутри Next-кода стоит вынести в
константу.
**Fix:** в TS вынести в общий модуль, например `lib/branding.ts`:
```ts
export const THEME_COLOR = "#2563eb";
```
и импортировать в `manifest.ts` и `layout.tsx`.

---

_Reviewed: 2026-06-12_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
