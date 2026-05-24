/**
 * Static "example conversation" card shown below the live AskLive chat.
 *
 * Why this exists: the live chat is empty until the visitor types. A
 * visitor who scrolls past the chat without interacting (~80% of them)
 * leaves with no idea what an interaction looks like. This card shows
 * one fully-resolved turn — question, tool chain, tool results, final
 * answer — in the same visual language as the live chat. Static so it
 * never hits OpenAI; the data is hand-curated from real outputs of the
 * synthetic-env scan.
 *
 * Update path: re-pick the example by running a few questions in the
 * live chat, picking the one with the cleanest tool chain, and copying
 * the values here. Two examples are rendered side-by-side on desktop
 * to demonstrate both shapes (single tool + multi-tool chain).
 */

const EXAMPLES = [
  {
    question: "Show me the resources the model is unsure about.",
    tools: [
      {
        tool: "find_anomalies",
        args: { limit: 5 },
        result: [
          { id: "test-deploy-v3",      team: "platform", conf: 0.78, note: "no name-based hint" },
          { id: "i-286218b8",          team: "data",     conf: 0.85, note: "iam_role contains 'data'" },
          { id: "myFunction-2",        team: "platform", conf: 0.89, note: "no name-based hint" },
          { id: "stg-rds-310c0c",      team: "platform", conf: 0.96, note: "no name-based hint" },
          { id: "old-cron-2018",       team: "data",     conf: 0.97, note: "no name-based hint" },
        ],
        summary: "5 anomalies, top: test-deploy-v3 (conf=0.78)",
      },
    ],
    answer:
      "The lowest-confidence prediction is test-deploy-v3, where the model assigned platform at only 0.78 confidence — it has no naming hint and the behavioural fingerprint is weak. Three other resources (myFunction-2, stg-rds-310c0c, old-cron-2018) are also flagged because they lack name-based signals and depend on graph + behavioural inference alone. These are exactly the resources to surface in the active-learning loop: ask a human to label them, retrain, and the model's confidence on the remaining unlabeled set jumps.",
  },
  {
    question: "Compare the ml team and the data team.",
    tools: [
      {
        tool: "compare_teams",
        args: { teams: ["ml", "data"] },
        result: {
          ml:   { resources: 18, total_cost: 4643.56, top: "prod-rds-ce88cb ($399.85)" },
          data: { resources: 19, total_cost: 2318.74, top: "internal-rds-eb2263 ($374.40)" },
        },
        summary: "2 teams: ml(18 resources, $4643.56), data(19, $2318.74)",
      },
    ],
    answer:
      "Both teams are comparable in resource count (ml: 18, data: 19), but the ml team spends roughly 2× more in total ($4,643 vs $2,318). Their top spender is prod-rds-ce88cb at $399.85; data's top is internal-rds-eb2263 at $374.40 — close per-resource costs, so the gap is breadth not depth. The ml team's higher overall spend tracks the team profile (GPU training, weekend usage) the synthetic env was built with.",
  },
];


export default function ExampleConversation() {
  return (
    <div className="grid lg:grid-cols-2 gap-6">
      {EXAMPLES.map((ex, i) => (
        <ExampleCard key={i} {...ex} />
      ))}
    </div>
  );
}


function ExampleCard({
  question, tools, answer,
}: {
  question: string;
  tools: Array<{ tool: string; args: unknown; result: unknown; summary: string }>;
  answer: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-bg-card overflow-hidden shadow-soft">
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-bg-soft">
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-text/40" />
          <div className="w-2.5 h-2.5 rounded-full bg-text/30" />
          <div className="w-2.5 h-2.5 rounded-full bg-text/20" />
        </div>
        <span className="text-xs text-text-soft font-mono ml-2">
          example transcript
        </span>
        <span className="ml-auto text-[10px] font-mono text-text-muted uppercase tracking-wider">
          captured run
        </span>
      </div>

      <div className="p-5 font-mono text-[13px] leading-relaxed">
        <div className="text-text">
          <span className="text-accent">❯ </span>
          {question}
        </div>

        <div className="mt-3 space-y-2 text-xs text-text-soft border-l-2 border-accent/40 pl-3">
          {tools.map((t, j) => {
            const argStr = JSON.stringify(t.args);
            const argDisplay = argStr === "{}" ? "" :
              argStr.length > 70 ? argStr.slice(0, 67) + "…" : argStr;
            return (
              <div key={j}>
                <div className="font-mono flex items-baseline gap-2">
                  <span className="text-accent">→</span>
                  <span className="text-text">{t.tool}</span>
                  {argDisplay && (
                    <span className="text-text-soft/70">{argDisplay}</span>
                  )}
                </div>
                <details className="mt-1 pl-5 group">
                  <summary className="cursor-pointer text-text-soft/80 hover:text-text font-mono text-[11px] flex items-baseline gap-2 list-none">
                    <span className="text-accent/60">←</span>
                    <span className="truncate">{t.summary}</span>
                    <span className="ml-auto text-text-muted/50 text-[10px] group-open:hidden">▸ expand</span>
                    <span className="ml-auto text-text-muted/50 text-[10px] hidden group-open:inline">▾ collapse</span>
                  </summary>
                  <pre className="mt-2 p-3 bg-bg/40 border border-border rounded text-[11px] font-mono text-text-soft overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap break-words">
                    {JSON.stringify(t.result, null, 2)}
                  </pre>
                </details>
              </div>
            );
          })}
        </div>

        <div className="mt-4 text-text whitespace-pre-wrap">
          {answer}
        </div>
      </div>
    </div>
  );
}
