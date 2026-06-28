---
phase: 17-card-promo-photo
plan: 02
subsystem: ui
tags: [tailwind, badge, sticker, productcard, react]

requires:
  - phase: 17-card-promo-photo/17-01
    provides: CardCornerButton — кнопка раскрытия фото для клиента

provides:
  - Усиленный стикер акции (MERCH-01): яркая «пилюля» 🔥 Акция вместо мелкого оранжевого бейджа
  - Хелпер renderBadge() — единое место вывода всех бейджей в ProductCard
  - Константы PROMO_STICKER_GRID / PROMO_STICKER_PRES / PROMO_STICKER_LIST

affects:
  - ProductCard.tsx (карточка)
  - этап 18+ (любые правки карточки использует renderBadge)

tech-stack:
  added: []
  patterns:
    - renderBadge() — хелпер, отрисовывает метку: для «акции» — усиленный стикер, для остальных — стандартный span
    - PROMO_STICKER_* — три константы размеров стикера под каждый режим (grid / presentation / list)

key-files:
  created: []
  modified:
    - components/ProductCard.tsx

key-decisions:
  - "[17-02] renderBadge() — общий хелпер для всех трёх точек вывода, устраняет дублирование"
  - "[17-02] bg-red-600 rounded-full shadow — «пилюля», визуально контрастнее оранжевого bg-orange-500"
  - "[17-02] Три константы PROMO_STICKER_*: grid text-[11px], pres text-xs, list text-[10px] — пропорциональны к размеру фото"
  - "[17-02] Хит и NEW не затронуты — только ветка badge === «акция» в renderBadge"

patterns-established:
  - "renderBadge(): централизованный рендер метки — расширяемо для будущих badge-типов"

requirements-completed: [MERCH-01]

duration: 12min
completed: 2026-06-28
---

# Phase 17 Plan 02: Стикер акции — Summary

**Стикер «акции» на карточке товара: яркая красная «пилюля» 🔥 Акция вместо мелкого оранжевого бейджа, во всех трёх режимах вывода (сетка, презентация, без фото, список) через хелпер renderBadge()**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-06-28T12:54:21Z
- **Completed:** 2026-06-28
- **Tasks:** 1 (Task 2 — checkpoint, ожидает приёмки на проде)
- **Files modified:** 1

## Accomplishments

- Введён хелпер `renderBadge()` в `ProductCard.tsx` — единое место вывода всех бейджей, без дублирования
- Для `product.badge === "акция"` рисуется усиленный стикер: `bg-red-600 rounded-full shadow`, текст «🔥 Акция», крупнее обычного бейджа (`text-[11px]`/`text-xs` vs `text-[9px]`/`text-[10px]`)
- Стикер применён во всех трёх точках: grid/presentation поверх фото (`absolute ${badgePos}`, top-left), режим «без фото» (`self-start`), режим списка (`absolute top-1.5 right-1.5`)
- Метки «хит» и «новинка» (NEW) без изменений: `renderBadge` для них рендерит прежний `<span>` с BADGE_STYLES
- `npm run build` — код 0, TypeScript-ошибок нет

## Task Commits

1. **Task 1: Усилить стикер акции во всех режимах вывода бейджа** — `e76fc85` (feat)

**Plan metadata:** (создаётся этим файлом)

## Files Created/Modified

- `components/ProductCard.tsx` — добавлены `PROMO_STICKER_*` константы, хелпер `renderBadge()`, все три точки вывода бейджа переведены на хелпер

## Decisions Made

- **renderBadge() как хелпер, а не inline-условие** — три точки вывода, дублирование нежелательно; хелпер получает `extraCls` (позиционирование снаружи) и `promoStk` (размер стикера под режим)
- **bg-red-600 rounded-full** — контрастнее текущего `bg-orange-500 rounded`, ярче читается на фото
- **Три отдельных PROMO_STICKER_*** — grid и list мельче фото, presentation крупнее; унифицировать в один класс нельзя без потери пропорций
- **Текст «🔥 Акция»** — иконка + слово; минимальная нагрузка, максимальная видимость

## Deviations from Plan

Нет — план выполнен точно как написан.

## Issues Encountered

Нет. Build прошёл с первой попытки.

## Checkpoint: Ожидает приёмки на проде (Task 2)

**Статус:** Код завершён и закоммичен. Ручная приёмка на Vercel — ОЖИДАЕТ деплоя.

Поскольку `badges.json` ключ `"акция"` сейчас пуст (D-11), для приёмки нужно временно отметить один товар акцией. После `git push`:

1. Открыть каталог, найти товар с меткой «акция».
2. В сетке и презентации — стикер «🔥 Акция» заметно крупнее/ярче, в левом углу фото.
3. Стикер НЕ перекрывает название и цену; не налезает на угловые кнопки справа.
4. Режим «без фото» — стикер над названием.
5. Режим списка — стикер в правом верхнем углу строки.
6. Товары «хит» и «NEW» выглядят как раньше.

Напишите «принято» или укажите желаемый текст/цвет/размер стикера.

## Next Phase Readiness

- MERCH-01 реализован; стикер готов — появится сразу, как владелец отметит товары акцией в `badges.json`
- Этап 17 полностью завершён (план 17-01 + 17-02); деплой — `git push`
- MERCH-02 (зачёркнутая старая цена) остаётся отложенной — нет поля «старая цена» в данных

---
*Phase: 17-card-promo-photo*
*Completed: 2026-06-28*
