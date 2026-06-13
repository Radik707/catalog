---
phase: 14-install-prompt-android-ios
reviewed: 2026-06-13T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - app/catalog/[secret]/layout.tsx
  - app/layout.tsx
  - components/InstallPrompt.tsx
  - components/InstallPromptProvider.tsx
  - components/SettingsPanel.tsx
  - lib/useInstallPrompt.ts
findings:
  critical: 1
  warning: 5
  info: 3
  total: 9
status: issues_found
---

# Этап 14: Отчёт по код-ревью

**Проверено:** 2026-06-13
**Глубина:** standard
**Файлов проверено:** 6
**Статус:** найдены проблемы

## Резюме

Проверена реализация подсказки об установке PWA (баннер Android, нижняя шторка-инструкция iOS, кнопка в настройках). Архитектура с провайдером и единым экземпляром `useInstallPrompt` выбрана верно — она решает реальную проблему одноразового события `beforeinstallprompt`. SSR-безопасность соблюдена, `try/catch` вокруг `localStorage` — на месте.

Однако есть один блокер (анимация iOS-шторки молча не работает, потому что keyframes `slideUp` нигде не объявлены) и несколько серьёзных предупреждений: перекрытие баннера и плавающей кнопки Telegram по одному z-index, кнопка-«пустышка» в настройках на Android, и расхождение комментария с кодом в `openFromSettings`.

**Что это значит:** код в целом написан грамотно и аккуратно, но в текущем виде до отправки в прод нужно поправить блокер с анимацией и разобраться с наложением кнопки Telegram на баннер — иначе на iPhone шторка появится без анимации, а кнопка «Установить»/крестик будут частично перекрыты круглой кнопкой Telegram.

## Critical Issues

### CR-01: Анимация iOS-шторки `slideUp` не определена — шторка появляется без анимации

**File:** `components/InstallPrompt.tsx:121`
**Issue:** В классах iOS-шторки используется `animate-[slideUp_0.25s_ease-out]`, но keyframes `slideUp` нигде не объявлены. Проверка показала, что `@keyframes slideUp` отсутствует и в `app/globals.css`, и в `tailwind.config.ts` (там `theme.extend` пустой — `{}`). Tailwind в arbitrary-значении `animate-[slideUp_...]` подставит имя анимации `slideUp`, но браузер не найдёт соответствующих keyframes и проигнорирует анимацию целиком. В результате заявленная плавность появления шторки на iOS (ключевая часть UX этого этапа) молча не работает — шторка просто мгновенно «прыгает» снизу. Это дефект корректности: реализованная фича не делает того, что декларирует, и об этом нельзя узнать без ручного теста на iPhone.

**Fix:** Объявить keyframes. В `app/globals.css`:
```css
@keyframes slideUp {
  from { transform: translateY(100%); }
  to   { transform: translateY(0); }
}
```
Либо добавить в `tailwind.config.ts`:
```ts
theme: {
  extend: {
    keyframes: {
      slideUp: { from: { transform: "translateY(100%)" }, to: { transform: "translateY(0)" } },
    },
    animation: { slideUp: "slideUp 0.25s ease-out" },
  },
},
```
во втором случае класс упростится до `animate-slideUp`.

## Warnings

### WR-01: Баннер установки и плавающая кнопка Telegram перекрываются (один z-index, оба снизу)

**File:** `components/InstallPrompt.tsx:69,121` и `components/TelegramButton.tsx:55`
**Issue:** Баннер Android и iOS-шторка позиционированы `fixed bottom-0 left-0 right-0 z-50`. Плавающая кнопка Telegram — `fixed bottom-6 right-4 z-50`. Они отрисованы в одном поддереве (`InstallPromptProvider` оборачивает в т.ч. `<TelegramButton />`, см. `layout.tsx:66,76`) и имеют одинаковый `z-50`. Когда баннер/шторка видны, круглая кнопка Telegram (56×56 px, в правом нижнем углу) накладывается на правую часть баннера — а именно туда попадают кнопка «Установить» и крестик «Позже» в Android-баннере. Какой элемент окажется сверху, зависит от порядка в DOM, но в любом случае часть интерактивных контролов будет перекрыта/некликабельна.

**Fix:** Когда баннер/шторка видимы, либо прятать кнопку Telegram, либо приподнимать её над баннером. Простейший вариант — поднять баннер выше по z-index и сдвинуть FAB, либо скрыть FAB при открытом баннере (прокинуть признак видимости через контекст). Минимально: задать баннеру `z-[60]` и добавить кнопке Telegram нижний отступ/скрытие, когда `platform` allows install и баннер показан.

### WR-02: На Android кнопка «Установить приложение» в настройках может быть «пустышкой»

**File:** `components/SettingsPanel.tsx:120-134` и `lib/useInstallPrompt.ts:189-209,232-240`
**Issue:** Кнопка «Установить приложение» в настройках показывается при `platform === "android"` независимо от `canPromptAndroid`. Нажатие вызывает `openFromSettings()` → `promptInstall()`. Но `promptInstall` первым делом делает `if (!prompt) return;` — то есть если событие `beforeinstallprompt` ещё не пришло, либо уже было использовано (`deferredPromptRef.current = null` после первого вызова), нажатие на кнопку молча ничего не делает. Пользователь («вайбкодеру»-владельцу и тем более рознице) видит активную кнопку, жмёт — и ничего не происходит, без обратной связи. После первой установки/попытки `canPromptAndroid` становится `false`, а кнопка остаётся.

**Fix:** Скрывать/блокировать кнопку на Android, когда нечего вызывать: условие показа `platform === "android" && canPromptAndroid` (для Android), а для iOS — как есть. Либо при `!deferredPromptRef.current` на Android показывать инструкцию-фолбэк. Пример условия:
```tsx
{!isStandalone && ((platform === "android" && canPromptAndroid) || platform === "ios") && (
```

### WR-03: Комментарий в `openFromSettings` противоречит коду (dismissed не сбрасывается)

**File:** `lib/useInstallPrompt.ts:233-235`
**Issue:** Комментарий гласит «Сбрасываем dismissed чтобы dismiss() из шторки мог снова его поставить», но код сбрасывает не `dismissed`, а ставит `forceOpen=true` (`setForceOpen(true)`), а `setDismissed(false)` не вызывается. Фактически логика работает (в `InstallPrompt` ветка iOS показывается при `forceOpen` даже если `dismissed`), но комментарий вводит в заблуждение и описывает несуществующее действие. При дальнейшей правке кто-то может «починить» код по комментарию и сломать поведение. Кроме того, флаг `dismissed` в `localStorage` остаётся `"1"` навсегда — если потом понадобится логика, опирающаяся на «свежий» dismissed, она будет рассогласована.

**Fix:** Привести комментарий в соответствие с кодом, например: «Не сбрасываем dismissed — вместо этого ставим forceOpen=true; ветка iOS в InstallPrompt показывается при forceOpen даже когда dismissed». Либо, если задумывался реальный сброс, добавить `setDismissed(false)` и `localStorage.removeItem(DISMISSED_KEY)`.

### WR-04: iOS-детект ловит iPad на iPadOS 13+ ложно-отрицательно

**File:** `lib/useInstallPrompt.ts:136-142`
**Issue:** iOS определяется как `/iPhone|iPad|iPod/.test(navigator.userAgent)`. Начиная с iPadOS 13 Safari на iPad по умолчанию отдаёт desktop-UA (строку с `Macintosh`, без `iPad`). Такие iPad не будут распознаны как `ios`, попадут в `unsupported`, и пользователь iPad никогда не увидит инструкцию по установке. Поскольку аудитория — владельцы магазинов с планшетами, это реальный пропуск целевого устройства.

**Fix:** Дополнить детект проверкой тач-Mac (характерно для iPadOS):
```ts
const isIpadOS =
  navigator.maxTouchPoints > 1 && /Macintosh/.test(ua);
const isIosSafari = /iPhone|iPad|iPod/.test(ua) || isIpadOS;
```

### WR-05: iOS-детект не отсекает не-Safari браузеры — инструкция «Поделиться» там неверна

**File:** `lib/useInstallPrompt.ts:136-142`
**Issue:** На iOS Chrome/Edge/Firefox используют WebKit, и их UA тоже содержит `iPhone`/`iPad`. Они будут определены как `platform === "ios"` и получат инструкцию «Нажмите Поделиться → На экран Домой». Но в сторонних браузерах на iOS установка PWA либо невозможна, либо делается иначе — инструкция будет вводить пользователя в заблуждение (он не найдёт нужного пункта). Установка «На экран Домой» корректно работает именно в Safari.

**Fix:** Ограничить ветку iOS именно Safari, исключив CriOS/FxiOS/EdgiOS/OPiOS:
```ts
const isRealSafari = !/CriOS|FxiOS|EdgiOS|OPiOS|GSA/.test(ua);
if (/iPhone|iPad|iPod/.test(ua) && isRealSafari) { setPlatform("ios"); }
```
Для не-Safari iOS оставить `unsupported` (или показывать иную подсказку «откройте в Safari»).

## Info

### IN-01: Сигнал вовлечённости по таймеру не очищается при срабатывании скролла (мелкая неэффективность)

**File:** `lib/useInstallPrompt.ts:157-176`
**Issue:** При срабатывании скролла `fireEngagement()` ставит `engagementFired=true` и `setEngaged(true)`, но `timer` (25 c) не очищается немедленно — он сработает позже и вызовет `fireEngagement()` повторно, где сразу выйдет по `if (engagementFired) return;`. Поведение корректное, но лишний таймер висит до cleanup/срабатывания. Аналогично, слушатель `scroll` не снимается после срабатывания (остаётся до размонтирования). Не баг, но можно прибраться.
**Fix:** В `fireEngagement()` после установки флага вызвать `clearTimeout(timer)` и `window.removeEventListener("scroll", handleScroll)` (вынести ссылки в замыкание).

### IN-02: Неиспользуемые поля контекста у потребителей — мелкий шум

**File:** `components/InstallPrompt.tsx:25-34`
**Issue:** Деструктуризация в `InstallPrompt` берёт `forceOpen` и `canPromptAndroid`, что корректно, но стоит перепроверить, что все вытащенные поля реально используются во всех ветках. Это не дефект, а замечание к читаемости: набор полей контекста большой, и при дальнейших правках легко рассинхронизировать.
**Fix:** Оставить как есть либо сгруппировать связанные поля. Действий не требуется.

### IN-03: Магическое значение высоты шапки продублировано как `top-12`

**File:** `components/SettingsPanel.tsx:48` (и `layout.tsx:51` — `h-12`)
**Issue:** Высота шапки задана как `h-12` в layout и продублирована как `top-12` в `SettingsPanel` с комментарием «высота шапки 48px». Если высоту шапки изменят, панель настроек «отъедет» — связь между значениями только в комментарии.
**Fix:** Не критично для этого этапа. При случае вынести высоту шапки в общую константу/CSS-переменную, чтобы панель позиционировалась относительно неё.

---

_Проверено: 2026-06-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Глубина: standard_
