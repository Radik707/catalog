import { FunctionDeclaration, SchemaType } from "@google/generative-ai";
import { searchProducts, getProducts } from "../services/products";
import { addToCart, removeFromCart, getCart, clearCart, calcTotal } from "../services/cart-store";
import { formatOrderForOwner, formatOrderForClient } from "../services/notify";

export const toolDeclarations: FunctionDeclaration[] = [
  {
    name: "search_products",
    description: "Поиск товаров по названию, категории или описанию",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {
        query: {
          type: SchemaType.STRING,
          description: "Поисковый запрос (название товара, категория, описание)",
        },
      },
      required: ["query"],
    },
  },
  {
    name: "add_to_cart",
    description: "Добавить товар в корзину клиента",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {
        product_name: {
          type: SchemaType.STRING,
          description: "Название товара (полное или частичное)",
        },
        quantity: {
          type: SchemaType.NUMBER,
          description: "Количество (в единицах фасовки, по умолчанию 1)",
        },
      },
      required: ["product_name"],
    },
  },
  {
    name: "remove_from_cart",
    description: "Удалить товар из корзины клиента",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {
        product_name: {
          type: SchemaType.STRING,
          description: "Название товара для удаления",
        },
      },
      required: ["product_name"],
    },
  },
  {
    name: "show_cart",
    description: "Показать текущую корзину клиента",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {},
    },
  },
  {
    name: "send_order",
    description: "Оформить и отправить заказ владельцу магазина",
    parameters: {
      type: SchemaType.OBJECT,
      properties: {},
    },
  },
];

interface UserInfo {
  userId: number;
  firstName?: string;
  lastName?: string;
  username?: string;
  botApi: { sendMessage: (chatId: string, text: string, opts?: object) => Promise<void> };
}

export async function executeTool(
  name: string,
  args: Record<string, unknown>,
  user: UserInfo
): Promise<string> {
  try {
    switch (name) {
      case "search_products": {
        const query = String(args.query || "");
        const results = await searchProducts(query);
        if (results.length === 0) return `Товаров по запросу «${query}» не найдено.`;
        const lines = results.slice(0, 10).map(
          (p) => `• ${p.name} — ${p.price}₽ (ост: ${p.stock}, ${p.category})`
        );
        return `Найдено ${results.length} товаров:\n${lines.join("\n")}`;
      }

      case "add_to_cart": {
        const productName = String(args.product_name || "");
        const quantity = Number(args.quantity) || 1;
        const products = await getProducts();
        const q = productName.toLowerCase();
        const matches = products.filter((p) => p.name.toLowerCase().includes(q));

        if (matches.length === 0) {
          return `Товар «${productName}» не найден в каталоге.`;
        }
        if (matches.length > 3) {
          const names = matches.slice(0, 5).map((p) => `• ${p.name}`).join("\n");
          return `Нашёл несколько товаров, уточните какой именно:\n${names}`;
        }

        const product = matches[0];
        const cart = await addToCart(
          user.userId,
          { name: product.name, price: product.price, unit: product.category },
          quantity
        );
        const { total } = calcTotal(cart);
        return `✅ Добавлено: ${product.name} — ${quantity} × ${product.price}₽ = ${(quantity * product.price).toFixed(0)}₽\nВсего в корзине: ${total.toFixed(0)}₽`;
      }

      case "remove_from_cart": {
        const productName = String(args.product_name || "");
        const cart = await removeFromCart(user.userId, productName);
        if (cart.length === 0) return "Товар удалён. Корзина пуста.";
        const { total } = calcTotal(cart);
        return `Товар «${productName}» удалён. Итого в корзине: ${total.toFixed(0)}₽`;
      }

      case "show_cart": {
        const cart = await getCart(user.userId);
        if (cart.length === 0) return "Корзина пуста.";
        return formatOrderForClient(cart).replace(/\*/g, "");
      }

      case "send_order": {
        const cart = await getCart(user.userId);
        if (cart.length === 0) return "Корзина пуста — нечего отправлять.";

        const ownerChatId = process.env.OWNER_CHAT_ID;
        if (!ownerChatId) return "Ошибка конфигурации: OWNER_CHAT_ID не задан.";

        const orderText = formatOrderForOwner({
          firstName: user.firstName,
          lastName: user.lastName,
          username: user.username,
          userId: user.userId,
          cart,
        });

        await user.botApi.sendMessage(ownerChatId, orderText, { parse_mode: "Markdown" });
        await clearCart(user.userId);
        return "✅ Заказ успешно отправлен! Олег свяжется с вами для подтверждения.";
      }

      default:
        return `Неизвестная функция: ${name}`;
    }
  } catch (err) {
    console.error(`executeTool(${name}) error:`, err);
    return `Ошибка выполнения функции ${name}.`;
  }
}
