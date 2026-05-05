/**
 * POST /api/ask
 *
 * Live agent endpoint backing the AskLive component on the landing page.
 * Loads the pre-baked synthetic scan, runs an Anthropic tool-use loop against
 * the 9 ported tools, returns the answer + tool calls.
 *
 * Body: { question: string, history?: any[] }
 * Env:
 *   ANTHROPIC_API_KEY — required (set in Vercel project env)
 *   COSTDNA_RATE_LIMIT_PER_HOUR — default 5; questions per IP per hour
 *   COSTDNA_DAILY_BUDGET_USD — default 10; soft cap to avoid surprise bills
 */

import Anthropic from "@anthropic-ai/sdk";
import { runTool, Scan, TOOL_DEFINITIONS } from "./tools";
import scanData from "../../../../public/data/scan.json";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const SYSTEM_PROMPT = `You are CostDNA, an AI agent that answers natural-language questions about \
AWS cloud cost attribution. You have access to tools that query a previously-completed scan.

When a user asks a question:
1. Decide which tool(s) to call.
2. Use the structured results to compose a concise answer in plain English (2-5 sentences).
3. Always cite specific resource IDs, teams, dollar amounts, timestamps, confidences from the results.
4. If a prediction has low confidence or the data doesn't support an answer, say so honestly.
5. Never invent values — only use what the tools return.

This is a synthetic AWS account with 4 teams (backend, data, ml, platform) and ~68 resources.`;

const MAX_ITERATIONS = 6;

// In-memory rate limit (Vercel functions are ephemeral but per-region this is
// good enough to soak up basic abuse). Keys are "ip:bucket".
const seen = new Map<string, number>();

const scan = scanData as unknown as Scan;

function rateKey(ip: string): string {
  const hour = new Date().toISOString().slice(0, 13); // YYYY-MM-DDTHH
  return `${ip}:${hour}`;
}

function getClientIp(req: Request): string {
  return (
    req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    req.headers.get("x-real-ip") ||
    "anonymous"
  );
}

export async function POST(req: Request) {
  if (!process.env.ANTHROPIC_API_KEY) {
    return Response.json(
      {
        error:
          "Live demo not configured — ANTHROPIC_API_KEY is missing on the server. " +
          "Run `costdna chat` locally instead, or contact pauti04 on GitHub.",
      },
      { status: 503 },
    );
  }

  const ip = getClientIp(req);
  const limit = Number(process.env.COSTDNA_RATE_LIMIT_PER_HOUR ?? "5");
  const used = seen.get(rateKey(ip)) ?? 0;
  if (used >= limit) {
    return Response.json(
      {
        error: `Rate limited — ${limit} questions per hour per IP. ` +
               `Try again later, or run \`costdna chat\` locally.`,
      },
      { status: 429 },
    );
  }
  seen.set(rateKey(ip), used + 1);

  const body = (await req.json()) as { question?: string; history?: any[] };
  const question = (body.question || "").trim();
  if (!question) {
    return Response.json({ error: "Empty question" }, { status: 400 });
  }
  if (question.length > 500) {
    return Response.json({ error: "Question too long (max 500 chars)" }, { status: 400 });
  }

  const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  const messages: Anthropic.MessageParam[] = [
    ...((body.history as Anthropic.MessageParam[] | undefined) ?? []),
    { role: "user", content: question },
  ];

  const toolCalls: Array<{ tool: string; args: any; result: unknown }> = [];

  for (let i = 0; i < MAX_ITERATIONS; i++) {
    let resp;
    try {
      resp = await client.messages.create({
        model: "claude-sonnet-4-5",
        max_tokens: 1024,
        system: SYSTEM_PROMPT,
        tools: TOOL_DEFINITIONS as Anthropic.Tool[],
        messages,
      });
    } catch (e: any) {
      return Response.json(
        { error: `Anthropic API error: ${e.message || String(e)}` },
        { status: 502 },
      );
    }

    if (resp.stop_reason === "end_turn" || resp.stop_reason === "stop_sequence") {
      const answer = resp.content
        .filter((b: any) => b.type === "text")
        .map((b: any) => b.text)
        .join("");
      messages.push({ role: "assistant", content: resp.content });
      return Response.json({
        answer: answer.trim(),
        tool_calls: toolCalls,
        history: messages,
      });
    }

    if (resp.stop_reason === "tool_use") {
      messages.push({ role: "assistant", content: resp.content });
      const toolResults: any[] = [];
      for (const block of resp.content) {
        if (block.type !== "tool_use") continue;
        const result = runTool(scan, block.name, block.input);
        toolCalls.push({ tool: block.name, args: block.input, result });
        toolResults.push({
          type: "tool_result",
          tool_use_id: block.id,
          content: JSON.stringify(result).slice(0, 8000),  // bound payload
        });
      }
      messages.push({ role: "user", content: toolResults });
      continue;
    }

    break;
  }

  return Response.json(
    {
      error: "Agent ran out of iterations without a final answer.",
      tool_calls: toolCalls,
    },
    { status: 500 },
  );
}
