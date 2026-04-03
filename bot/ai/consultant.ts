import { GoogleGenerativeAI, Tool } from "@google/generative-ai";
import { Context } from "grammy";
import { getProducts } from "../services/products";
import { buildSystemPrompt } from "./system-prompt";
import { toolDeclarations, executeTool } from "./tools";

const FALLBACK_MESSAGE =
  "Извините, произошла ошибка. Попробуйте позже или выберите товары через кнопку «Каталог».";

export async function handleAIMessage(ctx: Context): Promise<void> {
  const text = ctx.message?.text;
  if (!text) return;

  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    console.error("handleAIMessage: GEMINI_API_KEY не задан");
    await ctx.reply(FALLBACK_MESSAGE);
    return;
  }

  try {
    await ctx.replyWithChatAction("typing");
  } catch {
    // игнорируем ошибки typing action
  }

  try {
    const genAI = new GoogleGenerativeAI(apiKey);
    const products = await getProducts();
    const systemPrompt = buildSystemPrompt(products);

    const model = genAI.getGenerativeModel({
      model: "gemini-2.0-flash",
      systemInstruction: systemPrompt,
      tools: [{ functionDeclarations: toolDeclarations } as Tool],
    });

    const chat = model.startChat();
    let response = await chat.sendMessage(text);
    let result = response.response;

    // Цикл выполнения function calls
    let iterations = 0;
    while (result.functionCalls() && result.functionCalls()!.length > 0 && iterations < 5) {
      iterations++;
      const calls = result.functionCalls()!;
      const functionResponses = [];

      for (const call of calls) {
        const toolResult = await executeTool(
          call.name,
          call.args as Record<string, unknown>,
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

        functionResponses.push({
          functionResponse: {
            name: call.name,
            response: { result: toolResult },
          },
        });
      }

      response = await chat.sendMessage(functionResponses);
      result = response.response;
    }

    const finalText = result.text();
    if (finalText) {
      await ctx.reply(finalText);
    } else {
      await ctx.reply(FALLBACK_MESSAGE);
    }
  } catch (err) {
    console.error("handleAIMessage error:", err);
    await ctx.reply(FALLBACK_MESSAGE);
  }
}
