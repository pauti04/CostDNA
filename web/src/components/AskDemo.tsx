"use client";

import { useEffect, useState } from "react";
import clsx from "clsx";

type Turn = { question: string; answer: string };

const TURNS: Turn[] = [
  {
    question: "summarize this account",
    answer:
      "You're scanning 142 resources across 4 teams. Total spend in the window: $9,570. Highest-spending team is ml ($4,412 across 17 resources, avg confidence 0.94). Backend has 16 resources, data has 14, platform has 12. 4 resources flagged as low-confidence — see anomalies.",
  },
  {
    question: "why did our bill spike Tuesday?",
    answer:
      "Resource `i-0c4f3230` (predicted team: ml, conf 0.92) had a $7.30 cost spike at Tue 16:00 UTC. Team ml's deploy at Tue 14:18 (commit a4f2c91, repo ml-training-pipeline) is the most likely cause (Granger p=0.000). Two other ml-team RDS instances spiked at the same time, suggesting the deploy fanned out across the cluster.",
  },
  {
    question: "which resources don't fit any team?",
    answer:
      "8 anomalies. Top hits: `DatadogForwarder-63e91312` (conf 1.00, but +2.7σ from data-team centroid — likely a vendor resource), `cloudflare-access-logs-...` (similar), `alice-smith-personal-bucket` (orphan: IAM role belongs to a deleted user), and 5 more in the runs/ directory. Worth manual review.",
  },
  {
    question: "compare team ml and team data",
    answer:
      "**ml** has 17 resources / $4,412 / avg conf 0.94, mostly Lambda+S3 (model artifacts + training jobs). **data** has 14 resources / $2,143 / avg conf 0.91, mostly RDS+S3 (warehouse + ETL). Top ml resource: `mlops-rds-feature-store` ($820). Top data resource: `etl-rds-warehouse-001` ($612). ml resources show late-night peaks (Granger fits the training schedule); data resources are early-morning batch.",
  },
];

export default function AskDemo() {
  const [turn, setTurn] = useState(0);
  const [phase, setPhase] = useState<"asking" | "answering" | "done">("asking");
  const [shown, setShown] = useState("");

  useEffect(() => {
    const t = TURNS[turn];
    if (phase === "asking") {
      let i = 0;
      const id = setInterval(() => {
        if (i <= t.question.length) {
          setShown(t.question.slice(0, i));
          i++;
        } else {
          clearInterval(id);
          setTimeout(() => setPhase("answering"), 350);
        }
      }, 35);
      return () => clearInterval(id);
    }
    if (phase === "answering") {
      let i = 0;
      const id = setInterval(() => {
        if (i <= t.answer.length) {
          setShown(t.answer.slice(0, i));
          i++;
        } else {
          clearInterval(id);
          setTimeout(() => {
            setPhase("done");
          }, 1200);
        }
      }, 12);
      return () => clearInterval(id);
    }
    if (phase === "done") {
      const id = setTimeout(() => {
        setShown("");
        setPhase("asking");
        setTurn((t) => (t + 1) % TURNS.length);
      }, 4500);
      return () => clearTimeout(id);
    }
  }, [turn, phase]);

  const t = TURNS[turn];

  return (
    <div className="rounded-xl border border-border bg-zinc-950/80 overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-zinc-900/60">
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-bad/70" />
          <div className="w-2.5 h-2.5 rounded-full bg-amber-500/70" />
          <div className="w-2.5 h-2.5 rounded-full bg-good/70" />
        </div>
        <span className="text-xs text-text-soft font-mono ml-2">~/costdna · costdna chat</span>
      </div>
      <div className="p-5 font-mono text-[13px] leading-relaxed min-h-[280px]">
        {/* Question */}
        <div className="mb-3">
          <span className="text-accent">❯ </span>
          <span className="text-zinc-200">
            {phase === "asking" ? shown : t.question}
            {phase === "asking" && (
              <span className="inline-block w-2 h-4 ml-0.5 -mb-0.5 bg-accent animate-blink" />
            )}
          </span>
        </div>
        {/* Answer */}
        {phase !== "asking" && (
          <div className="text-zinc-300 whitespace-pre-wrap">
            {phase === "answering" ? shown : t.answer}
            {phase === "answering" && (
              <span className="inline-block w-2 h-4 ml-0.5 -mb-0.5 bg-zinc-400 animate-blink" />
            )}
          </div>
        )}
      </div>
      <div className="flex items-center justify-between px-4 py-2 border-t border-border bg-zinc-900/40 text-xs text-text-soft">
        <span>
          turn <span className="text-zinc-300">{turn + 1}</span> / {TURNS.length}
        </span>
        <div className="flex gap-1">
          {TURNS.map((_, i) => (
            <div
              key={i}
              className={clsx(
                "h-1 rounded-full transition-all",
                i === turn ? "w-8 bg-accent" : "w-2 bg-zinc-700",
              )}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
