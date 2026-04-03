import { Bot, InlineKeyboard } from "grammy";
import { getCategories } from "../services/products";

const BASE_URL = "https://catalog-khaki.vercel.app/catalog";

export function registerCatalogHandler(bot: Bot) {
  bot.hears("📋 Каталог", async (ctx) => {
    await showCategories(ctx as Parameters<typeof showCategories>[0]);
  });

  // Оставляем callback для обратной совместимости (например, из кнопок корзины)
  bot.callbackQuery("catalog", async (ctx) => {
    await ctx.answerCallbackQuery();
    await showCategories(ctx as Parameters<typeof showCategories>[0]);
  });
}

async function showCategories(ctx: { reply: (text: string, opts?: object) => Promise<unknown> }) {
  const categories = await getCategories();
  const secret = process.env.CATALOG_SECRET;

  if (categories.length === 0) {
    await ctx.reply("⚠️ Каталог временно недоступен. Попробуйте позже.");
    return;
  }

  const keyboard = new InlineKeyboard();
  for (const cat of categories) {
    const url = secret
      ? `${BASE_URL}/${secret}?category=${encodeURIComponent(cat)}`
      : BASE_URL;
    keyboard.url(cat, url).row();
  }

  await ctx.reply("📋 Выберите категорию — откроется сайт:", {
    reply_markup: keyboard,
  });
}
