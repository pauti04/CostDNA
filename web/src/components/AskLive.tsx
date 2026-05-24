"use client";

import { useState, useRef, useEffect, FormEvent } from "react";
import clsx from "clsx";

type ToolInvocation = {
  tool: string;
  args: unknown;
  result?: unknown;        // populated when the tool_result event arrives
};

type Turn = {
  question: string;
  answer: string;
  toolCalls?: ToolInvocation[];
  error?: string;
};

const SUGGESTIONS = [
  "Summarize this account.",
  "Which 5 resources are spending the most?",
  // Audit-themed: exercises find_anomalies. The methodology in 90 seconds.
  "Show me the resources the model is unsure about.",
  "Compare the ml team and the data team.",
];

export default function AskLive() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [historyState, setHistoryState] = useState<unknown[] | null>(null);
  const [warm, setWarm] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new turns.
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [turns, busy]);

  // Warm-up: fire a GET /api/ask as soon as the chat scrolls into view, so
  // the first POST doesn't pay the ~3-6s Vercel cold-start penalty.
  // Fire-and-forget; the visitor never sees this.
  useEffect(() => {
    if (warm || !containerRef.current) return;
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setWarm(true);
          fetch("/api/ask", { method: "GET" }).catch(() => {
            // Warm-up failures are silent. Next POST will retry.
          });
          obs.disconnect();
        }
      },
      { rootMargin: "400px" },   // trigger before the chat is fully on-screen
    );
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, [warm]);

  async function send(question: string) {
    if (!question.trim() || busy) return;
    setBusy(true);
    setInput("");
    const placeholder: Turn = { question, answer: "", toolCalls: [] };
    setTurns((t) => [...t, placeholder]);

    // Analytics — no-op if PostHog isn't configured.
    type TrackFn = (event: string, props?: object) => void;
    const track = (
      window as unknown as { costdnaTrack?: TrackFn }
    ).costdnaTrack;
    track?.("question_submitted", {
      question_length: question.length,
      turn_index: turns.length,
    });
    const t0 = performance.now();

    try {
      // Streaming response — NDJSON, one JSON event per line.
      const r = await fetch("/api/ask?stream=1", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, history: historyState }),
      });

      if (!r.ok || !r.body) {
        // Likely a rate-limit or server error returned as JSON.
        const data = await r.json().catch(() => ({ error: "request failed" }));
        track?.("question_failed", { status: r.status, error: data.error });
        setTurns((t) => {
          const last = { ...t[t.length - 1], error: data.error || `HTTP ${r.status}` };
          return [...t.slice(0, -1), last];
        });
        return;
      }

      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let answerText = "";
      const collectedTools: ToolInvocation[] = [];

      // Helper to push a fresh snapshot of `collectedTools` into the turn,
      // so React re-renders when results come in (mutating the array in
      // place wouldn't trigger a re-render).
      const flushTools = () => {
        setTurns((t) => {
          const last = { ...t[t.length - 1], toolCalls: collectedTools.map((c) => ({ ...c })) };
          return [...t.slice(0, -1), last];
        });
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        // NDJSON: split on newline, keep the trailing partial.
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.trim()) continue;
          let ev: { type: string; [k: string]: unknown };
          try { ev = JSON.parse(line); } catch { continue; }

          if (ev.type === "tool_call") {
            collectedTools.push({ tool: ev.tool as string, args: ev.args });
            flushTools();
          } else if (ev.type === "tool_result") {
            // Attach result to the most recent matching tool entry.
            const idx = collectedTools.findIndex(
              (c) => c.tool === ev.tool && c.result === undefined,
            );
            if (idx >= 0) {
              collectedTools[idx].result = ev.result;
              flushTools();
            }
          } else if (ev.type === "answer_chunk") {
            answerText += ev.text as string;
            setTurns((t) => {
              const last = { ...t[t.length - 1], answer: answerText };
              return [...t.slice(0, -1), last];
            });
          } else if (ev.type === "done") {
            setHistoryState(ev.history as unknown[]);
          } else if (ev.type === "error") {
            const msg = ev.message as string;
            track?.("question_failed", { error: msg });
            setTurns((t) => {
              const last = { ...t[t.length - 1], error: msg };
              return [...t.slice(0, -1), last];
            });
            return;
          }
        }
      }

      track?.("answer_received", {
        latency_ms: Math.round(performance.now() - t0),
        n_tool_calls: collectedTools.length,
        answer_length: answerText.length,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "network error";
      track?.("question_failed", { error: msg, network: true });
      setTurns((t) => {
        const last = { ...t[t.length - 1], error: msg };
        return [...t.slice(0, -1), last];
      });
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void send(input);
  }

  return (
    <div ref={containerRef} className="rounded-xl border border-border bg-bg-card overflow-hidden shadow-sm">
      {/* Title bar — keeps the dark "terminal" aesthetic on a light page */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-bg-soft">
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-text/40" />
          <div className="w-2.5 h-2.5 rounded-full bg-text/30" />
          <div className="w-2.5 h-2.5 rounded-full bg-text/20" />
        </div>
        <span className="text-xs text-text-soft font-mono ml-2">
          ~/costdna · costdna chat — <span className="text-text">live demo</span>
        </span>
        <span className="ml-auto text-[10px] font-mono text-text-soft uppercase tracking-wider">
          synthetic AWS account · 68 resources · 4 teams
        </span>
      </div>

      {/* Conversation */}
      <div
        ref={scrollRef}
        className="p-5 font-mono text-[13px] leading-relaxed min-h-[280px] max-h-[480px] overflow-y-auto bg-bg-card"
      >
        {turns.length === 0 && (
          <div className="text-text-soft">
            <p className="mb-3">
              Ask anything about a synthetic AWS account with 68 resources across
              4 teams. The agent has 10 tools and runs on GPT-4o.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-4">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={s}
                  onClick={() => void send(s)}
                  className={clsx(
                    "text-left text-xs px-3 py-2 rounded-md border transition",
                    // Highlight the audit-themed seed (index 2) — that's the
                    // one that lands the methodology in 90 seconds.
                    i === 2
                      ? "bg-accent/10 border-accent/40 text-text hover:bg-accent/20 hover:border-accent"
                      : "bg-bg-soft border-border hover:border-accent hover:text-accent",
                  )}
                >
                  {i === 2 && (
                    <span className="text-[10px] uppercase tracking-wider text-accent font-semibold mr-2">
                      audit
                    </span>
                  )}
                  {s}
                </button>
              ))}
            </div>
            <p className="mt-4 text-[11px] text-text-muted">
              ⓘ The agent picks tools live and chains them. Each call shows
              inline. Click any{" "}
              <code className="font-mono text-text-soft bg-bg-soft px-1 rounded">▸ expand</code>{" "}
              to see the raw structured response.
            </p>
          </div>
        )}

        {turns.map((t, i) => (
          <div key={i} className={i > 0 ? "mt-5 pt-5 border-t border-border" : ""}>
            <div className="text-text">
              <span className="text-accent">❯ </span>
              {t.question}
            </div>

            {/* Tool calls — visible by default. Each call renders with its
                args inline, and (once the tool_result event arrives) a small
                expandable panel with a peek of the structured response. The
                visitor can see exactly what data the agent worked with. */}
            {t.toolCalls && t.toolCalls.length > 0 && (
              <div className="mt-3 space-y-2 text-xs text-text-soft border-l-2 border-accent/40 pl-3">
                {t.toolCalls.map((tc, j) => {
                  const argStr = JSON.stringify(tc.args || {});
                  const argDisplay = argStr === "{}" ? "" :
                    argStr.length > 70 ? argStr.slice(0, 67) + "…" : argStr;
                  return (
                    <div key={j}>
                      <div className="font-mono flex items-baseline gap-2">
                        <span className="text-accent">→</span>
                        <span className="text-text">{tc.tool}</span>
                        {argDisplay && (
                          <span className="text-text-soft/70">
                            {argDisplay}
                          </span>
                        )}
                      </div>
                      {tc.result !== undefined && (
                        <ToolResultPeek result={tc.result} />
                      )}
                    </div>
                  );
                })}
                {/* Streaming indicator while the answer is still being produced
                    AND we have at least one tool call so far. Disappears once
                    answerText starts arriving. */}
                {!t.answer && !t.error && (
                  <div className="font-mono text-text-soft/60 flex items-baseline gap-2">
                    <span className="inline-block w-2 h-2 rounded-full bg-text-soft animate-pulse" />
                    <span>chaining…</span>
                  </div>
                )}
              </div>
            )}

            {t.answer ? (
              <div className="mt-3 text-text whitespace-pre-wrap">
                {t.answer}
              </div>
            ) : t.error ? (
              <div className="mt-2 text-bad">⚠ {t.error}</div>
            ) : t.toolCalls && t.toolCalls.length > 0 ? null /* indicator above */ : (
              <div className="mt-2 text-text-soft">
                <span className="inline-block w-2 h-4 bg-text-soft animate-blink" />
                <span className="ml-2 text-xs">thinking…</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Input */}
      <form
        onSubmit={onSubmit}
        className="flex items-center gap-2 px-4 py-3 border-t border-border bg-bg-soft"
      >
        <span className="text-accent font-mono text-sm">❯</span>
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={busy ? "agent is thinking…" : "ask anything…"}
          disabled={busy}
          className="flex-1 bg-transparent outline-none text-sm font-mono text-text placeholder:text-text-soft/60 disabled:opacity-50"
          maxLength={500}
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className={clsx(
            "px-3 py-1 rounded text-xs font-semibold transition",
            busy || !input.trim()
              ? "bg-bg-soft text-text-soft cursor-not-allowed border border-border"
              : "bg-accent text-white hover:brightness-110",
          )}
        >
          ask
        </button>
      </form>
    </div>
  );
}


/**
 * Renders a compact peek of a tool's structured response. Default is a
 * 1-line summary ("→ 12 anomalies, top: i-d8a3 (conf=0.42)"); a click
 * expands to a pretty-printed JSON dump.
 *
 * Per-tool summary heuristics live in `summarizeResult` — kept short so the
 * inline view stays scannable rather than swallowing the chat panel.
 */
function ToolResultPeek({ result }: { result: unknown }) {
  const summary = summarizeResult(result);
  return (
    <details className="mt-1 pl-5 group">
      <summary className="cursor-pointer text-text-soft/80 hover:text-text font-mono text-[11px] flex items-baseline gap-2 list-none">
        <span className="text-accent/60">←</span>
        <span className="truncate">{summary}</span>
        <span className="ml-auto text-text-muted/50 text-[10px] group-open:hidden">▸ expand</span>
        <span className="ml-auto text-text-muted/50 text-[10px] hidden group-open:inline">▾ collapse</span>
      </summary>
      <pre className="mt-2 p-3 bg-bg/40 border border-border rounded text-[11px] font-mono text-text-soft overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap break-words">
        {prettyJson(result)}
      </pre>
    </details>
  );
}


function summarizeResult(result: unknown): string {
  if (result === null || result === undefined) return "(no result)";
  if (typeof result !== "object") return String(result).slice(0, 80);
  const r = result as Record<string, unknown>;

  // find_anomalies: surface count + top anomaly's resource_id + confidence
  if (Array.isArray(r.anomalies)) {
    const arr = r.anomalies as Array<{ resource_id?: string; confidence?: number }>;
    const top = arr[0];
    return arr.length === 0
      ? "0 anomalies"
      : `${arr.length} anomalies, top: ${top?.resource_id} (conf=${top?.confidence?.toFixed(2)})`;
  }
  // top_spenders: show count + max spend
  if (Array.isArray(r.resources)) {
    const arr = r.resources as Array<{ resource_id?: string; total_cost?: number }>;
    if (arr.length > 0 && arr[0].total_cost !== undefined) {
      return `${arr.length} resources, top: ${arr[0].resource_id} ($${arr[0].total_cost?.toFixed(2)})`;
    }
    return `${arr.length} resources`;
  }
  // summarize_account / compare_teams: count teams
  if (Array.isArray(r.by_team)) {
    const arr = r.by_team as Array<{ team?: string; resources?: number }>;
    return `${arr.length} teams: ${arr.map((t) => `${t.team}(${t.resources})`).join(", ")}`;
  }
  // attribute_resource: single resource
  if (typeof r.predicted_team === "string") {
    return `team=${r.predicted_team}, conf=${(r.confidence as number)?.toFixed(2) ?? "?"}`;
  }
  // search_resources / find_idle / find_abandoned: list with count
  if (Array.isArray(r.matches)) {
    return `${(r.matches as unknown[]).length} matches`;
  }
  // Fallback — just the top-level keys
  return `{${Object.keys(r).slice(0, 5).join(", ")}${Object.keys(r).length > 5 ? ", …" : ""}}`;
}


function prettyJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
