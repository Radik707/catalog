"use client";

import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useNav, NavMode } from "./NavProvider";
import { SectionNav } from "@/lib/nav";

// Подписи режимов в свёрнутом/развёрнутом переключателе
const MODE_LABELS: Record<NavMode, string> = {
  catalog: "Каталог",
  hit: "★ Хит",
  new: "✦ Новинка",
};

// Навигация в синей шапке:
// 1) сворачивающийся переключатель режима (Каталог/Хит/Новинка),
// 2) иконки разделов с подписями (только в режиме «Каталог»).
export default function CatalogNav({ navData, secret }: { navData: SectionNav[]; secret: string }) {
  const { mode, section, setMode, selectSection } = useNav();
  // Развёрнут ли список режимов (выезжает вбок по тапу на кнопку режима)
  const [expanded, setExpanded] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const catalogPath = `/catalog/${secret}`;

  // Если мы не на странице каталога (например, в корзине) — вернуться в каталог.
  // Состояние навигации (NavProvider) живёт в общем layout и переживёт переход,
  // поэтому выбранный режим/раздел применится уже на витрине.
  const goCatalogIfNeeded = () => {
    if (pathname !== catalogPath) router.push(catalogPath);
  };

  const pickMode = (m: NavMode) => {
    setMode(m);
    setExpanded(false);
    goCatalogIfNeeded();
  };

  return (
    <div className="flex items-center gap-2 min-w-0 flex-1">
      {expanded ? (
        // Развёрнутый список из трёх режимов — выбрал, и он схлопнется
        <div className="flex gap-1 shrink-0">
          {(Object.keys(MODE_LABELS) as NavMode[]).map((m) => (
            <button
              key={m}
              onClick={() => pickMode(m)}
              className={`px-2.5 py-1 rounded text-sm font-medium whitespace-nowrap transition-colors ${
                mode === m
                  ? "bg-white text-blue-600"
                  : "bg-blue-500 text-white active:bg-blue-400 hover:bg-blue-400"
              }`}
            >
              {MODE_LABELS[m]}
            </button>
          ))}
        </div>
      ) : (
        // Свёрнутая кнопка текущего режима
        <button
          onClick={() => setExpanded(true)}
          className="shrink-0 px-2.5 py-1 rounded text-sm font-semibold bg-white text-blue-600 flex items-center gap-1"
        >
          {MODE_LABELS[mode]} <span className="text-[10px]">▾</span>
        </button>
      )}

      {/* Иконки разделов — только в «Каталоге» и только когда переключатель свёрнут */}
      {!expanded && mode === "catalog" && (
        <div className="flex gap-1 overflow-x-auto scrollbar-hide min-w-0">
          {navData.map((s) => {
            const active = section === s.section;
            return (
              <button
                key={s.section}
                onClick={() => {
                  selectSection(active ? null : s.section);
                  goCatalogIfNeeded();
                }}
                className={`shrink-0 flex flex-col items-center justify-center px-1.5 py-0.5 rounded leading-none transition-colors ${
                  active ? "bg-white text-blue-600" : "text-white active:bg-blue-500 hover:bg-blue-500"
                }`}
                style={{ minWidth: 46 }}
                title={s.section}
              >
                <span className="text-base">{s.icon}</span>
                <span className="text-[9px] mt-0.5 whitespace-nowrap">{s.label}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
