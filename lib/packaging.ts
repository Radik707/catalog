// Определение фасовки товара («за шт», «за блок», «за кг» и т.д.)
// по группе и названию. Используется и в карточке, и в просмотрщике фото.
export function getPackaging(group: string, name: string): string {
  const n = name.toLowerCase();

  // Приоритет 1: точные совпадения по конкретным товарам
  if (n.includes("конфеты фараделла с печеньем трио")) return "за упаковку";
  if (n.includes("шоко-кроко")) return "за упаковку";
  if (n.includes("сэнсой хлопья нори")) return "за коробку";
  if (n.includes("акконд крекер с солью 190г/20")) return "за шт";
  if (n.includes("акконд крекер с солью 255г/12")) return "за шт";
  if (n.includes("акконд крекер вес.") && !n.includes("аккондовский с солью со вкусом сметаны и лука")) return "за коробку";
  if (n.includes("акконд печ. вес.")) return "за коробку";
  if (n.includes("вафли вес.")) return "за коробку";
  if (n.startsWith("батончик")) return "за шт";
  if (n.startsWith("драже") && !n.includes("38г/12шт")) return "за шт";
  if (n.includes("нутелла")) return "за шт";
  if (n.includes("холс")) return "за блок";
  if (n.includes("ментос")) return "за блок";
  if (n.includes("орбит")) return "за блок";

  // Приоритет 2: ШТ большими буквами → за шт
  if (name.includes("ШТ")) return "за шт";

  // Приоритет 3: комбинированные правила
  if (name.includes("ТРИО") && n.includes("вес. конфеты")) return "за упаковку";

  // Приоритет 4: глобальные правила по ключевым словам
  if (n.includes("печ. фас. трио")) return "за блок";
  if (name.includes("УПК")) return "за упаковку";
  if (n.includes("фас кг")) return "за кг";
  if (n.includes("фас.")) return "за шт";

  // Приоритет 5: правила по категории
  switch (group) {
    case "Батончики и шоколад":
      return n.includes("шоколад") ? "за шт" : "за блок";
    case "Конфеты и печенье":
      if (n.includes("вес.")) return "за кг";
      if (n.includes("печ.") || n.includes("крекер")) return "за ящик";
      return "";
    case "Лапша и каши":
      return "за шт";
    case "Чай и кофе":
      return "за пачку";
    case "Снэки":
      return "за шт";
    case "Крупы и бакалея":
      return "за пачку";
    case "Детское":
      return "за упаковку";
    case "Напитки":
      if (n.includes("добрый сок")) return "за шт";
      if (n.includes("добрый")) return "за пак";
      if (n.includes("лотте")) return "за шт";
      return "за блок";
    case "Энергетики":
      return "за пак";
    case "Соусы и специи":
    case "Соусы и приправы":
    case "Коробочные конфеты":
    case "Прикассовое":
    case "Стоевъ и Сэнсой":
    case "Консервация":
      return "за шт";
    default:
      return "";
  }
}
