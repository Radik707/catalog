import { NextResponse } from "next/server";
import { getProducts } from "@/lib/sheets";

export const dynamic = 'force-dynamic';
export const revalidate = 300; // ISR: обновлять каждые 5 минут

export async function GET() {
  const products = await getProducts();
  return NextResponse.json(products);
}
