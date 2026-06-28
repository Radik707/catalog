# Phase 15: Роль «Торговый / Клиент» - Pattern Map

**Mapped:** 2026-06-27
**Files analyzed:** 6 (1 создать, 5 изменить)
**Analogs found:** 6 / 6

---

## File Classification

| Новый / изменяемый файл | Роль | Поток данных | Ближайший аналог | Качество совпадения |
|--------------------------|------|--------------|------------------|---------------------|
| `lib/useRole.ts` | hook/provider | event-driven (localStorage persist) | `components/CatalogSettings.tsx` + `lib/useDeviceClass.ts` | exact (оба аналога нужны одновременно) |
| `components/SettingsPanel.tsx` | component | request-response (UI toggle) | `components/SettingsPanel.tsx` строки 103–124 («Форма 1-я/2-я») | exact |
| `app/catalog/[secret]/layout.tsx` | layout/provider-mount | request-response | `app/catalog/[secret]/layout.tsx` (монтаж `CatalogSettingsProvider`) | exact |
| `components/HeaderPrimaryAction.tsx` | component | request-response | `components/HeaderPrimaryAction.tsx` (текущее ветвление `isTabletLike`) | exact |
| `components/CardCornerButton.tsx` | component | request-response | `components/CardCornerButton.tsx` (текущее ветвление `isTabletLike`) | exact |
| `components/CatalogSettings.tsx` | hook/provider | event-driven (localStorage persist) | `components/CatalogSettings.tsx` строки 107–115 (дефолт `gridPreset`) | exact |

---

## Pattern Assignments

### `lib/useRole.ts` (hook/provider, event-driven) — СОЗДАТЬ

**Аналог 1 — структура контекст + провайдер:** `components/CatalogSettings.tsx`

**Импорты (строки 1–6):**
```typescript
"use client";

import { createContext, useContext, useEffect, useState } from "react";
```

**Определение типа + контекст (строки 61–83):**
```typescript
// Повторить структуру: интерфейс → createContext(null) → хук с guard
interface CatalogSettings {
  viewMode: ViewMode;
  setViewMode: (m: ViewMode) => void;
  // ...остальные поля
}

const Ctx = createContext<CatalogSettings | null>(null);

export function useCatalogSettings(): CatalogSettings {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useCatalogSettings вне CatalogSettingsProvider");
  return ctx;
}
```
Для `useRole.ts` повторить этот же скелет:
```typescript
export type UserRole = 'sales' | 'client';

interface RoleContextValue {
  role: UserRole;
  setRole: (r: UserRole) => void;
  ready: boolean; // SSR-safe флаг (см. аналог 2)
}

const RoleCtx = createContext<RoleContextValue | null>(null);

export function useRole(): RoleContextValue {
  const ctx = useContext(RoleCtx);
  if (!ctx) throw new Error("useRole вне RoleProvider");
  return ctx;
}
```

**Persist-обёртки сеттеров (строки 139–159 CatalogSettings.tsx):**
```typescript
// Паттерн: setX(v) + localStorage.setItem("key", v) — атомарно в одной обёртке
const updateViewMode = (m: ViewMode) => {
  setViewMode(m);
  localStorage.setItem("viewMode", m);
};
const updateGridPreset = (p: GridPreset) => {
  setGridPreset(p);
  localStorage.setItem("gridPreset", p);
};
```
Для `useRole.ts` аналогично:
```typescript
const updateRole = (r: UserRole) => {
  setRole(r);
  localStorage.setItem("userRole", r);
};
```

**Загрузка из localStorage в useEffect (строки 103–137 CatalogSettings.tsx):**
```typescript
useEffect(() => {
  const v = localStorage.getItem("viewMode");
  if (v === "list" || v === "grid" || v === "presentation") setViewMode(v);

  const p = localStorage.getItem("gridPreset");
  if (p === "2x3" || p === "3x4" || p === "4x6") {
    setGridPreset(p);
  } else if (window.matchMedia && window.matchMedia("(max-width: 767px)").matches) {
    setGridPreset("2x3");
  }
  // ...
}, []);
```
Для `useRole.ts` упрощённый вариант — только чтение роли из localStorage:
```typescript
useEffect(() => {
  const saved = localStorage.getItem("userRole");
  if (saved === "sales" || saved === "client") {
    setRole(saved);
  }
  // дефолт всегда 'client' (D-02) — useState("client") уже установлен
  setReady(true);
}, []);
```

---

**Аналог 2 — SSR-safe флаг `ready`:** `lib/useDeviceClass.ts`

**Полный файл (строки 1–32):**
```typescript
"use client";

import { useEffect, useState } from "react";

export function useDeviceClass() {
  // SSR-safe: до монтирования считаем «не планшет» (false), чтобы серверный
  // и первый клиентский рендер совпадали и не было hydration mismatch.
  const [isTabletLike, setIsTabletLike] = useState(false);
  // Признак, что хук уже отработал на клиенте (значение достоверно).
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mq = window.matchMedia(TABLET_QUERY);
    const apply = () => setIsTabletLike(mq.matches);
    apply();
    setReady(true);   // <-- флаг выставляется ПОСЛЕ вычисления значения
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  return { isTabletLike, ready };
}
```
Для `useRole.ts`: аналогично `setReady(true)` вызывается в конце `useEffect` после загрузки из localStorage. До монтирования `role = 'client'` (нейтральный дефолт, не вызывает мелькания для большинства пользователей).

**Паттерн использования `ready` в потребителях (строки 13–16 HeaderPrimaryAction.tsx):**
```typescript
const { isTabletLike, ready } = useDeviceClass();

if (!ready) return <div className="h-9 w-9" />;  // держим место пустым
return isTabletLike ? <SyncButton /> : <FavoritesIcon secret={secret} />;
```
Для `HeaderPrimaryAction.tsx` после миграции:
```typescript
const { role, ready } = useRole();

if (!ready) return <div className="h-9 w-9" />;
return role === 'sales' ? <SyncButton /> : <FavoritesIcon secret={secret} />;
```

---

### `components/SettingsPanel.tsx` (component, UI toggle) — ИЗМЕНИТЬ

**Аналог — существующий сегмент «Форма 1-я/2-я» (строки 103–124 SettingsPanel.tsx):**
```tsx
{/* Форма цен: 1-я — +5% на товары Ефимовой; 2-я — базовые цены */}
<div className="flex items-center gap-2">
  <span className="text-xs text-gray-500">Форма</span>
  <div className="flex rounded-lg overflow-hidden border border-gray-200 text-xs">
    <button
      onClick={() => setPriceForm("1")}
      className={`px-3 py-1.5 transition-colors ${
        priceForm === "1" ? "bg-blue-500 text-white" : "bg-white text-gray-500"
      }`}
    >
      1-я
    </button>
    <button
      onClick={() => setPriceForm("2")}
      className={`px-3 py-1.5 transition-colors ${
        priceForm === "2" ? "bg-blue-500 text-white" : "bg-white text-gray-500"
      }`}
    >
      2-я
    </button>
  </div>
</div>
```

**Скопировать структуру для сегмента «Клиент | Агент» (вставить ПЕРВЫМ элементом в `flex flex-wrap` строка 54):**
```tsx
{/* Роль: Клиент | Агент — вставляется первым элементом (D-07) */}
<div className="flex items-center gap-2">
  <span className="text-xs text-gray-500">Роль</span>
  <div className="flex rounded-lg overflow-hidden border border-gray-200 text-xs">
    <button
      onClick={() => setRole("client")}
      className={`px-3 py-1.5 transition-colors ${
        role === "client" ? "bg-blue-500 text-white" : "bg-white text-gray-500"
      }`}
    >
      Клиент
    </button>
    <button
      onClick={() => setRole("sales")}
      className={`px-3 py-1.5 transition-colors ${
        role === "sales" ? "bg-blue-500 text-white" : "bg-white text-gray-500"
      }`}
    >
      Агент
    </button>
  </div>
</div>
```
Импорт `useRole` добавить в шапку файла рядом с `useCatalogSettings`.

---

### `app/catalog/[secret]/layout.tsx` (layout, provider-mount) — ИЗМЕНИТЬ

**Аналог — текущий монтаж `CatalogSettingsProvider` (строки 35–83 layout.tsx):**
```tsx
return (
  <CatalogSettingsProvider>     {/* <-- вот этот паттерн повторить */}
    <NavProvider>
      <CatalogSyncProvider>
        <InstallPromptProvider>
          ...
        </InstallPromptProvider>
      </CatalogSyncProvider>
    </NavProvider>
  </CatalogSettingsProvider>
);
```

**После изменения — `RoleProvider` монтируется рядом с (а не внутри) `CatalogSettingsProvider`:**
```tsx
// Добавить импорт RoleProvider из "@/lib/useRole"
import RoleProvider from "@/lib/useRole";

return (
  <RoleProvider>               {/* НОВЫЙ — снаружи, т.к. CatalogSettings читает роль */}
    <CatalogSettingsProvider>
      <NavProvider>
        <CatalogSyncProvider>
          <InstallPromptProvider>
            ...
          </InstallPromptProvider>
        </CatalogSyncProvider>
      </NavProvider>
    </CatalogSettingsProvider>
  </RoleProvider>
);
```
Примечание: `RoleProvider` размещается снаружи `CatalogSettingsProvider`, потому что `CatalogSettings.tsx` будет читать роль для вычисления дефолта `gridPreset` (D-10). Если потребитель — внутри дерева, провайдер должен быть выше.

---

### `components/HeaderPrimaryAction.tsx` (component, request-response) — ИЗМЕНИТЬ

**Текущий код целиком (строки 1–17):**
```typescript
"use client";

import { useDeviceClass } from "@/lib/useDeviceClass";
import SyncButton from "./SyncButton";
import FavoritesIcon from "./FavoritesIcon";

export default function HeaderPrimaryAction({ secret }: { secret: string }) {
  const { isTabletLike, ready } = useDeviceClass();

  if (!ready) return <div className="h-9 w-9" />;
  return isTabletLike ? <SyncButton /> : <FavoritesIcon secret={secret} />;
}
```

**После замены — только импорт и переменная меняются, логика if/return остаётся:**
```typescript
"use client";

import { useRole } from "@/lib/useRole";      // заменяет useDeviceClass
import SyncButton from "./SyncButton";
import FavoritesIcon from "./FavoritesIcon";

export default function HeaderPrimaryAction({ secret }: { secret: string }) {
  const { role, ready } = useRole();           // заменяет useDeviceClass

  if (!ready) return <div className="h-9 w-9" />;
  return role === "sales" ? <SyncButton /> : <FavoritesIcon secret={secret} />;
}
```

---

### `components/CardCornerButton.tsx` (component, request-response) — ИЗМЕНИТЬ

**Текущее ветвление `isTabletLike` (строки 28–59):**
```typescript
const { isTabletLike } = useDeviceClass();
// ...
// ── Планшет с фото: кнопка раскрытия фото ──
if (isTabletLike && canOpenPhoto) {
  return ( /* стрелки */ );
}
// ── Телефон/ПК: сердечко избранного ──
```

**После замены:**
```typescript
import { useRole } from "@/lib/useRole";          // заменяет useDeviceClass
// ...
const { role } = useRole();                        // ready не нужен: дефолт client = сердечко (правильно)
// ...
if (role === "sales" && canOpenPhoto) {           // вместо isTabletLike
  return ( /* стрелки */ );
}
// ── Клиент: сердечко избранного ──
```
Важно: `ready`-флаг здесь НЕ нужен, потому что дефолт до монтирования — `client`, а это сердечко, и оно же является корректным поведением для большинства пользователей. Гидратация безопасна.

---

### `components/CatalogSettings.tsx` (hook/provider) — ИЗМЕНИТЬ

**Текущая эвристика дефолта `gridPreset` (строки 107–115):**
```typescript
const p = localStorage.getItem("gridPreset");
if (p === "2x3" || p === "3x4" || p === "4x6") {
  setGridPreset(p);
} else if (window.matchMedia && window.matchMedia("(max-width: 767px)").matches) {
  // На телефоне без сохранённого выбора — по умолчанию 2×3
  setGridPreset("2x3");
}
```

**После замены — читаем роль из localStorage (не из контекста, потому что useEffect синхронный и `useRole()` может ещё не быть mounted):**
```typescript
const p = localStorage.getItem("gridPreset");
if (p === "2x3" || p === "3x4" || p === "4x6") {
  setGridPreset(p);                              // сохранённый выбор — всегда главнее (D-10)
} else {
  // Дефолт по роли (D-10): sales → 3x4, client → 2x3
  const savedRole = localStorage.getItem("userRole");
  setGridPreset(savedRole === "sales" ? "3x4" : "2x3");
  // Без записи в localStorage: останется адаптивным, пока пользователь сам не выберет
}
```
Примечание: ключ localStorage для роли — `"userRole"` (согласован с `useRole.ts`). Читать напрямую из localStorage (не через контекст) правильно, т.к. оба `useEffect` выполняются независимо при монтировании.

---

## Shared Patterns

### Persist-обёртка сеттера
**Источник:** `components/CatalogSettings.tsx` строки 140–159
**Применять ко:** `lib/useRole.ts`
```typescript
// Паттерн: один внутренний setter + одна функция-обёртка с persist
const [role, setRoleState] = useState<UserRole>("client");

const setRole = (r: UserRole) => {
  setRoleState(r);
  localStorage.setItem("userRole", r);
};
```

### SSR-safe ready-флаг
**Источник:** `lib/useDeviceClass.ts` строки 18–29
**Применять ко:** `lib/useRole.ts`, `components/HeaderPrimaryAction.tsx`
```typescript
const [ready, setReady] = useState(false);

useEffect(() => {
  // ... вычисления/загрузка ...
  setReady(true);   // ПОСЛЕДНЕЙ строкой в useEffect
}, []);
```
В `CardCornerButton.tsx` флаг `ready` не нужен — нейтральный дефолт (`client` = сердечко) безопасен при гидратации.

### Паттерн провайдера (createContext + хук-guard + export default Provider)
**Источник:** `components/CatalogSettings.tsx` строки 77–182 (или компактная версия из `components/FavoritesProvider.tsx`)
```typescript
// Компактный вариант (FavoritesProvider.tsx):
const FavoritesContext = createContext<FavoritesContextValue | null>(null);

export function FavoritesProvider({ children }: { children: ReactNode }) {
  const fav = useFavorites();
  return <FavoritesContext.Provider value={fav}>{children}</FavoritesContext.Provider>;
}

export function useFavoritesContext(): FavoritesContextValue {
  const ctx = useContext(FavoritesContext);
  if (!ctx) throw new Error("...");
  return ctx;
}
```
Для `useRole.ts` вся логика (state + useEffect + persist) остаётся в одном файле (как в CatalogSettings), а не выносится в отдельный хук — объём небольшой, разделение избыточно.

### Стиль сегмент-переключателя
**Источник:** `components/SettingsPanel.tsx` строки 103–124
```tsx
<div className="flex items-center gap-2">
  <span className="text-xs text-gray-500">{label}</span>
  <div className="flex rounded-lg overflow-hidden border border-gray-200 text-xs">
    <button className={`px-3 py-1.5 transition-colors ${
      active ? "bg-blue-500 text-white" : "bg-white text-gray-500"
    }`}>...</button>
  </div>
</div>
```

---

## No Analog Found

Все файлы этапа имеют точные аналоги в кодовой базе.

---

## Metadata

**Directories searched:** `lib/`, `components/`, `app/catalog/[secret]/`
**Files read:** 6 (CatalogSettings.tsx, useDeviceClass.ts, SettingsPanel.tsx, HeaderPrimaryAction.tsx, CardCornerButton.tsx, layout.tsx, FavoritesProvider.tsx)
**Pattern extraction date:** 2026-06-27
