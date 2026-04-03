import { kv } from "@vercel/kv";

export interface CartItem {
  productName: string;
  price: number;
  quantity: number;
  unit: string; // фасовка/категория
}

const TTL_SECONDS = 24 * 60 * 60; // 24 часа

function cartKey(userId: number): string {
  return `cart:${userId}`;
}

export async function getCart(userId: number): Promise<CartItem[]> {
  try {
    const data = await kv.get<CartItem[]>(cartKey(userId));
    return data ?? [];
  } catch (err) {
    console.error("getCart error:", err);
    return [];
  }
}

export async function addToCart(
  userId: number,
  product: { name: string; price: number; unit: string },
  quantity: number
): Promise<CartItem[]> {
  try {
    const cart = await getCart(userId);
    const existing = cart.find(
      (item) => item.productName === product.name
    );
    if (existing) {
      existing.quantity += quantity;
    } else {
      cart.push({
        productName: product.name,
        price: product.price,
        quantity,
        unit: product.unit,
      });
    }
    await kv.set(cartKey(userId), cart, { ex: TTL_SECONDS });
    return cart;
  } catch (err) {
    console.error("addToCart error:", err);
    return [];
  }
}

export async function removeFromCart(
  userId: number,
  productName: string
): Promise<CartItem[]> {
  try {
    const cart = await getCart(userId);
    const updated = cart.filter((item) => item.productName !== productName);
    await kv.set(cartKey(userId), updated, { ex: TTL_SECONDS });
    return updated;
  } catch (err) {
    console.error("removeFromCart error:", err);
    return [];
  }
}

export async function updateQuantity(
  userId: number,
  productName: string,
  delta: number
): Promise<CartItem[]> {
  try {
    const cart = await getCart(userId);
    const item = cart.find((i) => i.productName === productName);
    if (!item) return cart;

    item.quantity += delta;
    const updated = item.quantity <= 0
      ? cart.filter((i) => i.productName !== productName)
      : cart;

    await kv.set(cartKey(userId), updated, { ex: TTL_SECONDS });
    return updated;
  } catch (err) {
    console.error("updateQuantity error:", err);
    return [];
  }
}

export async function clearCart(userId: number): Promise<void> {
  try {
    await kv.del(cartKey(userId));
  } catch (err) {
    console.error("clearCart error:", err);
  }
}

export function calcTotal(cart: CartItem[]): { items: number; total: number } {
  return {
    items: cart.reduce((sum, i) => sum + i.quantity, 0),
    total: cart.reduce((sum, i) => sum + i.price * i.quantity, 0),
  };
}
