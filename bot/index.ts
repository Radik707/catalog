import { Bot, webhookCallback } from "grammy";
import { registerStartHandler } from "./handlers/start";
import { registerCatalogHandler } from "./handlers/catalog";
import { registerCartHandler } from "./handlers/cart";
import { registerOrderHandler } from "./handlers/order";
import { handleAIMessage } from "./ai/consultant";

if (!process.env.TELEGRAM_BOT_TOKEN) {
  throw new Error("TELEGRAM_BOT_TOKEN не задан в переменных окружения");
}

export const bot = new Bot(process.env.TELEGRAM_BOT_TOKEN);

registerStartHandler(bot);
registerCatalogHandler(bot);
registerCartHandler(bot);
registerOrderHandler(bot);

// Все текстовые сообщения (не команды) → ИИ-консультант
bot.on("message:text", async (ctx) => {
  await handleAIMessage(ctx);
});

export const handleUpdate = webhookCallback(bot, "std/http");
