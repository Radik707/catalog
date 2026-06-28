# Phase 17: Карточка витрины — стикер акции + раскрытие фото клиентом — Карта паттернов

**Составлено:** 2026-06-28
**Файлов проанализировано:** 2 изменяемых (+ 3 справочных аналога в том же кодовом ядре)
**Аналоги найдены:** 2 / 2 (оба — внутрифайловые, эталон рядом)

---

## Классификация файлов

| Файл (изменяется) | Роль | Поток данных | Ближайший аналог | Качество совпадения |
|-------------------|------|--------------|------------------|---------------------|
| `components/CardCornerButton.tsx` | component (угловая кнопка карточки) | event-driven (клик → `onPhotoOpen` / `toggleFavorite`) | **сам файл** — ветка `role === "sales"` (стрелки → `onPhotoOpen`) | exact (готовая кнопка-эталон внутри файла) |
| `components/ProductCard.tsx` | component (карточка товара) | transform / request-response (рендер `product.badge`) | **сам файл** — текущий вывод `badgeStyle` + `badgeLabel()` (строки 181–187, 199–203, 311–315) | exact (прокачка существующего вывода, не новый канал) |

> **Главный принцип этапа:** обе правки переиспользуют уже существующие в этих же файлах
> образцы (стрелки агента, вывод бейджа). Это не «найти аналог в другом файле», а
> «скопировать паттерн из соседней ветки того же компонента». Поэтому качество совпадения —
> exact, и планировщику не нужно искать ничего за пределами карточки.

---

## Назначения паттернов

### `components/CardCornerButton.tsx` (component, event-driven)

**Аналог:** ветка `role === "sales" && canOpenPhoto` в этом же файле (строки 45–66) — это
**готовая кнопка раскрытия фото** со стрелками и `onPhotoOpen`. Задача D-03/D-04/D-05 —
показать ту же кнопку клиенту **под** сердечком.

**SVG-иконка стрелок (копировать дословно, строки 56–63):**
```tsx
{/* Стрелки в разные стороны (arrows-pointing-out, heroicons) */}
<svg className={icon} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
  <path
    strokeLinecap="round"
    strokeLinejoin="round"
    d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
  />
</svg>
```

**Классы Tailwind угловой кнопки-стрелок (строка 54):**
```tsx
className={`absolute top-1 right-1 z-10 flex ${box} items-center justify-center rounded-full bg-white/80 text-gray-700 shadow-sm backdrop-blur-sm active:bg-white`}
```

**Паттерн `stopPropagation` в onClick (строки 49–52) — обязателен, чтобы клик не переворачивал карточку:**
```tsx
onClick={(e) => {
  e.stopPropagation();
  onPhotoOpen?.();
}}
```

**Сердечко клиента (строки 70–98) — остаётся как есть, новая кнопка добавляется ПОД ним.**
Классы сердечка (строка 79):
```tsx
className={`absolute top-1 right-1 z-10 flex ${box} items-center justify-center rounded-full bg-white/80 shadow-sm backdrop-blur-sm active:bg-white ${
  fav ? "text-red-500" : "text-gray-500"
}`}
```

**SSR-safe заглушка до `ready` (строки 39–42) — НЕ ломать, две кнопки тоже ждут роли:**
```tsx
// ── До готовности роли: пустое место того же размера (без мелькания иконки) ──
if (!ready) {
  return <div className={`absolute top-1 right-1 z-10 ${box}`} aria-hidden />;
}
```

**Размеры кнопки (строки 33–37) — переиспользовать для обеих кнопок клиента:**
```tsx
const box = size === "sm" ? "h-7 w-7" : "h-8 w-8";
const icon = size === "sm" ? "h-4 w-4" : "h-5 w-5";
```

**Что добавить (D-03..D-07):**
- В ветке `role === "client"` рендерить **вертикальный стек двух кнопок** в правом
  верхнем углу: сердечко сверху (как сейчас, `top-1 right-1`), стрелки — под ним.
- Вторая кнопка (стрелки) показывается **только при `canOpenPhoto`** (D-05): нет фото →
  только сердечко.
- Действие стрелок клиента — тот же `onPhotoOpen?.()` со `stopPropagation` (D-07),
  скопировать из ветки sales (строки 49–52).
- Смещение второй кнопки вниз — по образцу `Established Patterns` из CONTEXT: тот же
  шаблон `absolute ... rounded-full bg-white/80 shadow-sm backdrop-blur-sm`, но
  вертикальный отступ (например, обёртка-стек `flex flex-col gap-1` либо вторая кнопка
  с `top-9`/`top-10` вместо `top-1`). Точный отступ/z-index — на усмотрение (Discretion),
  чтобы кнопки не налезали друг на друга.
- **Агент (sales) не трогать** (D-06): его ветка остаётся ровно как строки 45–66.
- Реальный props-канал уже есть: `productId`, `onPhotoOpen`, `canOpenPhoto`, `size` —
  новые пропсы не нужны.

**Где монтируется компонент (контекст из ProductCard):** в трёх местах — режим grid/
presentation (строки 189–193, без `size`), режим list (строки 341–346, `size="sm"`).
Для списка две кнопки на миниатюре 14×14 могут не поместиться — давать ли клиенту
стрелки в списке, решает исполнитель (Discretion, D в CONTEXT, строки 102–104).

---

### `components/ProductCard.tsx` (component, transform)

**Аналог:** текущий вывод бейджа `акция` в этом же файле — `BADGE_STYLES.акция` +
`badgeLabel()` + позиционирование `badgePos`. Стикер (D-08) — это «прокачанная» версия
того же вывода (крупнее/ярче/с иконкой), а **не новый канал данных** (источник прежний —
`product.badge === "акция"` из `badges.json`).

**Текущий стиль бейджа акции (строки 53–57):**
```tsx
const BADGE_STYLES: Record<string, string> = {
  хит: "bg-red-500 text-white",
  новинка: "bg-green-500 text-white",
  акция: "bg-orange-500 text-white",
};
```

**Подпись бейджа (строки 61–64) — «новинка» → «NEW», остальное как есть:**
```tsx
function badgeLabel(badge?: string): string | undefined {
  if (!badge) return undefined;
  return badge === "новинка" ? "NEW" : badge;
}
```

**Выбор стиля по метке (строка 106):**
```tsx
const badgeStyle = product.badge ? BADGE_STYLES[product.badge] : null;
```

**Позиционирование бейджа в grid/presentation (строки 130–131):**
```tsx
const badgeCls = isPresentation ? "text-xs px-1.5 py-0.5" : "text-[9px] px-1 py-0.5";
const badgePos = isPresentation ? "top-2 left-2" : "top-1 left-1";
```

**Вывод бейджа поверх фото — grid/presentation (строки 181–187):**
```tsx
{badgeStyle && (
  <span
    className={`absolute ${badgePos} font-medium rounded ${badgeCls} ${badgeStyle}`}
  >
    {badgeLabel(product.badge)}
  </span>
)}
```

**Вывод бейджа в режиме «без фото» (строки 199–203):**
```tsx
{!showPhotos && badgeStyle && (
  <span className={`self-start font-medium rounded ${badgeCls} ${badgeStyle}`}>
    {badgeLabel(product.badge)}
  </span>
)}
```

**Вывод бейджа в режиме списка (строки 311–315):**
```tsx
{badgeStyle && (
  <span className={`absolute top-1.5 right-1.5 text-[10px] font-medium px-1.5 py-0.5 rounded ${badgeStyle}`}>
    {badgeLabel(product.badge)}
  </span>
)}
```

**Что добавить (D-08..D-11):**
- Сделать вывод метки `акция` **заметнее** обычного бейджа: яркая «пилюля» с иконкой
  (например, красный фон + 🔥 + «Акция»), крупнее текущего (`text-[9px]`/`text-xs`).
  Точный текст/цвет/эмодзи/размер/анимация — Discretion (CONTEXT строки 95–96).
- Стикер живёт **в углу фото `top-left`** (D-09), как нынешний бейдж (`badgePos`),
  чтобы НЕ перекрывать название/цену и НЕ конфликтовать с угловыми кнопками
  (`top-right`). Бейджи слева, кнопки справа — углы не пересекаются (CONTEXT строки
  99–101, 163–164).
- Реализация — частный случай вывода бейджа: когда `product.badge === "акция"`, рисовать
  стикер-вариант вместо/поверх стандартного `<span>`. Можно ввести отдельный стиль в
  `BADGE_STYLES.акция` (краснее/ярче) **и/или** отдельный фрагмент с иконкой. У товара
  ровно одна метка (D-10), конфликта «акция + хит» нет — приоритет не требуется.
- Применить во **всех трёх режимах** (grid, presentation, list) — три точки вывода бейджа
  выше (строки 181–187, 199–203, 311–315). В режиме «без фото» (199–203) стикер тоже
  уместен, но без угловой привязки (`self-start`).
- **Forward-looking** (D-11): `badges.json` ключ `"акция"` сейчас пуст — стикер ни на чём
  визуально не появится, пока владелец не отметит товар. Это нормально, проверять логику
  можно временной меткой.

---

## Общие паттерны (Shared Patterns)

### Угловая кнопка карточки (шаблон)
**Источник:** `components/CardCornerButton.tsx`, строки 54 и 79.
**Применять к:** обеим кнопкам клиента (сердечко + стрелки).
```tsx
absolute top-1 right-1 z-10 flex ${box} items-center justify-center rounded-full bg-white/80 shadow-sm backdrop-blur-sm active:bg-white
```
Вторая кнопка — тот же шаблон со смещением по вертикали вниз (стек).

### Защита от переворота карточки (stopPropagation)
**Источник:** `components/CardCornerButton.tsx`, строки 49–52 и 73–76.
**Применять к:** любому кликабельному элементу поверх фото (карточка переворачивается по
клику на фото — строки ProductCard 157, 322).
```tsx
onClick={(e) => { e.stopPropagation(); /* действие */ }}
```

### SSR-safe ветвление по роли
**Источник:** `lib/useRole.tsx` (`role`, `ready`) + `CardCornerButton.tsx` строки 39–42.
**Применять к:** любому коду, где роль меняет вёрстку. До `ready` — пустое место того же
размера, иначе на сотнях карточек мелькают иконки-дефолты.
```tsx
const { role, ready } = useRole();
if (!ready) return <div className={`absolute top-1 right-1 z-10 ${box}`} aria-hidden />;
```

### Источник действия раскрытия фото (Lightbox)
**Источник:** `components/CatalogView.tsx`, строки 171–174, 189–201, 112–117, 256–261.
**Применять к:** кнопке стрелок клиента — она просто дёргает уже проброшенный
`onPhotoOpen`, новой логики просмотрщика не нужно (D-07).
```tsx
// CatalogView пробрасывает в каждую карточку:
onPhotoOpen={() => openLightbox(product)}
// openLightbox ищет индекс в photoProducts (только товары с imageUrl) и открывает Lightbox.
```
Так как `photoProducts` уже фильтрует по `imageUrl`, кнопка стрелок у клиента безопасна
только при `canOpenPhoto = !!product.imageUrl` (уже передаётся из ProductCard, строки
192, 344).

### Контекст избранного (сердечко)
**Источник:** `components/FavoritesProvider.tsx` (`useFavoritesContext`) →
`isFavorite`, `toggleFavorite`. Уже используется в `CardCornerButton` (строка 31).
**Применять к:** оставить как есть — провайдер подключён, новых не нужно.

---

## Файлы без аналога

Нет. Обе правки — модификация существующих компонентов с эталоном внутри тех же файлов.
Внешний просмотрщик (`Lightbox.tsx`), роль (`useRole.tsx`), избранное
(`FavoritesProvider.tsx`) и источник действия (`CatalogView.tsx`) уже подключены и
переиспользуются как есть — новые провайдеры/файлы не создаются.

---

## Метаданные

**Область поиска аналогов:** `components/` (карточка и её зависимости), `lib/` (роль).
**Файлов прочитано:** 5 — `CardCornerButton.tsx`, `ProductCard.tsx`, `useRole.tsx`,
`CatalogView.tsx` (фрагменты), `FavoritesProvider.tsx`.
**Инварианты не затрагиваются:** `force-dynamic` витрины, офлайн-модель v1.3, SSR-safe
роль — правки чисто клиентские по фронту карточки (CONTEXT строки 164–166).
**Дата извлечения паттернов:** 2026-06-28
