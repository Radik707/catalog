---
phase: 15-role-sales-client
plan: "02"
subsystem: role-ux-branching
tags: [role, isTabletLike, HeaderPrimaryAction, CardCornerButton, CatalogSettings, useDeviceClass]
dependency_graph:
  requires: [lib/useRole.tsx]
  provides: [HeaderPrimaryAction (role-aware), CardCornerButton (role-aware), CatalogSettings (role-default-grid)]
  affects: [components/HeaderPrimaryAction.tsx, components/CardCornerButton.tsx, components/CatalogSettings.tsx]
tech_stack:
  added: []
  patterns: [role-branching (role === "sales"), localStorage direct read for sync useEffect]
key_files:
  created: []
  modified:
    - components/HeaderPrimaryAction.tsx
    - components/CardCornerButton.tsx
    - components/CatalogSettings.tsx
  deleted:
    - lib/useDeviceClass.ts
decisions:
  - "HeaderPrimaryAction: ready-флаг сохранён — SyncButton и FavoritesIcon заметно разные визуально, мелькание нежелательно"
  - "CardCornerButton: ready не деструктурируется — дефолт до монтирования client=сердечко является корректным безопасным поведением"
  - "CatalogSettings: роль читается из localStorage напрямую (не через useRole()), потому что useEffect синхронный и оба эффекта монтируются независимо"
  - "useDeviceClass удалён (D-05): grep подтвердил отсутствие активных потребителей; восстановим из git при необходимости"
metrics:
  duration: "~8 мин"
  completed: "2026-06-27"
  tasks_completed: 2
  files_created: 0
  files_modified: 3
  files_deleted: 1
requirements_fulfilled: [ROLE-03]
---

# Phase 15 Plan 02: Перенос ветвлений isTabletLike → role Summary

**Одной строкой:** Три точки ветвления UI (шапка, угол карточки, дефолт сетки) переведены с типа устройства (`isTabletLike`) на роль (`role === "sales"`); файл `useDeviceClass.ts` удалён как безпотребительный.

## Что сделано

### Task 1 — HeaderPrimaryAction и CardCornerButton на роль

**`components/HeaderPrimaryAction.tsx`** (было 17 строк → 18 строк):
- Заменён импорт `useDeviceClass` из `@/lib/useDeviceClass` на `useRole` из `@/lib/useRole`
- `const { isTabletLike, ready } = useDeviceClass()` → `const { role, ready } = useRole()`
- Возвращаемый тернарник: `isTabletLike ? <SyncButton />` → `role === "sales" ? <SyncButton />`
- Ветка `if (!ready) return <div className="h-9 w-9" />` сохранена без изменений
- Обновлён комментарий-шапка: «устройство» → «роль», «планшет/телефон» → «sales/client»

**`components/CardCornerButton.tsx`** (без изменения количества строк):
- Заменён импорт `useDeviceClass` на `useRole`
- `const { isTabletLike } = useDeviceClass()` → `const { role } = useRole()` (ready не деструктурируется)
- Условие: `if (isTabletLike && canOpenPhoto)` → `if (role === "sales" && canOpenPhoto)`
- Обновлены комментарии: «Планшет с фото» → «Агент (sales) с фото», «Телефон/ПК» → «Клиент»

### Task 2 — Дефолт gridPreset по роли + удаление useDeviceClass

**`components/CatalogSettings.tsx`** (блок строк 107–115 заменён):

Было:
```typescript
} else if (window.matchMedia && window.matchMedia("(max-width: 767px)").matches) {
  setGridPreset("2x3");
}
```

Стало:
```typescript
} else {
  // Дефолт по роли (D-10): sales → 3x4, client/прочее → 2x3.
  // Читаем роль напрямую из localStorage (не через useRole()), потому что
  // этот useEffect выполняется синхронно при монтировании независимо от
  // контекста роли — RoleProvider может ещё не применить сохранённое значение.
  const savedRole = localStorage.getItem("userRole");
  setGridPreset(savedRole === "sales" ? "3x4" : "2x3");
}
```

Приоритет: сохранённый `gridPreset` по-прежнему проверяется первым (`p === "2x3" || ...`); дефолт по роли применяется только при его отсутствии.

**`lib/useDeviceClass.ts` — удалён** (D-05):
- grep по `*.ts, *.tsx` (исключая `.next/`, `node_modules/`) нашёл только комментарии в `lib/useRole.tsx` (упоминание паттерна) — активных импортов нет
- Файл удалён командой `git rm lib/useDeviceClass.ts`
- При необходимости восстанавливается из `git show 62c5115~1:lib/useDeviceClass.ts`

## Требования

| ID | Статус | Реализация |
|----|--------|-----------|
| ROLE-03 | ВЫПОЛНЕНО | Угловое действие карточки, главное действие в шапке и дефолтная плотность сетки следуют роли, а не типу устройства |

## Коммиты

| Task | Хэш | Сообщение |
|------|-----|-----------|
| 1 | 7eabf34 | feat(этап-15): перевести HeaderPrimaryAction и CardCornerButton на роль |
| 2 | 62c5115 | feat(этап-15): дефолт gridPreset по роли; удалить useDeviceClass |

## Deviations from Plan

None — план выполнен точно как описан. useDeviceClass удалён (путь D-05 «Claude's Discretion» — удаление предпочтительнее спящего файла).

## Known Stubs

Стабов нет — все три ветвления полностью функциональны. Переключение роли в SettingsPanel (план 15-01) немедленно меняет поведение шапки, угла карточки и задаёт дефолт сетки.

## Threat Flags

Угрозы T-15-04 (Tampering, CatalogSettings чтение userRole) митигирована: любое значение userRole кроме `"sales"` трактуется как client (2x3) — `savedRole === "sales" ? "3x4" : "2x3"`. Повреждённое значение безопасно деградирует в клиентский вид.

Новых угроз сверх threat_model плана не обнаружено.

## Self-Check: PASSED

- components/HeaderPrimaryAction.tsx содержит `import { useRole } from "@/lib/useRole"`: FOUND
- components/HeaderPrimaryAction.tsx НЕ содержит `isTabletLike`: CONFIRMED (0 совпадений)
- components/HeaderPrimaryAction.tsx НЕ содержит `useDeviceClass`: CONFIRMED (0 совпадений)
- components/HeaderPrimaryAction.tsx содержит `role === "sales"`: FOUND
- components/HeaderPrimaryAction.tsx содержит `if (!ready) return`: FOUND
- components/CardCornerButton.tsx содержит `import { useRole } from "@/lib/useRole"`: FOUND
- components/CardCornerButton.tsx НЕ содержит `isTabletLike`: CONFIRMED (0 совпадений)
- components/CardCornerButton.tsx НЕ содержит `useDeviceClass`: CONFIRMED (0 совпадений)
- components/CardCornerButton.tsx содержит `role === "sales" && canOpenPhoto`: FOUND
- components/CatalogSettings.tsx содержит `localStorage.getItem("userRole")`: FOUND
- components/CatalogSettings.tsx содержит `setGridPreset(savedRole === "sales" ? "3x4" : "2x3")`: FOUND
- components/CatalogSettings.tsx НЕ содержит `matchMedia("(max-width: 767px)")`: CONFIRMED (0 совпадений)
- lib/useDeviceClass.ts: удалён (CONFIRMED — файл отсутствует)
- npm run build: PASSED (exit 0, все 7 страниц сгенерированы)
- Коммит 7eabf34: FOUND
- Коммит 62c5115: FOUND
