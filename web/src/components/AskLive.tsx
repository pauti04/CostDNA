"use client";

import { useState, useRef, useEffect, FormEvent } from "react";
import clsx from "clsx";

type Turn = {
  question: string;
  answer: string;
  toolCalls?: { tool: string; args: any }[];
  error?: string;
};

const SUGGESTIONS = [
  "Summarize this account.",
  "Why did our bill spike Tuesday?",
  "Which 5 resources are spending the most?",
  "Which resources don't fit any team?",
];

export default function AskLive() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [historyState, setHistoryState] = useState<unknown[] | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new turns.
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [turns, busy]);

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
      const collectedTools: { tool: string; args: unknown; result?: unknown }[] = [];

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
            setTurns((t) => {
              const last = { ...t[t.length - 1], toolCalls: [...collectedTools] };
              return [...t.slice(0, -1), last];
            });
          } else if (ev.type === "tool_result") {
            // Attach result to the most recent matching tool entry.
            const idx = collectedTools.findIndex(
              (c) => c.tool === ev.tool && c.result === undefined,
            );
            if (idx >= 0) collectedTools[idx].result = ev.result;
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
    <div className="rounded-xl border border-border bg-bg-card overflow-hidden shadow-sm">
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
              4 teams. The agent has 9 tools and uses Claude under the hood.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-4">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => void send(s)}
                  className="text-left text-xs px-3 py-2 rounded-md bg-bg-soft border border-border hover:border-accent hover:text-accent transition"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {turns.map((t, i) => (
          <div key={i} className={i > 0 ? "mt-5 pt-5 border-t border-border" : ""}>
            <div className="text-text">
              <span className="text-accent">❯ </span>
              {t.question}
            </div>
            {t.answer ? (
              <div className="mt-2 text-text whitespace-pre-wrap">
                {t.answer}
                {t.toolCalls && t.toolCalls.length > 0 && (
                  <details className="mt-3 text-xs text-text-soft">
                    <summary className="cursor-pointer hover:text-text">
                      🔧 {t.toolCalls.length} tool call
                      {t.toolCalls.length === 1 ? "" : "s"}
                    </summary>
                    <ul className="mt-2 space-y-1 pl-4">
                      {t.toolCalls.map((tc, j) => (
                        <li key={j} className="font-mono">
                          <span className="text-accent">{tc.tool}</span>
                          <span className="text-text-soft">
                            ({JSON.stringify(tc.args).slice(0, 120)})
                          </span>
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            ) : t.error ? (
              <div className="mt-2 text-bad">⚠ {t.error}</div>
            ) : (
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
