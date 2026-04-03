import { Bot, InlineKeyboard } from "grammy";
import {
  getCart,
  addToCart,
  removeFromCart,
  updateQuantity,
  clearCart,
  calcTotal,
  CartItem,
} from "../services/cart-store";
import { getProducts } from "../services/products";

function formatCart(cart: CartItem[]): string {
  if (cart.length === 0) return "🛒 Корзина пуста.";
  const { total } = calcTotal(cart);

  const lines = ["🛒 *Ваша корзина:*", ""];
  cart.forEach((item, i) => {
    const sum = (item.price * item.quantity).toFixed(0);
    lines.push(`${i + 1}. ${item.productName} — ${item.quantity} × ${item.price}₽ = ${sum}₽`);
  });
  lines.push("");
  lines.push(`💰 Итого: ${total.toFixed(0)}₽`);
  return lines.join("\n");
}

function buildCartKeyboard(cart: CartItem[]): InlineKeyboard {
  const keyboard = new InlineKeyboard();

  for (const item of cart) {
    const name = item.productName.slice(0, 20);
    keyboard
      .text("➖", `cart_minus:${encodeURIComponent(item.productName).slice(0, 40)}`)
      .text(`${item.quantity}`, "noop")
      .text("➕", `cart_plus:${encodeURIComponent(item.productName).slice(0, 40)}`)
      .text("🗑", `cart_remove:${encodeURIComponent(item.productName).slice(0, 40)}`)
      .row();
  }

  keyboard
    .text("📤 Отправить заказ", "order")
    .row()
    .text("🗑 Очистить корзину", "cart_clear")
    .row()
    .text("📋 Продолжить покупки", "catalog");

  return keyboard;
}

export function registerCartHandler(bot: Bot) {
  // Показать корзину
  bot.callbackQuery("cart", async (ctx) => {
    await ctx.answerCallbackQuery();
    const userId = ctx.from.id;
    const cart = await getCart(userId);

    if (cart.length === 0) {
      const keyboard = new InlineKeyboard()
        .text("📋 В каталог", "catalog")
        .row()
        .text("🏠 Главное меню", "main_menu");
      await ctx.editMessageText(
        "🛒 Корзина пуста. Выберите товары в каталоге!",
        { reply_markup: keyboard }
      );
      return;
    }

    await ctx.editMessageText(formatCart(cart), {
      reply_markup: buildCartKeyboard(cart),
      parse_mode: "Markdown",
    });
  });

  // Добавить в корзину из каталога: add:{product_encoded}:{qty}
  bot.callbackQuery(/^add:(.+):(\d+)$/, async (ctx) => {
    const productEncoded = ctx.match[1];
    const qty = parseInt(ctx.match[2]);
    const productName = decodeURIComponent(productEncoded);
    const userId = ctx.from.id;

    // Найти товар в каталоге
    const products = await getProducts();
    const product = products.find(
      (p) => p.name.toLowerCase().includes(productName.toLowerCase()) ||
             productName.toLowerCase().includes(p.name.toLowerCase().slice(0, 20))
    );

    if (!product) {
      await ctx.answerCallbackQuery("⚠️ Товар не найден");
      return;
    }

    const cart = await addToCart(
      userId,
      { name: product.name, price: product.price, unit: product.category },
      qty
    );

    const { total } = calcTotal(cart);
    await ctx.answerCallbackQuery(
      `✅ Добавлено! Корзина: ${cart.length} поз. / ${total.toFixed(0)}₽`
    );
  });

  // Увеличить количество
  bot.callbackQuery(/^cart_plus:(.+)$/, async (ctx) => {
    await ctx.answerCallbackQuery();
    const productName = decodeURIComponent(ctx.match[1]);
    const userId = ctx.from.id;
    const cart = await updateQuantity(userId, productName, +1);

    await ctx.editMessageText(formatCart(cart), {
      reply_markup: buildCartKeyboard(cart),
      parse_mode: "Markdown",
    });
  });

  // Уменьшить количество
  bot.callbackQuery(/^cart_minus:(.+)$/, async (ctx) => {
    await ctx.answerCallbackQuery();
    const productName = decodeURIComponent(ctx.match[1]);
    const userId = ctx.from.id;
    const cart = await updateQuantity(userId, productName, -1);

    if (cart.length === 0) {
      const keyboard = new InlineKeyboard()
        .text("📋 В каталог", "catalog")
        .row()
        .text("🏠 Главное меню", "main_menu");
      await ctx.editMessageText("🛒 Корзина пуста.", { reply_markup: keyboard });
      return;
    }

    await ctx.editMessageText(formatCart(cart), {
      reply_markup: buildCartKeyboard(cart),
      parse_mode: "Markdown",
    });
  });

  // Удалить товар
  bot.callbackQuery(/^cart_remove:(.+)$/, async (ctx) => {
    await ctx.answerCallbackQuery();
    const productName = decodeURIComponent(ctx.match[1]);
    const userId = ctx.from.id;
    const cart = await removeFromCart(userId, productName);

    if (cart.length === 0) {
      const keyboard = new InlineKeyboard()
        .text("📋 В каталог", "catalog")
        .row()
        .text("🏠 Главное меню", "main_menu");
      await ctx.editMessageText("🛒 Корзина пуста.", { reply_markup: keyboard });
      return;
    }

    await ctx.editMessageText(formatCart(cart), {
      reply_markup: buildCartKeyboard(cart),
      parse_mode: "Markdown",
    });
  });

  // Очистить корзину — запрос подтверждения
  bot.callbackQuery("cart_clear", async (ctx) => {
    await ctx.answerCallbackQuery();
    const keyboard = new InlineKeyboard()
      .text("✅ Да, очистить", "cart_clear_confirm")
      .text("❌ Отмена", "cart");

    await ctx.editMessageText("Очистить корзину? Это действие нельзя отменить.", {
      reply_markup: keyboard,
    });
  });

  bot.callbackQuery("cart_clear_confirm", async (ctx) => {
    await ctx.answerCallbackQuery("🗑 Корзина очищена");
    const userId = ctx.from.id;
    await clearCart(userId);

    const keyboard = new InlineKeyboard()
      .text("📋 В каталог", "catalog")
      .row()
      .text("🏠 Главное меню", "main_menu");
    await ctx.editMessageText("🛒 Корзина очищена.", { reply_markup: keyboard });
  });
}
