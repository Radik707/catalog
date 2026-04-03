import * as fs from "fs";
import * as path from "path";

// Загружаем .env.local вручную (без dotenv чтобы не добавлять зависимость)
function loadEnv() {
  const envPath = path.resolve(__dirname, "../.env.local");
  if (!fs.existsSync(envPath)) {
    console.error("Файл .env.local не найден");
    process.exit(1);
  }
  const lines = fs.readFileSync(envPath, "utf-8").split("\n");
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const idx = trimmed.indexOf("=");
    if (idx === -1) continue;
    const key = trimmed.slice(0, idx).trim();
    const value = trimmed.slice(idx + 1).trim().replace(/^["']|["']$/g, "");
    if (!process.env[key]) process.env[key] = value;
  }
}

async function setupWebhook() {
  loadEnv();

  const token = process.env.TELEGRAM_BOT_TOKEN;
  const secret = process.env.TELEGRAM_WEBHOOK_SECRET;

  if (!token) {
    console.error("TELEGRAM_BOT_TOKEN не задан в .env.local");
    process.exit(1);
  }
  if (!secret) {
    console.error("TELEGRAM_WEBHOOK_SECRET не задан в .env.local");
    process.exit(1);
  }

  const webhookUrl = "https://catalog-khaki.vercel.app/api/bot";

  console.log(`Регистрируем webhook: ${webhookUrl}`);

  const res = await fetch(
    `https://api.telegram.org/bot${token}/setWebhook`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: webhookUrl,
        secret_token: secret,
        allowed_updates: ["message", "callback_query"],
      }),
    }
  );

  const data = await res.json();

  if (data.ok) {
    console.log("✅ Webhook успешно зарегистрирован!");
    console.log(`   URL: ${webhookUrl}`);
  } else {
    console.error("❌ Ошибка регистрации webhook:", data.description);
    process.exit(1);
  }

  // Проверяем текущий статус
  const infoRes = await fetch(
    `https://api.telegram.org/bot${token}/getWebhookInfo`
  );
  const info = await infoRes.json();
  console.log("\nТекущий статус webhook:");
  console.log(`  URL: ${info.result?.url}`);
  console.log(`  Ожидающих обновлений: ${info.result?.pending_update_count}`);
  if (info.result?.last_error_message) {
    console.log(`  Последняя ошибка: ${info.result.last_error_message}`);
  }
}

setupWebhook().catch(console.error);
