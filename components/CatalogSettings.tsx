"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { PresentationSizes } from "./ProductCard";
import { PriceForm } from "@/lib/pricing";

// Общие настройки отображения каталога. Живут в контексте, чтобы
// кнопка-шестерёнка в шапке и сам каталог делили одно состояние.
export type ViewMode = "list" | "grid" | "presentation";
export type GridPreset = "2x3" | "3x4" | "4x6";

// Пресеты плотности сетки для режима презентации.
// cols — колонки (одинаково на всех экранах, чтобы совпадало с ярлыком),
// sizes — размеры фото/текста (масштабируются вместе с плотностью).
export const PRESENTATION_PRESETS: Record<
  GridPreset,
  { label: string; cols: string; sizes: PresentationSizes }
> = {
  "2x3": {
    label: "2×3",
    cols: "grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4", // десктоп: 3 и 4 колонки
    sizes: {
      photoH: "h-44 sm:h-72",
      bodyPad: "px-2 pt-1.5 pb-2 gap-1",
      nameCls: "text-sm sm:text-base",
      nameLines: "line-clamp-2",
      priceCls: "text-sm sm:text-lg",
      pkgCls: "text-xs",
      compactCart: false,
    },
  },
  "3x4": {
    label: "3×4",
    cols: "grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5", // десктоп: 4 и 5 колонок
    sizes: {
      photoH: "h-28 sm:h-44",
      bodyPad: "px-1.5 pt-1 pb-1.5 gap-0.5",
      nameCls: "text-xs sm:text-sm",
      nameLines: "line-clamp-2",
      priceCls: "text-xs sm:text-base",
      pkgCls: "text-[10px]",
      compactCart: true,
    },
  },
  "4x6": {
    label: "4×6",
    cols: "grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6", // десктоп: 5 и 6 колонок
    sizes: {
      photoH: "h-20 sm:h-32",
      bodyPad: "px-1 pt-1 pb-1 gap-0.5",
      nameCls: "text-[10px] sm:text-xs",
      nameLines: "line-clamp-2",
      priceCls: "text-[10px] sm:text-sm",
      pkgCls: "text-[9px]",
      compactCart: true,
    },
  },
};

interface CatalogSettings {
  viewMode: ViewMode;
  setViewMode: (m: ViewMode) => void;
  gridPreset: GridPreset;
  setGridPreset: (p: GridPreset) => void;
  showPhotos: boolean;
  setShowPhotos: (v: boolean) => void;
  showPrices: boolean;
  setShowPrices: (v: boolean) => void;
  priceForm: PriceForm; // "2" — базовые цены; "1" — +5% на товары Ефимовой
  setPriceForm: (v: PriceForm) => void;
  panelOpen: boolean; // открыта ли выпадающая панель настроек
  setPanelOpen: (v: boolean) => void;
}

const Ctx = createContext<CatalogSettings | null>(null);

export function useCatalogSettings(): CatalogSettings {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useCatalogSettings вне CatalogSettingsProvider");
  return ctx;
}

export default function CatalogSettingsProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  // Значения по умолчанию при первом открытии: презентация, сетка 3×4, с ценами.
  const [viewMode, setViewMode] = useState<ViewMode>("presentation");
  const [gridPreset, setGridPreset] = useState<GridPreset>("3x4");
  const [showPhotos, setShowPhotos] = useState(true);
  const [showPrices, setShowPrices] = useState(true);
  // Форма цен: по умолчанию "2" (базовые цены как сейчас)
  const [priceForm, setPriceForm] = useState<PriceForm>("2");
  const [panelOpen, setPanelOpen] = useState(false);

  // Загрузка сохранённых настроек из localStorage.
  useEffect(() => {
    const v = localStorage.getItem("viewMode");
    if (v === "list" || v === "grid" || v === "presentation") setViewMode(v);

    const p = localStorage.getItem("gridPreset");
    if (p === "2x3" || p === "3x4" || p === "4x6") {
      setGridPreset(p);
    } else if (window.matchMedia && window.matchMedia("(max-width: 767px)").matches) {
      // На телефоне без сохранённого выбора — по умолчанию 2×3 (крупнее, с именем+описанием).
      // Только состояние, без записи в localStorage: останется адаптивным, пока
      // пользователь сам не выберет плотность в шестерёнке.
      setGridPreset("2x3");
    }

    if (localStorage.getItem("showPhotos") === "0") setShowPhotos(false);
    if (localStorage.getItem("showPrices") === "0") setShowPrices(false);

    const pf = localStorage.getItem("priceForm");
    if (pf === "1" || pf === "2") setPriceForm(pf);
  }, []);

  // Обёртки сеттеров с сохранением в localStorage.
  const updateViewMode = (m: ViewMode) => {
    setViewMode(m);
    localStorage.setItem("viewMode", m);
  };
  const updateGridPreset = (p: GridPreset) => {
    setGridPreset(p);
    localStorage.setItem("gridPreset", p);
  };
  const updateShowPhotos = (v: boolean) => {
    setShowPhotos(v);
    localStorage.setItem("showPhotos", v ? "1" : "0");
  };
  const updateShowPrices = (v: boolean) => {
    setShowPrices(v);
    localStorage.setItem("showPrices", v ? "1" : "0");
  };
  const updatePriceForm = (v: PriceForm) => {
    setPriceForm(v);
    localStorage.setItem("priceForm", v);
  };

  return (
    <Ctx.Provider
      value={{
        viewMode,
        setViewMode: updateViewMode,
        gridPreset,
        setGridPreset: updateGridPreset,
        showPhotos,
        setShowPhotos: updateShowPhotos,
        showPrices,
        setShowPrices: updateShowPrices,
        priceForm,
        setPriceForm: updatePriceForm,
        panelOpen,
        setPanelOpen,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}
