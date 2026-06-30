"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useNav, NavMode } from "./NavProvider";
import { SectionNav } from "@/lib/nav";

// Три видимых чипа-фильтра в шапке: «Все · Хиты · Новинки».
// «Избранное» (fav) сюда НЕ входит — оно включается отдельной иконкой-сердечком
// и нижним табом. «Все» — это режим catalog (показать всё); название «Все»
// (а не «Каталог») убирает путаницу с нижним табом «Каталог».
const CHIP_MODES: { mode: NavMode; label: string }[] = [
  { mode: "catalog", label: "Все" },
  { mode: "hit", label: "Хиты" },
  { mode: "new", label: "Новинки" },
];

// Навигация в синей шапке:
// 1) три видимых чипа-фильтра (Все/Хиты/Новинки) — тап в один клик, ничего не прячется,
// 2) иконки разделов с подписями (только в режиме «Все»/catalog).
//
// После этапа 20 (план 01): у роли «Клиент» из правой части шапки убраны
// ♥ Избранное и 🛒 Корзина (они перенесены в нижние табы, D-03/D-04).
// Чипы держим компактными, ряд разделов — прокручиваемый (flex-1), берёт остаток места.
export default function CatalogNav({ navData, secret }: { navData: SectionNav[]; secret: string }) {
  const { mode, section, setMode, selectSection } = useNav();
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
  }, [updateEdges, navData, mode]);

  // Если мы не на странице каталога (например, в корзине) — вернуться в каталог.
  // Состояние навигации (NavProvider) живёт в общем layout и переживёт переход,
  // поэтому выбранный режим/раздел применится уже на витрине.
  const goCatalogIfNeeded = () => {
    if (pathname !== catalogPath) router.push(catalogPath);
  };

  const pickMode = (m: NavMode) => {
    setMode(m);
    goCatalogIfNeeded();
  };

  return (
    <div className="flex items-center gap-2 min-w-0 flex-1">
      {/* Три видимых чипа-фильтра: Все · Хиты · Новинки (компактные) */}
      <div className="flex gap-1 shrink-0">
        {CHIP_MODES.map(({ mode: m, label }) => (
          <button
            key={m}
            onClick={() => pickMode(m)}
            className={`px-2 py-1 rounded text-xs font-semibold whitespace-nowrap transition-colors ${
              mode === m
                ? "bg-white text-blue-600"
                : "bg-blue-500 text-white active:bg-blue-400 hover:bg-blue-400"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Иконки разделов — только в режиме «Все» (catalog) */}
      {mode === "catalog" && (
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
