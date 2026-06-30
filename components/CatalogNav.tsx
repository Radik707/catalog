"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useNav, NavMode } from "./NavProvider";
import { SectionNav } from "@/lib/nav";

// Подписи режимов в свёрнутом/развёрнутом переключателе
const MODE_LABELS: Record<NavMode, string> = {
  catalog: "Каталог",
  hit: "★ Хит",
  new: "✦ Новинка",
  fav: "♥ Избранное",
};

// Режимы в выпадающем переключателе. «Избранное» (fav) сюда НЕ входит —
// оно включается отдельной иконкой-сердечком в шапке.
const DROPDOWN_MODES: NavMode[] = ["catalog", "hit", "new"];

// Навигация в синей шапке:
// 1) сворачивающийся переключатель режима (Каталог/Хит/Новинка),
// 2) иконки разделов с подписями (только в режиме «Каталог»).
//
// После этапа 20 (план 01): у роли «Клиент» из правой части шапки убраны
// ♥ Избранное и 🛒 Корзина (они перенесены в нижние табы, D-03/D-04).
// Освободившееся место автоматически отдаётся этому компоненту через flex-1 —
// ряд разделов «дышит» и не теснится со свёрнутой кнопкой режима.
export default function CatalogNav({ navData, secret }: { navData: SectionNav[]; secret: string }) {
  const { mode, section, setMode, selectSection } = useNav();
  // Развёрнут ли список режимов (выезжает вбок по тапу на кнопку режима)
  const [expanded, setExpanded] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const catalogPath = `/catalog/${secret}`;

  // ── Подсказка о прокрутке ряда разделов ──
  // Градиент у края показывает, что иконки можно листать (есть скрытые слева/справа).
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canLeft, setCanLeft] = useState(false);
  const [canRight, setCanRight] = useState(false);

  const updateEdges = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    setCanLeft(el.scrollLeft > 4);
    // Запас 4px на дробные ширины
    setCanRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 4);
  }, []);

  // Пересчёт при монтировании, смене данных/режима и ресайзе окна
  useEffect(() => {
    updateEdges();
    window.addEventListener("resize", updateEdges);
    return () => window.removeEventListener("resize", updateEdges);
  }, [updateEdges, navData, mode, expanded]);

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
          {DROPDOWN_MODES.map((m) => (
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
        <div className="relative min-w-0 flex-1">
          {/* Прокручиваемый ряд иконок */}
          <div
            ref={scrollRef}
            onScroll={updateEdges}
            className="flex gap-1 overflow-x-auto scrollbar-hide"
          >
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
          {/* Градиент-подсказка слева: есть скрытые иконки за левым краем */}
          {canLeft && (
            <div className="pointer-events-none absolute inset-y-0 left-0 w-6 bg-gradient-to-r from-blue-600 to-transparent" />
          )}
          {/* Градиент-подсказка справа: есть ещё иконки за правым краем */}
          {canRight && (
            <div className="pointer-events-none absolute inset-y-0 right-0 w-6 bg-gradient-to-l from-blue-600 to-transparent" />
          )}
        </div>
      )}
    </div>
  );
}
