import { Bot, webhookCallback } from "grammy";
import { registerStartHandler } from "./handlers/start";
import { registerCatalogHandler } from "./handlers/catalog";
import { registerCartHandler } from "./handlers/cart";
import { registerOrderHandler } from "./handlers/order";
import { handleAIMessage } from "./ai/consultant";

// Тексты кнопок ReplyKeyboard — не передавать в ИИ
const MENU_BUTTONS = new Set(["💬 Спросить", "📋 Каталог", "🛒 Корзина", "📤 Отправить заказ"]);

if (!process.env.TELEGRAM_BOT_TOKEN) {
  throw new Error("TELEGRAM_BOT_TOKEN не задан в переменных окружения");
}

export const bot = new Bot(process.env.TELEGRAM_BOT_TOKEN);

registerStartHandler(bot);
registerCatalogHandler(bot);
registerCartHandler(bot);
registerOrderHandler(bot);

// Все прочие текстовые сообщения → ИИ-консультант
bot.on("message:text", async (ctx) => {
  if (!MENU_BUTTONS.has(ctx.message.text)) {
    await handleAIMessage(ctx);
  }
});

export const handleUpdate = webhookCallback(bot, "std/http");
