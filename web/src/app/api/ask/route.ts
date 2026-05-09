/**
 * POST /api/ask
 *
 * Live agent endpoint backing the AskLive component on the landing page.
 * Loads the pre-baked synthetic scan, runs an OpenAI tool-use loop against
 * the 9 ported tools, returns the answer + tool calls.
 *
 * Body: { question: string, history?: any[] }
 * Env:
 *   OPENAI_API_KEY — required (set in Vercel project env)
 *   COSTDNA_RATE_LIMIT_PER_HOUR — default 5; questions per IP per hour
 */

import OpenAI from "openai";
import { runTool, Scan, TOOL_DEFINITIONS } from "./tools";

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
const MODEL = "gpt-4o";

// In-memory rate limit (Vercel functions are ephemeral but per-region this is
// good enough to soak up basic abuse). Keys are "ip:bucket".
const seen = new Map<string, number>();

// Scan is fetched from the deployment's own static-asset URL on first call
// (Vercel can't read public/ via fs and bundling 6MB+ of JSON breaks the build).
let scanCache: Scan | null = null;
async function loadScan(req: Request): Promise<Scan> {
  if (scanCache) return scanCache;
  const origin =
    process.env.VERCEL_URL
      ? `https://${process.env.VERCEL_URL}`
      : new URL(req.url).origin;
  const r = await fetch(`${origin}/data/scan.json`, { cache: "force-cache" });
  if (!r.ok) throw new Error(`scan fetch failed: ${r.status}`);
  scanCache = (await r.json()) as Scan;
  return scanCache;
}

// OpenAI uses {type:"function", function:{name, description, parameters}}
// while our tools.ts keeps the simpler Anthropic-shape definitions.
const OPENAI_TOOLS: OpenAI.Chat.ChatCompletionTool[] = TOOL_DEFINITIONS.map((t) => ({
  type: "function",
  function: {
    name: t.name,
    description: t.description,
    parameters: t.input_schema as Record<string, unknown>,
  },
}));

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
  if (!process.env.OPENAI_API_KEY) {
    return Response.json(
      {
        error:
          "Live demo not configured — OPENAI_API_KEY is missing on the server. " +
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

  let scan: Scan;
  try {
    scan = await loadScan(req);
  } catch (e: any) {
    return Response.json(
      { error: `Server failed to load scan: ${e.message ?? "unknown"}` },
      { status: 500 },
    );
  }

  const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

  // Strip any incoming system messages to avoid duplicates / drift.
  const incomingHistory = ((body.history as any[] | undefined) ?? []).filter(
    (m) => m && m.role !== "system",
  );

  const messages: OpenAI.Chat.ChatCompletionMessageParam[] = [
    { role: "system", content: SYSTEM_PROMPT },
    ...(incomingHistory as OpenAI.Chat.ChatCompletionMessageParam[]),
    { role: "user", content: question },
  ];

  // Streaming opt-in via ?stream=1 query param. Non-streaming clients
  // (including older versions of AskLive) still get the JSON-once response.
  const wantsStream = new URL(req.url).searchParams.get("stream") === "1";
  if (wantsStream) {
    return streamingResponse({ client, scan, messages });
  }

  const toolCalls: Array<{ tool: string; args: any; result: unknown }> = [];

  for (let i = 0; i < MAX_ITERATIONS; i++) {
    let resp;
    try {
      resp = await client.chat.completions.create({
        model: MODEL,
        max_tokens: 1024,
        messages,
        tools: OPENAI_TOOLS,
        tool_choice: "auto",
      });
    } catch (e: any) {
      const status = e?.status ?? 502;
      return Response.json(
        { error: `OpenAI API error: ${status} ${e?.message ?? String(e)}` },
        { status: 502 },
      );
    }

    const msg = resp.choices[0]?.message;
    if (!msg) break;
    messages.push(msg as OpenAI.Chat.ChatCompletionMessageParam);

    const calls = msg.tool_calls ?? [];
    if (calls.length === 0) {
      // Final answer from the assistant.
      return Response.json({
        answer: (msg.content ?? "").trim(),
        tool_calls: toolCalls,
        history: messages.filter((m) => m.role !== "system"),
      });
    }

    for (const tc of calls) {
      if (tc.type !== "function") continue;
      let args: any = {};
      try {
        args = tc.function.arguments ? JSON.parse(tc.function.arguments) : {};
      } catch {
        args = {};
      }
      const result = runTool(scan, tc.function.name, args);
      toolCalls.push({ tool: tc.function.name, args, result });
      messages.push({
        role: "tool",
        tool_call_id: tc.id,
        content: JSON.stringify(result).slice(0, 8000),
      });
    }
  }

  return Response.json(
    {
      error: "Agent ran out of iterations without a final answer.",
      tool_calls: toolCalls,
    },
    { status: 500 },
  );
}


// ─────────────────────────────────────────────────────────────────────
// Streaming response — NDJSON over a ReadableStream.
//
// Each chunk is a JSON object on its own line:
//   {"type":"tool_call",   "tool":"x", "args":{...}}
//   {"type":"tool_result", "tool":"x", "result":{...}}
//   {"type":"answer_chunk","text":"..."}    (many of these for the final answer)
//   {"type":"done",        "history":[...], "tool_calls":[...]}
//   {"type":"error",       "message":"..."}
//
// Tool-calling iterations stay non-streaming (cleaner state machine);
// only the final assistant text response is streamed token-by-token.
// ─────────────────────────────────────────────────────────────────────
async function streamingResponse(deps: {
  client: OpenAI;
  scan: Scan;
  messages: OpenAI.Chat.ChatCompletionMessageParam[];
}): Promise<Response> {
  const { client, scan, messages } = deps;
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      const send = (obj: unknown) => {
        controller.enqueue(encoder.encode(JSON.stringify(obj) + "\n"));
      };
      const toolCalls: Array<{ tool: string; args: any; result: unknown }> = [];

      try {
        for (let i = 0; i < MAX_ITERATIONS; i++) {
          // Probe call first (non-streaming) to see if the model wants
          // to call a tool or produce a final answer.
          const probe = await client.chat.completions.create({
            model: MODEL,
            max_tokens: 1024,
            messages,
            tools: OPENAI_TOOLS,
            tool_choice: "auto",
          });
          const msg = probe.choices[0]?.message;
          if (!msg) break;
          messages.push(msg as OpenAI.Chat.ChatCompletionMessageParam);

          const calls = msg.tool_calls ?? [];
          if (calls.length === 0) {
            // Final answer iteration: re-issue with stream:true and emit
            // chunks. To avoid double-billing, we use the content we already
            // got (the probe call) and just stream-emulate it by sending
            // it in chunks. This costs the same and is simpler than a
            // second OpenAI call.
            const text = (msg.content ?? "").trim();
            // Chunk every ~3 words for a natural-feeling stream.
            const words = text.split(/(\s+)/);
            for (let w = 0; w < words.length; w += 3) {
              const chunk = words.slice(w, w + 3).join("");
              if (chunk) send({ type: "answer_chunk", text: chunk });
              await new Promise((r) => setTimeout(r, 25));
            }
            send({
              type: "done",
              tool_calls: toolCalls,
              history: messages.filter((m) => m.role !== "system"),
            });
            controller.close();
            return;
          }

          // Tool-call iteration.
          for (const tc of calls) {
            if (tc.type !== "function") continue;
            let args: any = {};
            try {
              args = tc.function.arguments ? JSON.parse(tc.function.arguments) : {};
            } catch {
              args = {};
            }
            send({ type: "tool_call", tool: tc.function.name, args });
            const result = runTool(scan, tc.function.name, args);
            toolCalls.push({ tool: tc.function.name, args, result });
            send({ type: "tool_result", tool: tc.function.name, result });
            messages.push({
              role: "tool",
              tool_call_id: tc.id,
              content: JSON.stringify(result).slice(0, 8000),
            });
          }
        }

        send({
          type: "error",
          message: "Agent ran out of iterations without a final answer.",
        });
        controller.close();
      } catch (e: any) {
        send({
          type: "error",
          message: `OpenAI API error: ${e?.status ?? "?"} ${e?.message ?? String(e)}`,
        });
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "application/x-ndjson",
      "Cache-Control": "no-store",
    },
  });
}
