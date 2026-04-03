import { Bot, InlineKeyboard } from "grammy";
import { getCart, clearCart, calcTotal } from "../services/cart-store";
import { formatOrderForOwner, formatOrderForClient } from "../services/notify";

export function registerOrderHandler(bot: Bot) {
  // Показать предварительный заказ + подтверждение
  bot.callbackQuery("order", async (ctx) => {
    await ctx.answerCallbackQuery();
    const userId = ctx.from.id;
    const cart = await getCart(userId);

    if (cart.length === 0) {
      const keyboard = new InlineKeyboard()
        .text("📋 В каталог", "catalog")
        .row()
        .text("🏠 Главное меню", "main_menu");
      await ctx.editMessageText("🛒 Корзина пуста, нечего отправлять.", {
        reply_markup: keyboard,
      });
      return;
    }

    const preview = formatOrderForClient(cart);
    const keyboard = new InlineKeyboard()
      .text("✅ Подтвердить", "order_confirm")
      .text("❌ Отмена", "cart");

    await ctx.editMessageText(`${preview}\n\nОтправить заказ?`, {
      reply_markup: keyboard,
      parse_mode: "Markdown",
    });
  });

  // Подтвердить и отправить заказ
  bot.callbackQuery("order_confirm", async (ctx) => {
    await ctx.answerCallbackQuery();
    const userId = ctx.from.id;
    const cart = await getCart(userId);

    if (cart.length === 0) {
      const keyboard = new InlineKeyboard().text("📋 В каталог", "catalog");
      await ctx.editMessageText("🛒 Корзина уже пуста.", { reply_markup: keyboard });
      return;
    }

    const ownerChatId = process.env.OWNER_CHAT_ID;
    if (!ownerChatId) {
      console.error("OWNER_CHAT_ID не задан");
      await ctx.editMessageText(
        "⚠️ Ошибка отправки заказа. Пожалуйста, свяжитесь с нами напрямую."
      );
      return;
    }

    const orderText = formatOrderForOwner({
      firstName: ctx.from.first_name,
      lastName: ctx.from.last_name,
      username: ctx.from.username,
      userId,
      cart,
    });

    try {
      await ctx.api.sendMessage(ownerChatId, orderText, {
        parse_mode: "Markdown",
      });
    } catch (err) {
      console.error("Ошибка отправки заказа владельцу:", err);
      await ctx.editMessageText(
        "⚠️ Не удалось отправить заказ. Попробуйте позже."
      );
      return;
    }

    await clearCart(userId);

    const keyboard = new InlineKeyboard()
      .text("📋 Продолжить покупки", "catalog")
      .row()
      .text("🏠 Главное меню", "main_menu");

    await ctx.editMessageText(
      "✅ Заказ отправлен! Олег свяжется с вами для подтверждения.",
      { reply_markup: keyboard }
    );
  });
}
