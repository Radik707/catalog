---
phase: 14-install-prompt-android-ios
plan: "01"
subsystem: pwa-install
tags: [pwa, install-prompt, react-context, hooks]
dependency_graph:
  requires: []
  provides: [lib/useInstallPrompt.ts, components/InstallPromptProvider.tsx]
  affects: [plan-02-install-ui]
tech_stack:
  added: []
  patterns: [react-context-provider, sse-safe-hooks, localStorage-try-catch]
key_files:
  created:
    - lib/useInstallPrompt.ts
    - components/InstallPromptProvider.tsx
  modified: []
decisions:
  - "useInstallPrompt перехватывает beforeinstallprompt через addEventListener в useEffect — событие в ref (не state) чтобы promptInstall имел доступ без лишних ре-рендеров"
  - "Сигнал вовлечённости: таймер 25с ИЛИ скролл ≥100px — flag engagementFired защищает от двойного срабатывания"
  - "localStorage обёрнут в try/catch во всех точках — деградация к «показать как обычно» в приватном режиме iOS (T-14-01)"
  - "InstallPromptProvider по паттерну CatalogSyncProvider — один вызов хука, контекст раздаёт результат"
metrics:
  duration: "~5 мин"
  completed: "2026-06-13"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 0
---

# Phase 14 Plan 01: useInstallPrompt + InstallPromptProvider Summary

**Одной строкой:** Клиентский хук детекта платформы установки (android/ios/installed/unsupported) с перехватом `beforeinstallprompt`, сигналом вовлечённости и провайдером единого экземпляра через React-контекст.

## Что сделано

### Task 1: Хук useInstallPrompt

Создан `lib/useInstallPrompt.ts` — центральный детектор платформы и состояния подсказки об установке.

**Логика детекта:**
- `standalone` (D-04): `matchMedia('(display-mode: standalone)')` ИЛИ `navigator.standalone === true` → platform="installed"
- iOS Safari (D-03): UA `/iPhone|iPad|iPod/` И не standalone → platform="ios"
- Android (D-02): подписка на `beforeinstallprompt` → `preventDefault()` → сохранение события в `deferredPromptRef` → platform="android", canPromptAndroid=true

**Сигнал вовлечённости (D-01):**
- Таймер 25 секунд ИЛИ скролл ≥100px (флаг `engagementFired` исключает двойное срабатывание)
- `engaged=true` переводит UI в состояние «можно показать баннер»

**localStorage (D-04, T-14-01):**
- Ключ `pwa-install-dismissed`; чтение при монтировании, запись в `dismiss()`
- Оба обращения в try/catch — защита от приватного режима iOS

**Cleanup:** снятие всех подписок (`beforeinstallprompt`, `scroll`) и таймера в return-функции useEffect.

**Экспорты:** тип `InstallPlatform`, интерфейс `UseInstallPromptResult`, функция `useInstallPrompt()`

### Task 2: InstallPromptProvider

Создан `components/InstallPromptProvider.tsx` — провайдер единого экземпляра хука.

- `InstallPromptContext = createContext<UseInstallPromptResult | null>(null)`
- `useInstallPromptContext()` — хук-потребитель с русской ошибкой при использовании вне провайдера
- `InstallPromptProvider` — компонент-обёртка с единственным вызовом `useInstallPrompt()` внутри
- Паттерн полностью совпадает с `CatalogSyncProvider` (этап 13)

## Коммиты

| Хэш | Описание |
|-----|----------|
| 3eb9ed5 | feat(этап-14): хук useInstallPrompt + провайдер InstallPromptProvider |

## Проверки

- Grep-проверка Task 1: OK (beforeinstallprompt, preventDefault, display-mode: standalone, pwa-install-dismissed, try, catch, useInstallPrompt)
- Grep-проверка Task 2: OK (use client, createContext, useInstallPromptContext, InstallPromptProvider, useInstallPrompt)
- `npm run build`: ✓ без ошибок TypeScript

## Deviations from Plan

None — план выполнен точно как написан.

## Threat Flags

Нет новой сетевой поверхности или точек входа. Угрозы T-14-01 и T-14-02 обработаны согласно плану: T-14-01 (localStorage в приватном режиме iOS) смягчён через try/catch во всех точках; T-14-02 (beforeinstallprompt живёт в памяти вкладки) — accepted.

## Self-Check: PASSED

- [x] `C:/catalog/lib/useInstallPrompt.ts` — существует, 165 строк > min_lines 60
- [x] `C:/catalog/components/InstallPromptProvider.tsx` — существует, 56 строк > min_lines 30
- [x] Коммит 3eb9ed5 — подтверждён
- [x] `npm run build` — проходит без ошибок
- [x] Никакие существующие файлы не изменены
