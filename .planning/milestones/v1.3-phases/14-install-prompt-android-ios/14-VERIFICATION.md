---
phase: 14-install-prompt-android-ios
verified: 2026-06-13T00:00:00Z
status: human_needed
score: 7/9 must-haves verified
overrides_applied: 0
deferred:
  - truth: "На реальном iPhone bottom-sheet понятен без технических знаний (критерий #2)"
    addressed_in: "Конец вехи v1.3 — финальная iPhone-приёмка"
    evidence: "STATE.md → «Отложенные элементы»: «PWA-02 iPhone-приёмка Install Prompt (этап 14, критерии #2/#5) — Отложена. Перед сдачей вехи v1.3». Явный чекпойнт в 14-03-PLAN.md Task 2 (checkpoint:human-verify), сигнал «отложено» оформлен штатно по образцу этапов 11/12/13."
  - truth: "Установка каталога на домашний экран iPhone через Safari → запуск в standalone без браузерной строки (критерий #5)"
    addressed_in: "Конец вехи v1.3 — финальная iPhone-приёмка"
    evidence: "Та же запись в STATE.md. Критерий явно заявлен в 14-03-SUMMARY.md как отложенный, все авто-критерии (#1, #3, #4) закрыты кодом."
human_verification:
  - test: "Открыть каталог в Safari на реальном iPhone → подождать ~25 с или прокрутить список → должна появиться нижняя шторка с инструкцией «Нажмите Поделиться → На экран Домой»"
    expected: "Шторка появляется, текст понятен без технических знаний, шаги 1-2-3 читаются без затруднений"
    why_human: "Невозможно проверить программно: требует реального iOS-устройства + Safari + визуальная оценка понятности текста"
  - test: "Закрыть шторку («Понятно, позже») → перезагрузить страницу → убедиться, что шторка НЕ появляется автоматически"
    expected: "Шторка не появляется (localStorage-флаг pwa-install-dismissed сохранился)"
    why_human: "Требует реального устройства; поведение localStorage в Safari нельзя достоверно симулировать"
  - test: "Настройки (шестерёнка) → «Установить приложение» → шторка-инструкция открывается снова"
    expected: "forceOpen=true перекрывает dismissed; шторка показывается принудительно"
    why_human: "Требует реального устройства"
  - test: "Установить каталог на домашний экран → запустить с домашнего экрана → проверить отсутствие адресной строки Safari и корректный safe-area (нижнее содержимое не под чёлкой)"
    expected: "Приложение открывается в standalone, viewport-fit=cover активен, нижние острова (OfflineBar, баннер) не уходят под системную зону"
    why_human: "Требует реального iPhone с чёлкой + ручной установки"
  - test: "В standalone-режиме открыть настройки → пункт «Установить приложение» должен отсутствовать"
    expected: "Пункт скрыт (isStandalone=true, условие !isStandalone → false)"
    why_human: "Требует standalone-режима, который недостижим без реального устройства"
---

# Этап 14: Install Prompt (Android + iOS) — Отчёт верификации

**Цель этапа:** Агент (владелец магазина) получает подсказку об установке каталога на домашний экран — баннер на Android, понятная инструкция «Поделиться → На экран Домой» на iPhone; промпт однократный; корректное standalone-отображение.

**Проверено:** 2026-06-13
**Статус:** human_needed (все авто-критерии пройдены; iPhone-приёмка отложена штатно)
**Повторная верификация:** Нет — первоначальная проверка

---

## Цель этапа: достигнута по авто-критериям

Вся клиентская реализация существует в коде, компилируется, смонтирована в layout. Два отложенных критерия (#2 и #5) требуют реального iPhone и зафиксированы как штатная отложенная приёмка конца вехи v1.3 — по образцу этапов 11/12/13.

---

## Наблюдаемые утверждения (Truths)

| # | Утверждение | Статус | Доказательство |
|---|-------------|--------|----------------|
| 1 | Хук различает три платформы: android (beforeinstallprompt), ios (UA-детект), installed (standalone) | ✓ VERIFIED | `lib/useInstallPrompt.ts` строки 110–151: matchMedia + navigator.standalone → "installed"; /iPhone\|iPad\|iPod/ → "ios"; beforeinstallprompt listener → "android" |
| 2 | Перехваченное beforeinstallprompt сохраняется в одном экземпляре через контекст | ✓ VERIFIED | `deferredPromptRef` (ref, не state) в хуке; `InstallPromptProvider` вызывает хук единожды и раздаёт через Context; баннер и SettingsPanel читают через `useInstallPromptContext()` |
| 3 | Флаг dismissed читается/пишется в localStorage с try/catch | ✓ VERIFIED | `lib/useInstallPrompt.ts:125–133` (чтение при монтировании) и `216–225` (запись в dismiss()) — оба в try/catch; ключ `pwa-install-dismissed` |
| 4 | Сигнал вовлечённости: таймер 25с ИЛИ скролл ≥100px → engaged=true | ✓ VERIFIED | `lib/useInstallPrompt.ts:157–183`: setTimeout(25000) и window scroll с порогом SCROLL_THRESHOLD=100; флаг engagementFired исключает двойное срабатывание; cleanup снимает оба слушателя |
| 5 | Android-баннер показывается по сигналу вовлечённости; кнопка «Установить» вызывает promptInstall() | ✓ VERIFIED | `components/InstallPrompt.tsx:43–113`: условие `canPromptAndroid && engaged && !dismissed`; кнопка onClick → `promptInstall()`; крестик → `dismiss()` |
| 6 | iOS bottom-sheet показывает пошаговую инструкцию «Поделиться → На экран Домой» | ✓ VERIFIED | `components/InstallPrompt.tsx:118–213`: три шага с синими кружками, текст «Нажмите кнопку «Поделиться»», «На экран "Домой"»», «Нажмите «Добавить»»; SVG-иконка Поделиться; кнопка «Понятно, позже» → dismiss() |
| 7 | InstallPromptProvider обёртывает дерево каталога; InstallPrompt смонтирован рядом с OfflineBar | ✓ VERIFIED | `app/catalog/[secret]/layout.tsx:47,66`: `<InstallPromptProvider>` охватывает header, OfflineBar, SettingsPanel и main; `<InstallPrompt />` на строке 66, сразу после `<OfflineBar />` строка 63 |
| 8 | SettingsPanel содержит «Установить приложение», скрыт в standalone, на Android gated canPromptAndroid | ✓ VERIFIED | `components/SettingsPanel.tsx:126–142`: условие `!isStandalone && (platform === "ios" \|\| (platform === "android" && canPromptAndroid))`; кнопка «Установить приложение» с иконкой 📲 |
| 9 | app/layout.tsx содержит единственный export viewport с viewportFit: "cover" | ✓ VERIFIED | `app/layout.tsx:30–36`: ровно один `export const viewport: Viewport` со `themeColor: "#2563eb"` и `viewportFit: "cover"` |

**Счёт:** 9/9 авто-утверждений верифицировано кодом

---

## Обязательные артефакты

| Артефакт | Ожидается | Статус | Детали |
|----------|-----------|--------|--------|
| `lib/useInstallPrompt.ts` | Хук, ≥60 строк | ✓ VERIFIED | 254 строки; "use client"; экспортирует `useInstallPrompt` и `UseInstallPromptResult` |
| `components/InstallPromptProvider.tsx` | Провайдер контекста, ≥30 строк | ✓ VERIFIED | 54 строки; createContext, useInstallPromptContext, InstallPromptProvider |
| `components/InstallPrompt.tsx` | Баннер + bottom-sheet, ≥60 строк | ✓ VERIFIED | 218 строк; Android и iOS ветки; fixed bottom-0 z-[60]; safe-area через inline style |
| `app/catalog/[secret]/layout.tsx` | Содержит InstallPrompt | ✓ VERIFIED | Строки 15–17: импорты; строки 47, 66: монтирование |
| `components/SettingsPanel.tsx` | Содержит «Установить приложение» | ✓ VERIFIED | Строки 10, 32, 126–142 |
| `app/layout.tsx` | viewportFit: "cover" | ✓ VERIFIED | Строка 35 |

---

## Ключевые связи (Key Links)

| От | К | Через | Статус | Детали |
|----|---|-------|--------|--------|
| `lib/useInstallPrompt.ts` | window beforeinstallprompt | addEventListener + preventDefault + deferredPromptRef | ✓ WIRED | Строки 146–153 |
| `components/InstallPromptProvider.tsx` | `lib/useInstallPrompt.ts` | единственный вызов useInstallPrompt() внутри провайдера | ✓ WIRED | Строка 47 |
| `components/InstallPrompt.tsx` | `components/InstallPromptProvider.tsx` | useInstallPromptContext() | ✓ WIRED | Строка 23 импорт, строка 26 вызов |
| `app/catalog/[secret]/layout.tsx` | `components/InstallPrompt.tsx` | `<InstallPrompt />` внутри `<InstallPromptProvider>` | ✓ WIRED | Строки 47 и 66 |
| `components/SettingsPanel.tsx` | `components/InstallPromptProvider.tsx` | useInstallPromptContext() | ✓ WIRED | Строка 10 импорт, строка 31 вызов |
| `app/layout.tsx` | env(safe-area-inset-*) в InstallPrompt | viewportFit: "cover" | ✓ WIRED | Строка 35; inline style paddingBottom в InstallPrompt.tsx строки 71, 123 |

---

## Трассировка данных (Level 4)

Компоненты рендерят состояние из React-хука (не из API/БД), поэтому полный data-flow trace:

| Компонент | Переменная | Источник | Данные реальные | Статус |
|-----------|------------|----------|-----------------|--------|
| `InstallPrompt.tsx` | platform, engaged, dismissed, forceOpen | useInstallPromptContext() → useInstallPrompt() → window events + localStorage | Да: браузерные события + localStorage | ✓ FLOWING |
| `SettingsPanel.tsx` | platform, isStandalone, canPromptAndroid | useInstallPromptContext() → единственный экземпляр хука | Да: тот же экземпляр | ✓ FLOWING |

---

## Проверка code review (REVIEW.md)

| Находка | Статус в коде | Доказательство |
|---------|---------------|----------------|
| CR-01: keyframes slideUp не объявлены | ✓ ИСПРАВЛЕНО | `app/globals.css:19–28`: @keyframes slideUp с from/to |
| WR-01: z-index конфликт баннера и Telegram (оба z-50) | ✓ ИСПРАВЛЕНО | `components/InstallPrompt.tsx:70,122`: z-[60] (выше Telegram z-50) |
| WR-02: Android кнопка в настройках без canPromptAndroid | ✓ ИСПРАВЛЕНО | `components/SettingsPanel.tsx:128`: условие включает `&& canPromptAndroid` |
| WR-03: вводящий в заблуждение комментарий в openFromSettings | ✓ ИСПРАВЛЕНО | `lib/useInstallPrompt.ts:233–236`: комментарий описывает forceOpen=true, не сброс dismissed |
| WR-04: iPadOS 13+ ложно-отрицательный UA | accepted (решение D-03) | Цель — телефон агента, а не iPad; принято сознательно |
| WR-05: iOS Chrome/Edge получают инструкцию «Поделиться» | accepted (решение D-03) | Принято сознательно; простая эвристика выбрана в решении |

---

## Антипаттерны

| Файл | Строка | Паттерн | Серьёзность | Влияние |
|------|--------|---------|-------------|---------|
| Нет | — | Нет TBD/FIXME/XXX/placeholder в изменённых файлах | — | — |

Проверены файлы: `lib/useInstallPrompt.ts`, `components/InstallPromptProvider.tsx`, `components/InstallPrompt.tsx`, `components/SettingsPanel.tsx`, `app/layout.tsx`, `app/catalog/[secret]/layout.tsx`, `app/globals.css`. Долговые маркеры не обнаружены.

---

## Покрытие требований

| Требование | Описание | Статус | Доказательство |
|------------|----------|--------|----------------|
| PWA-02 | На Android — подсказка об установке; на iPhone — инструкция «Поделиться → На экран Домой» | ЧАСТИЧНО (авто-критерии) | Android-баннер: код ✓. iOS-шторка: код ✓. Ручная iPhone-приёмка — отложена штатно |

---

## Поведенческие проверки (Spot-checks)

Поскольку логика полностью клиентская (браузерные события, localStorage) и не имеет серверных endpoint-ов, автоматические spot-checks ограничены статическим анализом:

| Поведение | Проверка | Результат | Статус |
|-----------|----------|-----------|--------|
| Ключ dismissed в localStorage | grep 'pwa-install-dismissed' | Найден в useInstallPrompt.ts:66 (константа) и строках 127, 222 | ✓ PASS |
| Единственный export viewport | node -e (regex count) | Ровно 1 match "export const viewport" в app/layout.tsx | ✓ PASS |
| viewportFit: "cover" | grep в layout.tsx | Строка 35 | ✓ PASS |
| beforeinstallprompt + preventDefault | grep в useInstallPrompt.ts | Строки 147–148 | ✓ PASS |
| try/catch вокруг localStorage | grep | Строки 125–133 (чтение), 219–224 (запись) | ✓ PASS |

---

## Отложенные элементы (Step 9b — по образцу этапов 11/12/13)

Два критерия явно отложены на конец вехи v1.3 как человеческая приёмка. Это штатное решение, зафиксированное в STATE.md.

| # | Элемент | Отложен до | Доказательство |
|---|---------|------------|----------------|
| 1 | Критерий #2: bottom-sheet на реальном iPhone понятен без технических знаний | Конец вехи v1.3 | STATE.md → «Отложенные элементы»: «PWA-02 iPhone-приёмка Install Prompt (этап 14, критерии #2/#5)»; 14-03-PLAN.md Task 2 (checkpoint:human-verify, сигнал «отложено» оформлен) |
| 2 | Критерий #5: установка на домашний экран через Safari → запуск в standalone | Конец вехи v1.3 | То же. 14-03-SUMMARY.md: «Task 2 отложена» с явной таблицей критериев |

---

## Ручная приёмка (требуется)

### 1. iOS: bottom-sheet инструкция (критерий #2)

**Тест:** Открыть секретную ссылку каталога в Safari на реальном iPhone → подождать ~25 с или прокрутить список → появляется нижняя шторка.
**Ожидаемое:** Три чётких шага с номерами: (1) «Нажмите Поделиться» + SVG-иконка, (2) «На экран "Домой"», (3) «Нажмите Добавить». Текст понятен без технических знаний.
**Почему человек:** Визуальная оценка читаемости и понятности на реальном устройстве; тест требует iOS + Safari.

### 2. iOS: однократность (критерий #3 на iPhone)

**Тест:** Закрыть шторку («Понятно, позже») → перезагрузить страницу → шторка не появляется автоматически.
**Ожидаемое:** localStorage-флаг pwa-install-dismissed сохраняется между сессиями Safari.
**Почему человек:** Поведение localStorage в Safari (включая приватный режим) нельзя достоверно верифицировать без устройства.

### 3. iOS: «Установить приложение» в настройках (критерий #3 на iPhone)

**Тест:** Шестерёнка → «Установить приложение» → шторка-инструкция открывается снова (forceOpen игнорирует dismissed).
**Ожидаемое:** Шторка появляется даже если ранее была закрыта.
**Почему человек:** Требует реального устройства и Safari.

### 4. Standalone: полный экран без адресной строки (критерий #4)

**Тест:** Следуя инструкции, установить каталог → запустить с домашнего экрана → проверить отсутствие адресной строки Safari и корректность safe-area (нижнее содержимое не под чёлкой).
**Ожидаемое:** Приложение открывается в полный экран; viewport-fit=cover обеспечивает правильные insets; баннер/шторка не уходят за системную зону.
**Почему человек:** Standalone-режим не достижим без реального устройства + установки.

### 5. Standalone: кнопка «Установить» скрыта (критерий #5)

**Тест:** Запустить с домашнего экрана → открыть настройки → пункт «Установить приложение» должен отсутствовать.
**Ожидаемое:** isStandalone=true, условие SettingsPanel скрывает кнопку.
**Почему человек:** Требует standalone-режима.

---

## Итого

Все 9 автоматически проверяемых утверждений подтверждены кодом. Код-ревью CR-01/WR-01/WR-02/WR-03 исправлены (коммит e7aff75). Два критерия (#2 и #5) требуют реального iPhone и отложены штатно, по образцу этапов 11/12/13, с записью в STATE.md.

Статус: **human_needed** — ожидается финальная iPhone-приёмка перед сдачей вехи v1.3.

---

_Проверено: 2026-06-13_
_Верификатор: Claude (gsd-verifier)_
