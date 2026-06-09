// Серверный модуль: индекс «категория → раздел/подгруппа» из structure_map.json.
// Используется как запасной механизм в lib/sheets.ts, когда в Google-таблице
// ещё нет колонок «Подгруппа»/«Раздел» (до боевой перезаливки upload.py).
// Импортируется ТОЛЬКО на сервере — JSON не попадает в клиентский бандл.
import structureMap from "../scripts/structure_map.json";

export interface StructureEntry {
  section: string;
  subgroup: string;
  sort: [number, number, number]; // (раздел, подгруппа, категория) — для сортировки
}

let _index: Map<string, StructureEntry> | null = null;

// Построить (и закэшировать) индекс категория → раздел/подгруппа/порядок.
export function getCategoryIndex(): Map<string, StructureEntry> {
  if (_index) return _index;
  const idx = new Map<string, StructureEntry>();
  const sm = structureMap as Record<string, Record<string, string[]>>;
  let secIdx = 0;
  for (const [section, subgroups] of Object.entries(sm)) {
    let subIdx = 0;
    for (const [subgroup, categories] of Object.entries(subgroups)) {
      let catIdx = 0;
      for (const category of categories) {
        idx.set(category, { section, subgroup, sort: [secIdx, subIdx, catIdx] });
        catIdx++;
      }
      subIdx++;
    }
    secIdx++;
  }
  _index = idx;
  return idx;
}
