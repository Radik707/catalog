import { Bot, Keyboard } from "grammy";

export const mainMenuKeyboard = new Keyboard()
  .text("💬 Спросить").text("📋 Каталог").row()
  .text("🛒 Корзина").text("📤 Отправить заказ")
  .resized();

export function registerStartHandler(bot: Bot) {
  bot.command("start", async (ctx) => {
    await ctx.reply(
      "Привет! Я помощник по каталогу. Выберите действие или просто напишите что вас интересует.",
      { reply_markup: mainMenuKeyboard }
    );
  });

  bot.hears("💬 Спросить", async (ctx) => {
    await ctx.reply(
      "Напишите ваш вопрос! Например:\n" +
        "• Какие дешёвые конфеты есть?\n" +
        "• Что популярное из карамели?\n" +
        "• Добавь 5 кг Барбариса в корзину"
    );
  });
}
