---
phase: 15-role-sales-client
plan: "01"
subsystem: role-context
tags: [role, context, localStorage, SSR-safe, settings]
dependency_graph:
  requires: []
  provides: [lib/useRole.tsx, RoleProvider, useRole]
  affects: [components/SettingsPanel.tsx, app/catalog/[secret]/layout.tsx]
tech_stack:
  added: []
  patterns: [context+provider (CatalogSettings.tsx), SSR-safe ready-flag (useDeviceClass.ts), persist-setter, segment-toggle]
key_files:
  created:
    - lib/useRole.tsx
  modified:
    - app/catalog/[secret]/layout.tsx
    - components/SettingsPanel.tsx
decisions:
  - "lib/useRole.tsx создан как .tsx (не .ts) — содержит JSX для RoleCtx.Provider; tsconfig включает **/*.tsx"
  - "Дефолт роли всегда 'client' через useState('client'), без автоопределения по устройству (D-02)"
  - "Валидация при чтении localStorage: принимать только строго 'sales'/'client' (STRIDE T-15-01)"
  - "RoleProvider монтируется снаружи CatalogSettingsProvider — CatalogSettings читает роль при init (D-10)"
  - "setReady(true) вызывается последней строкой useEffect — паттерн useDeviceClass (D-04)"
metrics:
  duration: "~10 мин"
  completed: "2026-06-27"
  tasks_completed: 3
  files_created: 1
  files_modified: 2
requirements_fulfilled: [ROLE-01, ROLE-02, ROLE-04]
---

# Phase 15 Plan 01: Ядро роли (useRole + RoleProvider + переключатель) Summary

**Одной строкой:** Хук-контекст `useRole` с persist в localStorage, SSR-safe `ready`-флагом и переключателем «Клиент | Агент» первым элементом панели настроек.

## Что сделано

### Task 1 — Создан lib/useRole.tsx
Новый файл с директивой `"use client"`. Экспортирует:
- `UserRole = "sales" | "client"` — тип роли
- `useRole()` — именованный хук с guard-бросанием вне провайдера
- `RoleProvider` (default export) — провайдер с persist и SSR-safe флагом

Ключевые детали реализации:
- `useState<UserRole>("client")` — дефолт всегда `client` (D-02)
- `setRole(r)` — persist-обёртка: `setRoleState(r) + localStorage.setItem("userRole", r)`
- `useEffect`: читает `localStorage.getItem("userRole")`, применяет **только** если строго `"sales"` или `"client"`, затем `setReady(true)` последней строкой
- Файл `.tsx` (не `.ts`) — содержит JSX для `<RoleCtx.Provider>`

### Task 2 — Смонтирован RoleProvider в layout.tsx
В `app/catalog/[secret]/layout.tsx` добавлен `import RoleProvider from "@/lib/useRole"`. RoleProvider монтируется **снаружи** CatalogSettingsProvider — верхний провайдер в дереве, чтобы план 15-02 мог дать CatalogSettings доступ к роли при init.

Дерево после изменения:
```
RoleProvider
  └── CatalogSettingsProvider
        └── NavProvider → CatalogSyncProvider → InstallPromptProvider → ...
```

### Task 3 — Переключатель «Клиент | Агент» в SettingsPanel
В `components/SettingsPanel.tsx` добавлены:
- `import { useRole } from "@/lib/useRole"`
- `const { role, setRole } = useRole()` в теле компонента
- Блок «Роль» с кнопками «Клиент» / «Агент» — **первый** дочерний элемент контейнера `flex flex-wrap` (D-07)

Стиль скопирован с сегмента «Форма 1-я/2-я» (D-06): подпись «Роль» слева + `flex rounded-lg overflow-hidden border` + активная кнопка `bg-blue-500 text-white`.

## Требования

| ID | Статус | Реализация |
|----|--------|-----------|
| ROLE-01 | ВЫПОЛНЕНО | `useState("client")` — дефолт всегда client, без автоопределения |
| ROLE-02 | ВЫПОЛНЕНО | persist-обёртка `setRole`: localStorage.setItem("userRole", r) |
| ROLE-04 | ВЫПОЛНЕНО | `ready=false` до монтирования, `setReady(true)` в useEffect |

## Коммиты

| Task | Хэш | Сообщение |
|------|-----|-----------|
| 1 | 60ad9dc | feat(этап-15): создать lib/useRole.tsx |
| 2 | a6aee75 | feat(этап-15): монтаж RoleProvider в layout |
| 3 | a514f9a | feat(этап-15): переключатель «Клиент|Агент» в SettingsPanel |

## Deviations from Plan

### Отклонение от плана: расширение файла .tsx вместо .ts

- **Найдено во время:** Task 1
- **Причина:** Файл содержит JSX (`<RoleCtx.Provider>`). TypeScript-компилятор отказывается компилировать JSX в `.ts`-файлах (ошибка TS1005 `'>' expected`)
- **Решение:** Создан `lib/useRole.tsx` вместо `lib/useRole.ts`. tsconfig.json включает `**/*.tsx`, поэтому файл подхватывается. Все импорты в других файлах используют `@/lib/useRole` без расширения — Next.js резолвит автоматически
- **Влияние:** Нулевое — стандартная практика для файлов с JSX в TypeScript-проектах

## Known Stubs

Стабов нет — переключатель полностью функционален, данные пишутся в localStorage и читаются обратно при монтировании.

## Threat Flags

Новых угроз сверх threat_model плана не обнаружено. Поверхность атаки минимальна: роль — локальная UI-настройка, нет сетевых эндпоинтов.

## Self-Check: PASSED

- lib/useRole.tsx существует: FOUND
- app/catalog/[secret]/layout.tsx содержит RoleProvider: FOUND
- components/SettingsPanel.tsx содержит setRole: FOUND
- Коммит 60ad9dc: FOUND
- Коммит a6aee75: FOUND
- Коммит a514f9a: FOUND
- npm run build: PASSED (3 динамических маршрута, без ошибок)
