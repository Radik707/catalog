import { NextResponse } from "next/server";
import { getProducts } from "@/lib/sheets";

export const dynamic = 'force-dynamic';
// Без ISR-кэша: ответ всегда отражает актуальный лист «Товары» (см. lib/sheets.ts — no-store)

export async function GET() {
  const products = await getProducts();
  return NextResponse.json(products);
}
