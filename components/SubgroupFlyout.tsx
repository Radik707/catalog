"use client";

import { useNav } from "./NavProvider";
import { SectionNav } from "@/lib/nav";

// Выезжающая полоса подгрупп выбранного раздела (под синей шапкой).
// Появляется только в режиме «Каталог», когда выбран раздел.
// Тап по подгруппе фильтрует витрину только на неё; «Все» — сброс фильтра.
export default function SubgroupFlyout({ navData }: { navData: SectionNav[] }) {
  const { mode, section, subgroup, selectSubgroup } = useNav();

  if (mode !== "catalog" || !section) return null;
  const data = navData.find((s) => s.section === section);
  if (!data || data.subgroups.length === 0) return null;

  return (
    // Прилипает под синей шапкой (h-12 = 48px), поэтому top-12
    <div className="sticky top-12 z-40 bg-white border-b border-gray-200 shadow-sm">
      <div className="flex gap-2 px-4 py-2 overflow-x-auto scrollbar-hide">
        <button
          onClick={() => selectSubgroup(null)}
          className={`shrink-0 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            subgroup === null
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-600 active:bg-gray-200"
          }`}
        >
          Все
        </button>
        {data.subgroups.map((sg) => (
          <button
            key={sg}
            onClick={() => selectSubgroup(sg)}
            className={`shrink-0 px-3 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
              subgroup === sg
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-600 active:bg-gray-200"
            }`}
          >
            {sg}
          </button>
        ))}
      </div>
    </div>
  );
}
