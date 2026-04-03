import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const secret = req.headers.get("x-telegram-bot-api-secret-token");

  if (secret !== process.env.TELEGRAM_WEBHOOK_SECRET) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const { handleUpdate } = await import("../../../bot/index");
    return await handleUpdate(req);
  } catch (err) {
    console.error("Ошибка обработки Telegram update:", err);
    return NextResponse.json({ ok: true }); // всегда возвращать 200 Telegram
  }
}
