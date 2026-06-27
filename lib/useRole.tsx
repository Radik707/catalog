"use client";

// Ядро роли каталога: хук-контекст useRole + провайдер RoleProvider.
// Роль управляет видом интерфейса (угловая кнопка карточки, кнопка шапки, пресет сетки).
// Паттерн: CatalogSettings.tsx (контекст + persist) + useDeviceClass.ts (SSR-safe ready).

import { createContext, useContext, useEffect, useState } from "react";

// Возможные роли пользователя.
// 'client' — покупатель (дефолт для всех новых устройств, D-02).
// 'sales'  — торговый агент (активируется вручную в настройках).
export type UserRole = "sales" | "client";

interface RoleContextValue {
  // Текущая роль. Дефолт 'client' — до монтирования и при первом заходе.
  role: UserRole;
  // Persist-обёртка: меняет состояние + сохраняет в localStorage("userRole").
  setRole: (r: UserRole) => void;
  // SSR-safe флаг: false до монтирования (серверный рендер), true после useEffect.
  // Потребители, у которых роль меняет вёрстку, должны ждать ready=true (D-04).
  ready: boolean;
}

// Контекст роли. null — вне провайдера (хук выбросит понятную ошибку).
const RoleCtx = createContext<RoleContextValue | null>(null);

// Именованный экспорт хука. Выбрасывает ошибку вне RoleProvider.
export function useRole(): RoleContextValue {
  const ctx = useContext(RoleCtx);
  if (!ctx) throw new Error("useRole вне RoleProvider");
  return ctx;
}

// Провайдер роли. Монтируется снаружи CatalogSettingsProvider в layout каталога,
// чтобы CatalogSettings мог читать роль при вычислении дефолта gridPreset (D-10).
export default function RoleProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  // Дефолт всегда 'client' — без автоопределения по устройству (D-02, D-05).
  const [role, setRoleState] = useState<UserRole>("client");
  // SSR-safe флаг: выставляется в true последней строкой useEffect (паттерн useDeviceClass).
  const [ready, setReady] = useState(false);

  // Persist-обёртка сеттера: меняет состояние и сохраняет в localStorage.
  // Ключ "userRole" — согласован между useRole.tsx и CatalogSettings.tsx (D-10).
  const setRole = (r: UserRole) => {
    setRoleState(r);
    localStorage.setItem("userRole", r);
  };

  // При монтировании читаем сохранённую роль из localStorage.
  // Валидация: принимаем только "sales" или "client" — повреждённое/иное значение
  // игнорируется, остаётся дефолт 'client' (STRIDE T-15-01: защита от tampered storage).
  useEffect(() => {
    const saved = localStorage.getItem("userRole");
    if (saved === "sales" || saved === "client") {
      setRoleState(saved);
    }
    // Флаг ready выставляется последним — после загрузки значения (паттерн useDeviceClass).
    setReady(true);
  }, []);

  return (
    <RoleCtx.Provider value={{ role, setRole, ready }}>
      {children}
    </RoleCtx.Provider>
  );
}
