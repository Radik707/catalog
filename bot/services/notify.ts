import { CartItem, calcTotal } from "./cart-store";

interface OrderInfo {
  firstName?: string;
  lastName?: string;
  username?: string;
  userId: number;
  cart: CartItem[];
}

export function formatOrderForOwner(order: OrderInfo): string {
  const { firstName, lastName, username, userId, cart } = order;
  const { total } = calcTotal(cart);

  const clientName = [firstName, lastName].filter(Boolean).join(" ") || "Без имени";
  const usernameStr = username ? ` (@${username})` : "";

  const lines: string[] = [
    "🛒 *Новый заказ!*",
    "",
    `👤 Клиент: ${clientName}${usernameStr}`,
    `📱 Telegram ID: ${userId}`,
    "",
    "📋 Заказ:",
  ];

  cart.forEach((item, i) => {
    const sum = (item.price * item.quantity).toFixed(0);
    lines.push(
      `${i + 1}. ${item.productName} — ${item.quantity} × ${item.price}₽ = ${sum}₽`
    );
  });

  lines.push("");
  lines.push(`💰 Итого: ${total.toFixed(0)}₽`);
  lines.push(`🕐 Время: ${new Date().toLocaleString("ru-RU", { timeZone: "Europe/Moscow" })}`);

  return lines.join("\n");
}

export function formatOrderForClient(cart: CartItem[]): string {
  const { total } = calcTotal(cart);

  const lines: string[] = ["📋 *Ваш заказ:*", ""];

  cart.forEach((item, i) => {
    const sum = (item.price * item.quantity).toFixed(0);
    lines.push(
      `${i + 1}. ${item.productName} — ${item.quantity} × ${item.price}₽ = ${sum}₽`
    );
  });

  lines.push("");
  lines.push(`💰 Итого: ${total.toFixed(0)}₽`);

  return lines.join("\n");
}
