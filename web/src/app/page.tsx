import Image from "next/image";
import CodeBlock from "@/components/CodeBlock";
import FadeIn from "@/components/FadeIn";
import AskDemo from "@/components/AskDemo";

const GH_URL = "https://github.com/pauti04/CostDNA";

export default function Home() {
  return (
    <main className="min-h-screen">
      {/* ────────── NAV ────────── */}
      <nav className="sticky top-0 z-50 backdrop-blur-md bg-bg/70 border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <a href="#" className="font-mono font-semibold tracking-tight">
            <span className="gradient-text">●</span> CostDNA
          </a>
          <div className="flex gap-5 text-sm text-text-soft">
            <a href="#audit" className="hover:text-text transition">audit story</a>
            <a href="#tools" className="hover:text-text transition">tools</a>
            <a href="#try" className="hover:text-text transition">try it</a>
            <a href={GH_URL} className="text-accent hover:underline" target="_blank">
              GitHub ↗
            </a>
          </div>
        </div>
      </nav>

      {/* ────────── HERO ────────── */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 grid-pattern opacity-50" aria-hidden />
        <div className="absolute inset-0 bg-gradient-to-b from-bg/0 via-bg/40 to-bg pointer-events-none" />
        <div className="relative max-w-6xl mx-auto px-6 pt-24 pb-16">
          <FadeIn>
            <div className="font-mono text-xs text-text-soft uppercase tracking-[0.2em] mb-5">
              Open-source · LLM agent over GraphSAGE attribution
            </div>
          </FadeIn>
          <FadeIn delay={0.05}>
            <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight leading-[1.05] text-balance">
              Ask your AWS bill questions.{" "}
              <span className="gradient-text">In English.</span>
            </h1>
          </FadeIn>
          <FadeIn delay={0.12}>
            <p className="mt-6 text-lg md:text-xl text-text-soft max-w-3xl text-balance leading-relaxed">
              A natural-language agent that combines a behavioral GraphSAGE GNN
              with LLM-derived semantic features and structured CloudTrail /
              Cost Explorer queries. Answers questions like{" "}
              <em className="text-zinc-300">"why did our bill spike Tuesday?"</em>{" "}
              with specific resources, teams, and dollar amounts.
            </p>
          </FadeIn>
          <FadeIn delay={0.18}>
            <div className="mt-8 flex flex-wrap gap-3">
              <a
                href={GH_URL}
                target="_blank"
                className="inline-flex items-center gap-2 bg-accent text-zinc-950 font-semibold px-5 py-2.5 rounded-md hover:brightness-110 transition"
              >
                ↗ View on GitHub
              </a>
              <a
                href="#audit"
                className="inline-flex items-center gap-2 bg-bg-card border border-border px-5 py-2.5 rounded-md hover:border-accent transition"
              >
                The audit story →
              </a>
              <a
                href="#try"
                className="inline-flex items-center gap-2 bg-bg-card border border-border px-5 py-2.5 rounded-md hover:border-accent transition"
              >
                Try it yourself
              </a>
            </div>
          </FadeIn>

          {/* Live demo */}
          <FadeIn delay={0.28} className="mt-14">
            <AskDemo />
          </FadeIn>

          {/* KPI strip */}
          <FadeIn delay={0.36} className="mt-14">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                ["2.6M", "Real Azure VMs in the audit set"],
                ["2", "Label-leakage bugs caught via self-audit"],
                ["9", "LLM-callable tools the agent chains"],
                ["14", "CLI subcommands, all production-grade"],
              ].map(([v, l]) => (
                <div
                  key={l}
                  className="bg-bg-card border border-border rounded-lg p-4"
                >
                  <div className="text-3xl font-mono font-bold text-accent">
                    {v}
                  </div>
                  <div className="text-xs text-text-soft mt-1">{l}</div>
                </div>
              ))}
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ────────── PROBLEM ────────── */}
      <Section number="01" title="The problem">
        <p className="text-lg text-text-soft leading-relaxed max-w-3xl">
          Every FinOps team's most painful metric: the percentage of AWS spend
          that can't be attributed to any team. Industry estimates put it at{" "}
          <b className="text-text">40–60%</b>. Tagging is the standard answer,
          but tags drift. Resources are created in a hurry. Engineers leave.
        </p>
        <p className="mt-4 text-text-soft leading-relaxed max-w-3xl">
          Existing FinOps dashboards (CloudHealth, Vantage, Apptio) are only
          as good as the tags you have — and on most accounts, the tags you
          have aren't enough. CostDNA is the input layer: a tool that{" "}
          <em className="text-zinc-300">infers</em> the missing tags from
          behavior, then lets you ask English questions about the result.
        </p>
      </Section>

      {/* ────────── AUDIT STORY ────────── */}
      <Section number="02" title="The audit story" id="audit">
        <p className="text-lg text-text-soft leading-relaxed max-w-3xl">
          I had a 97% accuracy result on Microsoft's published 2.6M-VM Azure
          dataset. I audited it. <b className="text-text">It was a tautology.</b>
        </p>

        <FadeIn>
          <div className="my-8 p-6 rounded-lg bg-amber-500/5 border border-amber-500/30 border-l-4 max-w-3xl">
            <div className="font-mono text-xs text-accent uppercase tracking-wider mb-2">
              The catch
            </div>
            <p className="text-zinc-300 leading-relaxed">
              Across all <b>33,205 deployments</b> in the Azure trace,{" "}
              <b>100%</b> mapped 1:1 to a single subscription. So{" "}
              <code className="text-amber-300 bg-zinc-900 px-1.5 py-0.5 rounded text-sm">
                deployment_id
              </code>
              , used as a graph edge, was a perfect lookup of{" "}
              <code className="text-amber-300 bg-zinc-900 px-1.5 py-0.5 rounded text-sm">
                subscription_id
              </code>
              . LabelProp's "97%" was a graph database join, not learning.
            </p>
          </div>
        </FadeIn>

        <p className="text-text-soft leading-relaxed max-w-3xl mb-8">
          Most engineers stop when they see a high accuracy number and ship
          it. I caught the leak by asking{" "}
          <em className="text-zinc-300">"are you sure data is accurate?"</em>{" "}
          The same audit on Microsoft's Philly DL trace surfaced another
          partial leak: 85% of users belong to one virtual cluster. Three
          datasets, three different shortcuts, one consistent finding.
        </p>

        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-zinc-900/60">
              <tr>
                <th className="px-4 py-3 text-left text-xs uppercase tracking-wider text-text-soft font-semibold">
                  Dataset
                </th>
                <th className="px-4 py-3 text-right text-xs uppercase tracking-wider text-text-soft font-semibold">
                  Resources
                </th>
                <th className="px-4 py-3 text-right text-xs uppercase tracking-wider text-text-soft font-semibold">
                  First-cut
                </th>
                <th className="px-4 py-3 text-left text-xs uppercase tracking-wider text-text-soft font-semibold">
                  Audited shortcut
                </th>
                <th className="px-4 py-3 text-right text-xs uppercase tracking-wider text-text-soft font-semibold">
                  Honest behavioral
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {[
                {
                  ds: "Microsoft Azure",
                  n: "2.6M VMs",
                  first: "97%",
                  shortcut: "deployment_id ≡ sub (100% deterministic)",
                  honest: "6.9% (12× rand)",
                  bad: true,
                },
                {
                  ds: "Microsoft Philly",
                  n: "117K jobs",
                  first: "89%",
                  shortcut: "user_id → vc (85% deterministic)",
                  honest: "14% (2× rand)",
                  bad: true,
                },
              ].map((row) => (
                <tr key={row.ds}>
                  <td className="px-4 py-3 font-semibold">{row.ds}</td>
                  <td className="px-4 py-3 text-right font-mono text-text-soft">
                    {row.n}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-bad">
                    {row.first}
                  </td>
                  <td className="px-4 py-3 text-text-soft text-xs">
                    {row.shortcut}
                  </td>
                  <td className="px-4 py-3 text-right font-mono">{row.honest}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="mt-8 text-text-soft leading-relaxed max-w-3xl">
          <b className="text-text">The methodological finding:</b> production
          cloud attribution is mostly a metadata-lookup problem. Behavioral
          fingerprinting matters specifically when metadata is missing or
          unreliable — exactly the gap CostDNA's synthetic env reproduces.
        </p>
      </Section>

      {/* ────────── TOOLS ────────── */}
      <Section number="03" title="9 tools the agent chains" id="tools">
        <p className="text-lg text-text-soft leading-relaxed max-w-3xl mb-8">
          Each tool wraps a piece of the underlying CostDNA pipeline. Claude
          (or any tool-using LLM) decides which to call based on the question.
        </p>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
          {[
            ["summarize_account", "High-level rollup: total resources, by-team spend and confidence."],
            ["attribute_resource", "Look up which team owns a specific resource and the why-explanation."],
            ["top_spenders", "Top resources by total cost, optionally filtered by team."],
            ["find_cost_spikes", "Largest spikes + Granger-causality attribution to deploys."],
            ["find_anomalies", "Resources that don't fit any team — investigate manually."],
            ["search_resources", "Substring match across resource IDs."],
            ["signal_history", "Recent CloudTrail events + cost samples for one resource."],
            ["find_idle", "Low-activity resources to consider for cleanup."],
            ["compare_teams", "Side-by-side comparison: counts, spend, top resources, by type."],
          ].map(([name, desc]) => (
            <div
              key={name}
              className="rounded-lg border border-border bg-bg-card p-4 hover:border-accent/50 transition"
            >
              <code className="font-mono text-sm text-accent">{name}</code>
              <p className="mt-2 text-sm text-text-soft leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* ────────── VISUAL PROOF ────────── */}
      <Section number="04" title="Visual proof — embedding space">
        <p className="text-lg text-text-soft leading-relaxed max-w-3xl mb-8">
          GraphSAGE learns a 2D-projected representation where same-team
          resources cluster together and unowned ones sit visibly separate.
        </p>

        <FadeIn>
          <div className="rounded-lg overflow-hidden border border-border bg-bg-card">
            <Image
              src="/images/umap-synthetic.png"
              alt="UMAP embedding of synthetic AWS resources"
              width={1383}
              height={965}
              className="w-full h-auto"
              priority
            />
          </div>
        </FadeIn>
        <p className="mt-4 text-sm text-text-soft max-w-3xl">
          Synthetic AWS env. The tan{" "}
          <span className="font-mono text-zinc-200">unowned</span> cluster (vendor
          / legacy / orphan / shadow resources) sits visibly apart from the
          team clusters. The anomaly detector catches them automatically.
        </p>
      </Section>

      {/* ────────── TRY IT ────────── */}
      <Section number="05" title="Try it yourself" id="try">
        <p className="text-lg text-text-soft leading-relaxed max-w-3xl mb-8">
          Three usage patterns, depending on whether you prefer CLI, REPL, or
          web UI. All run on top of the same agent.
        </p>

        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <span className="text-accent font-mono text-xs">A.</span>
              One-shot CLI
            </h3>
            <CodeBlock
              filename="bash"
              code={`$ costdna ask "why did our bill spike Tuesday?" \\
    --from-dir runs/today`}
            />
          </div>
          <div>
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <span className="text-accent font-mono text-xs">B.</span>
              Multi-turn REPL
            </h3>
            <CodeBlock
              filename="bash"
              code={`$ costdna chat --from-dir runs/today
[0] ❯ summarize this account
[1] ❯ which 5 resources are spending the most?
[2] ❯ tell me about i-0c4f3230 specifically`}
            />
          </div>
          <div>
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <span className="text-accent font-mono text-xs">C.</span>
              Web chat UI
            </h3>
            <CodeBlock
              filename="bash"
              code={`$ pip install 'costdna[ui,agent]'
$ costdna serve
# open http://localhost:8501 → "Chat with the agent" tab`}
            />
          </div>
          <div>
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <span className="text-accent font-mono text-xs">D.</span>
              Docker (no install)
            </h3>
            <CodeBlock
              filename="bash"
              code={`$ docker run --rm pauti04/costdna scan --synthetic`}
            />
          </div>
        </div>

        <p className="mt-8 text-sm text-text-soft max-w-3xl">
          Setup for the agent commands: <code className="font-mono text-zinc-300 bg-zinc-900/80 px-1.5 py-0.5 rounded">pip install &apos;costdna[agent]&apos;</code> +{" "}
          <code className="font-mono text-zinc-300 bg-zinc-900/80 px-1.5 py-0.5 rounded">export ANTHROPIC_API_KEY=...</code>
        </p>
      </Section>

      {/* ────────── STACK ────────── */}
      <Section number="06" title="Stack">
        <ul className="space-y-3 text-text-soft">
          {[
            ["Python 3.11", "pandas, numpy, scikit-learn, statsmodels, networkx"],
            ["PyTorch 2.x + PyTorch Geometric", "GraphSAGE classifier — 4 layers, residual, hidden_dim 16"],
            ["sentence-transformers", "MiniLM embeddings of IAM role names + resource IDs + tags"],
            ["Anthropic SDK", "Tool-using agent loop over the 9 CostDNA tools"],
            ["boto3 (hardened)", "Adaptive retry, throttle-aware CloudTrail lookup_events"],
            ["Streamlit + Click + Rich", "CLI commands and the interactive chat UI"],
            ["Terraform", "4-team labeled AWS env with CloudTrail data events + VPC Flow Logs"],
            ["pytest + GitHub Actions", "CI on every commit; Docker auto-publish on tag"],
          ].map(([head, body]) => (
            <li key={head} className="flex gap-3 items-start">
              <span className="text-accent mt-1.5 text-xs">▸</span>
              <span>
                <b className="text-text">{head}</b>
                <span className="ml-2 text-text-soft">— {body}</span>
              </span>
            </li>
          ))}
        </ul>
      </Section>

      {/* ────────── FOOTER ────────── */}
      <footer className="border-t border-border mt-12">
        <div className="max-w-6xl mx-auto px-6 py-12 text-center text-sm text-text-soft">
          <p>
            Built by{" "}
            <a
              href="https://github.com/pauti04"
              className="text-accent-2 hover:underline"
            >
              @pauti04
            </a>{" "}
            ·{" "}
            <a
              href={GH_URL}
              className="text-accent-2 hover:underline"
              target="_blank"
            >
              github.com/pauti04/CostDNA
            </a>{" "}
            · MIT licensed
          </p>
          <p className="mt-2">
            If you&apos;re hiring for cloud-cost / FinOps / ML-infra roles —
            this is the kind of work I&apos;d like to do full-time.
          </p>
        </div>
      </footer>
    </main>
  );
}

/* ─────────────────────── helpers ─────────────────────── */

function Section({
  number,
  title,
  id,
  children,
}: {
  number: string;
  title: string;
  id?: string;
  children: React.ReactNode;
}) {
  return (
    <section
      id={id}
      className="border-t border-border py-20 px-6"
    >
      <div className="max-w-6xl mx-auto">
        <FadeIn>
          <div className="flex items-center gap-3 mb-3">
            <span className="font-mono text-xs text-accent">{number}</span>
            <span className="h-px w-10 bg-border" />
          </div>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-8">
            {title}
          </h2>
        </FadeIn>
        <FadeIn delay={0.05}>{children}</FadeIn>
      </div>
    </section>
  );
}
