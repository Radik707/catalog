import { Product } from "./types";

// Иконка для каждого раздела (emoji — без внешних библиотек иконок).
export const SECTION_ICONS: Record<string, string> = {
  Новинки: "✨",
  Сладкое: "🍬",
  Напитки: "🥤",
  "Крупы, лапша, бакалея": "🌾",
  "Соусы и консервация": "🥫",
  "Снэки и прикассовое": "🍿",
  Прочее: "📦",
};

// Короткая подпись под иконкой (полные названия слишком длинные для шапки).
export const SECTION_SHORT: Record<string, string> = {
  "Крупы, лапша, бакалея": "Бакалея",
  "Соусы и консервация": "Соусы",
  "Снэки и прикассовое": "Снэки",
};

// Один раздел для шапки: имя, иконка, короткая подпись и список его подгрупп.
export interface SectionNav {
  section: string;
  icon: string;
  label: string;
  subgroups: string[];
}

// Построить данные навигации из товаров: разделы и их подгруппы в порядке
// первого появления (товары уже отсортированы по структуре). Товары с остатком
// ≤ 1 пропускаются — пустых разделов в шапке не будет. «Новинки» — всегда первыми.
export function buildNavData(products: Product[]): SectionNav[] {
  const order: string[] = [];
  const subs = new Map<string, string[]>();

  for (const p of products) {
    if (p.stock <= 1) continue;
    const sec = p.section || "Новинки";
    const sub = p.subgroup || p.category || "—";
    if (!subs.has(sec)) {
      subs.set(sec, []);
      order.push(sec);
    }
    const list = subs.get(sec)!;
    if (!list.includes(sub)) list.push(sub);
  }

  // «Новинки» — всегда первым разделом, если присутствуют
  if (order.includes("Новинки")) {
    order.splice(order.indexOf("Новинки"), 1);
    order.unshift("Новинки");
  }

  return order.map((sec) => ({
    section: sec,
    icon: SECTION_ICONS[sec] ?? "📦",
    label: SECTION_SHORT[sec] ?? sec,
    subgroups: subs.get(sec)!,
  }));
}
