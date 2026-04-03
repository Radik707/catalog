import Anthropic from "@anthropic-ai/sdk";
import { Context } from "grammy";
import { getProducts } from "../services/products";
import { buildSystemPrompt } from "./system-prompt";
import { anthropicTools, executeTool } from "./tools";

const FALLBACK_MESSAGE =
  "Извините, произошла ошибка. Попробуйте позже или выберите товары через кнопку «Каталог».";

export async function handleAIMessage(ctx: Context): Promise<void> {
  const text = ctx.message?.text;
  if (!text) return;

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    console.error("handleAIMessage: ANTHROPIC_API_KEY не задан");
    await ctx.reply(FALLBACK_MESSAGE);
    return;
  }

  try {
    await ctx.replyWithChatAction("typing");
  } catch {
    // игнорируем ошибки typing action
  }

  try {
    const client = new Anthropic({ apiKey });
    const products = await getProducts();
    const systemPrompt = buildSystemPrompt(products);

    const messages: Anthropic.MessageParam[] = [
      { role: "user", content: text },
    ];

    let iterations = 0;
    while (iterations < 5) {
      iterations++;

      const response = await client.messages.create({
        model: "claude-haiku-4-5-20251001",
        max_tokens: 1024,
        system: systemPrompt,
        tools: anthropicTools,
        messages,
      });

      messages.push({ role: "assistant", content: response.content });

      if (response.stop_reason === "end_turn") {
        const textBlock = response.content.find((b) => b.type === "text");
        if (textBlock && textBlock.type === "text") {
          await ctx.reply(textBlock.text);
        } else {
          await ctx.reply(FALLBACK_MESSAGE);
        }
        break;
      }

      if (response.stop_reason === "tool_use") {
        const toolUseBlocks = response.content.filter((b) => b.type === "tool_use");
        const toolResults: Anthropic.ToolResultBlockParam[] = [];

        for (const block of toolUseBlocks) {
          if (block.type !== "tool_use") continue;
          const result = await executeTool(
            block.name,
            block.input as Record<string, unknown>,
            {
              userId: ctx.from!.id,
              firstName: ctx.from?.first_name,
              lastName: ctx.from?.last_name,
              username: ctx.from?.username,
              botApi: {
                sendMessage: async (chatId, msg, opts) => {
                  await ctx.api.sendMessage(
                    chatId,
                    msg,
                    opts as Parameters<typeof ctx.api.sendMessage>[2]
                  );
                },
              },
            }
          );
          toolResults.push({
            type: "tool_result",
            tool_use_id: block.id,
            content: result,
          });
        }

        messages.push({ role: "user", content: toolResults });
      } else {
        // Неожиданный stop_reason — возвращаем текст если есть
        const textBlock = response.content.find((b) => b.type === "text");
        if (textBlock && textBlock.type === "text") {
          await ctx.reply(textBlock.text);
        } else {
          await ctx.reply(FALLBACK_MESSAGE);
        }
        break;
      }
    }
  } catch (err) {
    console.error("handleAIMessage error:", err);
    await ctx.reply(FALLBACK_MESSAGE);
  }
}
