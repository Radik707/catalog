import { Bot, InlineKeyboard } from "grammy";

export function registerStartHandler(bot: Bot) {
  bot.command("start", async (ctx) => {
    const keyboard = new InlineKeyboard()
      .text("📋 Каталог", "catalog")
      .text("💬 Спросить консультанта", "ask_ai")
      .row()
      .text("🛒 Корзина", "cart")
      .text("📤 Отправить заказ", "order");

    await ctx.reply(
      "👋 Привет! Я помощник по каталогу кондитерских изделий.\n\n" +
        "Могу помочь выбрать товар, подсказать цены и оформить заказ.\n\n" +
        "Выберите действие:",
      { reply_markup: keyboard }
    );
  });

  bot.callbackQuery("ask_ai", async (ctx) => {
    await ctx.answerCallbackQuery();
    await ctx.reply(
      "Напишите ваш вопрос, и я помогу! Например:\n" +
        "• Какие дешёвые конфеты есть?\n" +
        "• Что популярное из карамели?\n" +
        "• Добавь 5 кг Барбариса в корзину"
    );
  });
}
