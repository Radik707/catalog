import { NextResponse } from "next/server";
import { getSiteSettings } from "@/lib/sheets";

// Настройки сайта (например, price_color) из вкладки «Настройки» Google Sheet.
// force-dynamic + no-store в getSiteSettings: смена в админке видна на витрине сразу.
export const dynamic = "force-dynamic";

export async function GET() {
  const settings = await getSiteSettings();
  return NextResponse.json(settings);
}
