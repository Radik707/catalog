"use client";

// Общий слой состояния навигации каталога.
// Шапка (переключатель режима + иконки разделов + полоса подгрупп) и сама
// витрина живут в разных частях дерева (layout и page), поэтому состояние
// навигации вынесено в общий контекст — так они согласованно реагируют на выбор.

import { createContext, useContext, useState, useCallback, ReactNode } from "react";

// Режим витрины: обычный каталог, только хиты, только новинки
export type NavMode = "catalog" | "hit" | "new";

interface NavState {
  mode: NavMode;
  section: string | null; // выбранный раздел (только в режиме «Каталог»)
  subgroup: string | null; // выбранная подгруппа внутри раздела
  setMode: (m: NavMode) => void;
  selectSection: (s: string | null) => void;
  selectSubgroup: (s: string | null) => void;
}

const NavContext = createContext<NavState | null>(null);

export function NavProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<NavMode>("catalog");
  const [section, setSection] = useState<string | null>(null);
  const [subgroup, setSubgroup] = useState<string | null>(null);

  // Смена режима сбрасывает выбранные раздел и подгруппу
  const setMode = useCallback((m: NavMode) => {
    setModeState(m);
    setSection(null);
    setSubgroup(null);
  }, []);

  // Выбор нового раздела сбрасывает подгруппу
  const selectSection = useCallback((s: string | null) => {
    setSection(s);
    setSubgroup(null);
  }, []);

  const selectSubgroup = useCallback((s: string | null) => {
    setSubgroup(s);
  }, []);

  return (
    <NavContext.Provider
      value={{ mode, section, subgroup, setMode, selectSection, selectSubgroup }}
    >
      {children}
    </NavContext.Provider>
  );
}

export function useNav(): NavState {
  const ctx = useContext(NavContext);
  if (!ctx) throw new Error("useNav должен использоваться внутри NavProvider");
  return ctx;
}
