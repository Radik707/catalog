import { Bot, webhookCallback } from "grammy";
import { registerStartHandler } from "./handlers/start";
import { registerCatalogHandler } from "./handlers/catalog";
import { registerCartHandler } from "./handlers/cart";
import { registerOrderHandler } from "./handlers/order";

if (!process.env.TELEGRAM_BOT_TOKEN) {
  throw new Error("TELEGRAM_BOT_TOKEN не задан в переменных окружения");
}

export const bot = new Bot(process.env.TELEGRAM_BOT_TOKEN);

registerStartHandler(bot);
registerCatalogHandler(bot);
registerCartHandler(bot);
registerOrderHandler(bot);

// Обработка неизвестных команд
bot.on("message:text", async (ctx) => {
  // В этапе 4 этот обработчик будет передавать сообщения в ИИ-консультант
  // Пока показываем меню
  const { InlineKeyboard } = await import("grammy");
  const keyboard = new InlineKeyboard()
    .text("📋 Каталог", "catalog")
    .text("🛒 Корзина", "cart")
    .row()
    .text("📤 Отправить заказ", "order");

  await ctx.reply(
    "Используйте кнопки для навигации. ИИ-консультант будет доступен в следующем обновлении.",
    { reply_markup: keyboard }
  );
});

export const handleUpdate = webhookCallback(bot, "std/http");
