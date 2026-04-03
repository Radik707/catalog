import { Bot, InlineKeyboard } from "grammy";
import { getCategories, getProductsByCategory } from "../services/products";
import { Product } from "../../lib/types";

const PAGE_SIZE = 10;

function formatProduct(p: Product): string {
  const stock = p.stock > 100 ? "в наличии" : `${p.stock} ${p.category.includes("кг") ? "кг" : "шт"}`;
  const badge = p.badge ? ` ${p.badge}` : "";
  return `*${p.name}*${badge}\n💰 ${p.price}₽ | 📦 ${p.stock} | ${p.category}`;
}

function encodeProduct(name: string): string {
  // Telegram callback_data ограничен 64 байтами — берём первые 50 символов
  return encodeURIComponent(name).slice(0, 50);
}

export function registerCatalogHandler(bot: Bot) {
  // Callback: показать список категорий
  bot.callbackQuery("catalog", async (ctx) => {
    await ctx.answerCallbackQuery();
    const categories = await getCategories();

    if (categories.length === 0) {
      await ctx.editMessageText("⚠️ Каталог временно недоступен. Попробуйте позже.");
      return;
    }

    const keyboard = new InlineKeyboard();
    for (const cat of categories) {
      keyboard.text(cat, `cat:${encodeProduct(cat)}`).row();
    }
    keyboard.text("🏠 Главное меню", "main_menu");

    await ctx.editMessageText("📋 Выберите категорию:", {
      reply_markup: keyboard,
      parse_mode: "Markdown",
    });
  });

  // Callback: показать товары категории (страница 0 по умолчанию)
  bot.callbackQuery(/^cat:(.+)$/, async (ctx) => {
    await ctx.answerCallbackQuery();
    const match = ctx.match;
    const catEncoded = match[1];

    // Проверяем формат с пагинацией: cat:{кат}:page:{n}
    let categoryEncoded = catEncoded;
    let page = 0;
    const pageMatch = catEncoded.match(/^(.+):page:(\d+)$/);
    if (pageMatch) {
      categoryEncoded = pageMatch[1];
      page = parseInt(pageMatch[2]);
    }

    const category = decodeURIComponent(categoryEncoded);
    const products = await getProductsByCategory(category);

    if (products.length === 0) {
      const keyboard = new InlineKeyboard().text("⬅️ К категориям", "catalog");
      await ctx.editMessageText(`В категории «${category}» нет товаров в наличии.`, {
        reply_markup: keyboard,
      });
      return;
    }

    const totalPages = Math.ceil(products.length / PAGE_SIZE);
    const pageItems = products.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

    const lines: string[] = [`📦 *${category}* (стр. ${page + 1}/${totalPages})\n`];
    const keyboard = new InlineKeyboard();

    for (const p of pageItems) {
      lines.push(formatProduct(p));
      const addCallback = `add:${encodeProduct(p.name)}:1`;
      keyboard.text(`➕ ${p.name.slice(0, 25)}`, addCallback).row();
    }

    // Пагинация
    const pagination = new InlineKeyboard();
    if (page > 0) {
      pagination.text("◀️ Назад", `cat:${categoryEncoded}:page:${page - 1}`);
    }
    if (totalPages > 1) {
      pagination.text(`${page + 1}/${totalPages}`, "noop");
    }
    if (page < totalPages - 1) {
      pagination.text("Далее ▶️", `cat:${categoryEncoded}:page:${page + 1}`);
    }
    if (page > 0 || page < totalPages - 1) {
      pagination.row();
    }
    pagination.text("⬅️ К категориям", "catalog").row();
    pagination.text("🏠 Главное меню", "main_menu");

    // Объединяем клавиатуры
    const fullKeyboard = new InlineKeyboard();
    for (const row of keyboard.inline_keyboard) {
      for (const btn of row) fullKeyboard.add(btn);
      fullKeyboard.row();
    }
    for (const row of pagination.inline_keyboard) {
      for (const btn of row) fullKeyboard.add(btn);
      fullKeyboard.row();
    }

    await ctx.editMessageText(lines.join("\n"), {
      reply_markup: fullKeyboard,
      parse_mode: "Markdown",
    });
  });

  // Callback: заглушка для кнопки текущей страницы
  bot.callbackQuery("noop", async (ctx) => {
    await ctx.answerCallbackQuery();
  });

  // Callback: главное меню
  bot.callbackQuery("main_menu", async (ctx) => {
    await ctx.answerCallbackQuery();
    const keyboard = new InlineKeyboard()
      .text("📋 Каталог", "catalog")
      .text("💬 Спросить консультанта", "ask_ai")
      .row()
      .text("🛒 Корзина", "cart")
      .text("📤 Отправить заказ", "order");

    await ctx.editMessageText(
      "👋 Привет! Я помощник по каталогу кондитерских изделий.\n\n" +
        "Могу помочь выбрать товар, подсказать цены и оформить заказ.\n\n" +
        "Выберите действие:",
      { reply_markup: keyboard }
    );
  });
}
