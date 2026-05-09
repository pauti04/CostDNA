import Image from "next/image";
import CodeBlock from "@/components/CodeBlock";
import FadeIn from "@/components/FadeIn";
import AskLive from "@/components/AskLive";

const GH_URL = "https://github.com/pauti04/CostDNA";

export default function Home() {
  return (
    <main className="min-h-screen">
      {/* ────────── NAV ────────── */}
      <nav className="sticky top-0 z-50 backdrop-blur-md bg-bg/80 border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <a href="#" className="font-mono font-semibold tracking-tight text-text">
            ● CostDNA
          </a>
          <div className="flex gap-6 text-sm text-text-soft">
            <a href="#audit" className="hover:text-text transition">Audit</a>
            <a href="#how" className="hover:text-text transition">How it works</a>
            <a href="#tools" className="hover:text-text transition">Tools</a>
            <a href="#try" className="hover:text-text transition">Try it</a>
            <a href={GH_URL} className="text-text hover:underline" target="_blank">
              GitHub ↗
            </a>
          </div>
        </div>
      </nav>

      {/* ────────── HERO ────────── */}
      <section className="relative bg-bg-section border-b border-border overflow-hidden">
        <div className="absolute inset-0 grid-pattern opacity-60" aria-hidden />
        <div className="relative max-w-6xl mx-auto px-6 pt-20 pb-20">
          <FadeIn>
            <div className="font-mono text-[11px] text-text-muted uppercase tracking-[0.25em] mb-6 flex items-center gap-3">
              <span className="inline-block w-8 h-px bg-border-strong" />
              Open source · LLM agent over GraphSAGE
            </div>
          </FadeIn>
          <FadeIn delay={0.05}>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.05] text-balance text-text max-w-4xl">
              Ask your AWS bill questions.{" "}
              <span className="gradient-text">In English.</span>
            </h1>
          </FadeIn>
          <FadeIn delay={0.12}>
            <p className="mt-6 text-lg md:text-xl text-text-soft max-w-2xl text-balance leading-relaxed">
              A natural-language agent that infers resource ownership from CloudTrail,
              IAM, and cost behaviour using a Graph Neural Network.
              Answers questions like <em className="text-text">why did our bill spike Tuesday?</em>{" "}
              with specific resources, teams, and dollar amounts.
            </p>
          </FadeIn>
          <FadeIn delay={0.18}>
            <div className="mt-10 flex flex-wrap gap-3">
              <a
                href="#try"
                className="inline-flex items-center gap-2 bg-bg-deep text-text-on-deep font-medium px-6 py-3 rounded-md hover:bg-bg-deep-soft transition"
              >
                Try the live demo →
              </a>
              <a
                href={GH_URL}
                target="_blank"
                className="inline-flex items-center gap-2 bg-bg-section border border-border text-text font-medium px-6 py-3 rounded-md hover:border-border-strong transition"
              >
                View on GitHub ↗
              </a>
              <a
                href="#audit"
                className="inline-flex items-center gap-2 text-text-soft font-medium px-6 py-3 rounded-md hover:text-text transition"
              >
                The audit story
              </a>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ────────── BIG STATS STRIP ────────── */}
      <section className="bg-bg border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-14">
          <FadeIn>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-border rounded-lg overflow-hidden">
              {[
                ["2.6M", "Real Azure VMs in the audit set"],
                ["13/15", "Real-AWS attribution accuracy (87%)"],
                ["+53%", "Lift over best baseline (k-fold)"],
                ["3", "Clouds: AWS · Azure · GCP"],
              ].map(([v, l]) => (
                <div key={l} className="bg-bg-section p-6">
                  <div className="text-4xl md:text-5xl font-bold tracking-tight text-text">
                    {v}
                  </div>
                  <div className="text-xs text-text-soft mt-3 leading-snug">{l}</div>
                </div>
              ))}
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ────────── LIVE DEMO ────────── */}
      <section id="try" className="bg-bg-section border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="01" title="Try it live" />
          <FadeIn delay={0.05}>
            <p className="text-lg text-text-soft leading-relaxed max-w-3xl mb-10">
              Chat with the agent over a synthetic 68-resource AWS account. The
              agent has 9 tools — it picks which to chain based on your question,
              hits the GraphSAGE-attributed scan, and answers in plain English.
            </p>
          </FadeIn>
          <FadeIn delay={0.10}>
            <div className="rounded-xl shadow-soft-lg">
              <AskLive />
            </div>
          </FadeIn>
          <FadeIn delay={0.15}>
            <p className="mt-6 text-sm text-text-muted">
              Live demo runs on GPT-4o · ~$0.01 per question · rate-limited to 5/IP/hour
            </p>
          </FadeIn>
        </div>
      </section>

      {/* ────────── PROBLEM ────────── */}
      <section className="bg-bg border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="02" title="The problem" />
          <div className="grid md:grid-cols-2 gap-12 max-w-5xl">
            <FadeIn>
              <p className="text-lg text-text-soft leading-relaxed">
                Every FinOps team's most painful metric: the percentage of AWS spend
                that can't be attributed to any team. Industry estimates put it at{" "}
                <b className="text-text">40–60%</b>. Tagging is the standard answer,
                but tags drift. Resources are created in a hurry. Engineers leave.
              </p>
            </FadeIn>
            <FadeIn delay={0.05}>
              <p className="text-lg text-text-soft leading-relaxed">
                Existing FinOps dashboards (CloudHealth, Vantage, Apptio) are only
                as good as the tags you have — and on most accounts, the tags you
                have aren't enough. CostDNA is the input layer: a tool that{" "}
                <em className="text-text">infers</em> the missing tags from
                behaviour, then lets you ask English questions about the result.
              </p>
            </FadeIn>
          </div>
        </div>
      </section>

      {/* ────────── AUDIT STORY ────────── */}
      <section id="audit" className="bg-bg-section border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="03" title="The audit story" />
          <div className="max-w-4xl">
            <FadeIn>
              <p className="text-lg text-text-soft leading-relaxed mb-8">
                I had a 97% accuracy result on Microsoft's published 2.6M-VM
                Azure dataset. I audited it.{" "}
                <b className="text-text">It was a tautology.</b>
              </p>
            </FadeIn>

            {/* Big-number callout */}
            <FadeIn delay={0.05}>
              <div className="my-10 grid grid-cols-3 bg-bg rounded-xl border border-border overflow-hidden">
                <div className="p-6 border-r border-border">
                  <div className="text-xs uppercase tracking-wider text-text-muted mb-2">First-cut</div>
                  <div className="text-4xl font-bold text-text-soft line-through decoration-2">97%</div>
                  <div className="text-xs text-text-muted mt-2">Inflated by leak</div>
                </div>
                <div className="p-6 border-r border-border bg-bg-soft">
                  <div className="text-xs uppercase tracking-wider text-text-muted mb-2">Honest</div>
                  <div className="text-4xl font-bold text-text">6.9%</div>
                  <div className="text-xs text-text-muted mt-2">After audit, 100 classes</div>
                </div>
                <div className="p-6">
                  <div className="text-xs uppercase tracking-wider text-text-muted mb-2">Random baseline</div>
                  <div className="text-4xl font-bold text-text-muted">1%</div>
                  <div className="text-xs text-text-muted mt-2">12× lift remains</div>
                </div>
              </div>
            </FadeIn>

            <FadeIn delay={0.10}>
              <div className="my-8 p-6 rounded-lg bg-bg border-l-4 border-text">
                <div className="font-mono text-xs text-text-muted uppercase tracking-wider mb-3">
                  The catch
                </div>
                <p className="text-text leading-relaxed">
                  Across all <b>33,205 deployments</b> in the Azure trace,{" "}
                  <b>100%</b> mapped 1:1 to a single subscription. So{" "}
                  <code className="text-text bg-bg-soft px-1.5 py-0.5 rounded text-sm">
                    deployment_id
                  </code>
                  , used as a graph edge, was a perfect lookup of{" "}
                  <code className="text-text bg-bg-soft px-1.5 py-0.5 rounded text-sm">
                    subscription_id
                  </code>
                  . LabelProp's "97%" was a graph database join, not learning.
                </p>
              </div>
            </FadeIn>

            <FadeIn delay={0.15}>
              <p className="text-text-soft leading-relaxed mb-8">
                Most engineers stop when they see a high accuracy number and ship
                it. I caught the leak by asking{" "}
                <em className="text-text">"are you sure data is accurate?"</em>{" "}
                The same audit on Microsoft's Philly DL trace surfaced another
                partial leak: 85% of users belong to one virtual cluster. Three
                datasets, three different shortcuts, one consistent finding.
              </p>
            </FadeIn>

            <FadeIn delay={0.20}>
              <div className="overflow-x-auto rounded-xl border border-border shadow-soft">
                <table className="w-full text-sm">
                  <thead className="bg-bg-soft">
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
                        Honest behavioural
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border bg-bg-section">
                    {[
                      {
                        ds: "Microsoft Azure",
                        n: "2.6M VMs",
                        first: "97%",
                        shortcut: "deployment_id ≡ sub (100% deterministic)",
                        honest: "6.9% (12× rand)",
                      },
                      {
                        ds: "Microsoft Philly",
                        n: "117K jobs",
                        first: "89%",
                        shortcut: "user_id → vc (85% deterministic)",
                        honest: "14% (2× rand)",
                      },
                    ].map((row) => (
                      <tr key={row.ds}>
                        <td className="px-4 py-3 font-semibold text-text">{row.ds}</td>
                        <td className="px-4 py-3 text-right font-mono text-text-soft">
                          {row.n}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-text-muted line-through">
                          {row.first}
                        </td>
                        <td className="px-4 py-3 text-text-soft text-xs">
                          {row.shortcut}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-text font-semibold">{row.honest}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </FadeIn>

            <FadeIn delay={0.25}>
              <p className="mt-10 text-text-soft leading-relaxed">
                <b className="text-text">The methodological finding:</b> production
                cloud attribution is mostly a metadata-lookup problem. Behavioural
                fingerprinting matters specifically when metadata is missing or
                unreliable — exactly the gap CostDNA's synthetic env reproduces.
              </p>
            </FadeIn>
          </div>
        </div>
      </section>

      {/* ────────── HOW IT WORKS ────────── */}
      <section id="how" className="bg-bg border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="04" title="How it works" />
          <FadeIn>
            <p className="text-lg text-text-soft leading-relaxed max-w-3xl mb-12">
              Three layers, all cloud-agnostic. Only the collector layer (left)
              changes per cloud — the GNN and agent (right) are identical for
              AWS, Azure, and GCP.
            </p>
          </FadeIn>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                num: "1",
                title: "Collect",
                body: "Hardened boto3 / azure-mgmt / google-cloud collectors pull CloudTrail (or equivalent), Cost Explorer, IAM roles, VPC flow logs. Throttle-aware retry. AWS production-tested.",
              },
              {
                num: "2",
                title: "Train",
                body: "Behavioural features (peak_hour, write_ratio, event_diversity, …) + LLM-derived semantic features (sentence-transformer over IAM names) → 2/4-layer GraphSAGE GNN. Auto-shrinks for small label sets.",
              },
              {
                num: "3",
                title: "Ask",
                body: "9-tool LLM agent (GPT-4o / Claude) answers natural-language questions. Tools are pure data lookups against the trained scan output — fast, deterministic, auditable.",
              },
            ].map((step, i) => (
              <FadeIn key={step.num} delay={i * 0.05}>
                <div className="bg-bg-section border border-border rounded-xl p-6 h-full shadow-soft hover:shadow-soft-lg transition">
                  <div className="font-mono text-xs text-text-muted mb-3">
                    STEP {step.num}
                  </div>
                  <div className="text-2xl font-semibold text-text mb-3">
                    {step.title}
                  </div>
                  <p className="text-sm text-text-soft leading-relaxed">
                    {step.body}
                  </p>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* ────────── 9 TOOLS ────────── */}
      <section id="tools" className="bg-bg-section border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="05" title="10 tools the agent chains" />
          <FadeIn>
            <p className="text-lg text-text-soft leading-relaxed max-w-3xl mb-10">
              Each tool wraps a piece of the underlying CostDNA pipeline. The LLM
              decides which to call (or chain) based on the visitor's question.
            </p>
          </FadeIn>

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
              ["find_abandoned", "Resources whose activity has collapsed in the recent half of the window — likely abandoned. Sorted by spend."],
            ].map(([name, desc]) => (
              <div
                key={name}
                className="rounded-lg border border-border bg-bg p-4 hover:border-border-strong transition"
              >
                <code className="font-mono text-sm font-semibold text-text">{name}</code>
                <p className="mt-2 text-sm text-text-soft leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ────────── REAL-AWS RESULT ────────── */}
      <section className="bg-bg-deep text-text-on-deep border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="06" title="Real-AWS deployment" dark />
          <FadeIn>
            <p className="text-lg text-zinc-300 leading-relaxed max-w-3xl mb-10">
              Provisioned a labeled AWS environment, ran per-team workload
              simulators on a 24/7 EC2 to generate authentic CloudTrail signal,
              scanned the live account. Same code that powers the live demo.
            </p>
          </FadeIn>
          <div className="grid md:grid-cols-3 gap-6 max-w-5xl">
            {[
              ["13 / 15", "Per-resource accuracy (87%)"],
              ["13 / 13", "High-confidence (≥0.79) accuracy — 100%"],
              ["13,402", "CloudTrail events processed"],
            ].map(([v, l]) => (
              <div key={l} className="bg-bg-deep-soft rounded-xl p-6 border border-zinc-700">
                <div className="text-3xl font-bold text-text-on-deep">{v}</div>
                <div className="text-sm text-zinc-300 mt-2">{l}</div>
              </div>
            ))}
          </div>
          <FadeIn delay={0.10}>
            <p className="mt-10 text-sm text-zinc-400 max-w-3xl leading-relaxed">
              Both wrong predictions came back with confidence below 0.7 and were
              correctly surfaced by <code className="bg-bg-deep-soft px-1.5 py-0.5 rounded text-zinc-300">find_anomalies</code> for human review —
              exactly the active-learning workflow the system is designed for.
              Verification artifacts in <a href="https://github.com/pauti04/CostDNA/tree/main/docs/real-aws-evidence" className="underline" target="_blank">docs/real-aws-evidence/</a>.
            </p>
          </FadeIn>
        </div>
      </section>

      {/* ────────── VISUAL PROOF ────────── */}
      <section className="bg-bg border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="07" title="Visual proof — embedding space" />
          <FadeIn>
            <p className="text-lg text-text-soft leading-relaxed max-w-3xl mb-10">
              GraphSAGE learns a 2D-projected representation where same-team
              resources cluster together and unowned ones sit visibly separate.
            </p>
          </FadeIn>

          <FadeIn delay={0.05}>
            <div className="rounded-xl overflow-hidden border border-border bg-bg-section shadow-soft">
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
          <p className="mt-4 text-sm text-text-muted max-w-3xl">
            Synthetic AWS env. The tan{" "}
            <span className="font-mono text-text-soft">unowned</span> cluster (vendor
            / legacy / orphan / shadow resources) sits visibly apart from the
            team clusters. The anomaly detector catches them automatically.
          </p>
        </div>
      </section>

      {/* ────────── MULTI-CLOUD ────────── */}
      <section className="bg-bg-section border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="08" title="Multi-cloud architecture" />
          <FadeIn>
            <p className="text-lg text-text-soft leading-relaxed max-w-3xl mb-10">
              The model + features + agent are cloud-agnostic — only the
              collector layer is provider-specific. AWS calls{" "}
              <code className="bg-bg-soft px-1.5 py-0.5 rounded text-sm">cloudtrail:LookupEvents</code>;
              Azure calls{" "}
              <code className="bg-bg-soft px-1.5 py-0.5 rounded text-sm">monitor.activity_logs.list</code>;
              GCP calls{" "}
              <code className="bg-bg-soft px-1.5 py-0.5 rounded text-sm">cloud_logging.list_entries</code>.
              Same downstream pipeline.
            </p>
          </FadeIn>
          <div className="grid md:grid-cols-3 gap-4">
            {[
              { name: "AWS", status: "Production-tested", note: "13/15 = 87% on real AWS · live demo runs against this stack",
                stat: "✓" },
              { name: "Azure", status: "Implemented · awaiting validation", note: "Code follows azure-mgmt-resource v25 + activity-logs + cost-management v4 patterns; mocked-shape tests pass",
                stat: "—" },
              { name: "GCP", status: "Implemented · awaiting validation", note: "Code follows google-cloud-asset v4 + cloud-logging protobuf payloads; mocked-shape tests pass",
                stat: "—" },
            ].map((c) => (
              <div key={c.name} className="rounded-xl border border-border bg-bg p-6">
                <div className="flex items-baseline justify-between mb-3">
                  <div className="text-2xl font-semibold text-text">{c.name}</div>
                  <div className="text-3xl font-bold text-text-muted">{c.stat}</div>
                </div>
                <div className="text-xs uppercase tracking-wider text-text-muted mb-3">
                  {c.status}
                </div>
                <p className="text-sm text-text-soft leading-relaxed">{c.note}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ────────── INSTALL ────────── */}
      <section className="bg-bg border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="09" title="Run it yourself" />
          <FadeIn>
            <p className="text-lg text-text-soft leading-relaxed max-w-3xl mb-10">
              Three usage patterns — CLI, REPL, web UI. All run against the same
              agent code that powers the live demo above.
            </p>
          </FadeIn>

          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-semibold text-text mb-3 flex items-center gap-2">
                <span className="font-mono text-xs text-text-muted">A.</span>
                One-shot CLI
              </h3>
              <CodeBlock
                filename="bash"
                code={`$ costdna ask "why did our bill spike Tuesday?" \\
    --from-dir runs/today`}
              />
            </div>
            <div>
              <h3 className="font-semibold text-text mb-3 flex items-center gap-2">
                <span className="font-mono text-xs text-text-muted">B.</span>
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
              <h3 className="font-semibold text-text mb-3 flex items-center gap-2">
                <span className="font-mono text-xs text-text-muted">C.</span>
                Web chat UI (Streamlit)
              </h3>
              <CodeBlock
                filename="bash"
                code={`$ pip install 'costdna[ui,agent]'
$ costdna serve
# open http://localhost:8501 → "Chat with the agent" tab`}
              />
            </div>
            <div>
              <h3 className="font-semibold text-text mb-3 flex items-center gap-2">
                <span className="font-mono text-xs text-text-muted">D.</span>
                Docker (no install)
              </h3>
              <CodeBlock
                filename="bash"
                code={`$ docker run --rm pauti04/costdna scan --synthetic`}
              />
            </div>
          </div>

          <p className="mt-8 text-sm text-text-muted max-w-3xl">
            Setup for the agent commands:{" "}
            <code className="font-mono text-text bg-bg-soft px-1.5 py-0.5 rounded">pip install 'costdna[agent]'</code> +{" "}
            <code className="font-mono text-text bg-bg-soft px-1.5 py-0.5 rounded">export ANTHROPIC_API_KEY=...</code>
          </p>
        </div>
      </section>

      {/* ────────── STACK ────────── */}
      <section className="bg-bg-section border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="10" title="Stack" />
          <ul className="grid md:grid-cols-2 gap-x-12 gap-y-4 text-text-soft max-w-5xl">
            {[
              ["Python 3.11", "pandas, numpy, scikit-learn, statsmodels, networkx"],
              ["PyTorch 2.x + PyTorch Geometric", "GraphSAGE classifier — 2 to 4 layers, residual"],
              ["sentence-transformers", "MiniLM embeddings of IAM role names + resource IDs + tags"],
              ["OpenAI + Anthropic SDKs", "tool-using agent loop — pluggable backend"],
              ["boto3 (hardened)", "adaptive retry, throttle-aware CloudTrail lookup_events"],
              ["azure-mgmt-* + google-cloud-*", "multi-cloud collectors (lazy-loaded extras)"],
              ["Streamlit + Click + Rich", "CLI commands + interactive chat UI"],
              ["Terraform", "labelled AWS env with CloudTrail data events + VPC Flow Logs"],
              ["pytest + GitHub Actions", "CI on every commit; Docker auto-publish on tag"],
              ["Next.js + Vercel", "this landing page + serverless agent endpoint"],
            ].map(([head, body]) => (
              <li key={head} className="flex gap-3 items-start">
                <span className="text-text-muted mt-1.5 text-xs">▸</span>
                <span>
                  <b className="text-text">{head}</b>
                  <span className="ml-2 text-text-soft">— {body}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* ────────── FINAL CTA ────────── */}
      <section className="bg-bg-deep text-text-on-deep">
        <div className="max-w-4xl mx-auto px-6 py-20 text-center">
          <FadeIn>
            <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-text-on-deep mb-6">
              Open source. Forkable. Ready.
            </h2>
          </FadeIn>
          <FadeIn delay={0.05}>
            <p className="text-lg text-zinc-300 mb-10 max-w-2xl mx-auto leading-relaxed">
              MIT licensed, hardened collectors, multi-cloud architecture, real-AWS
              numbers in the README. If you're hiring for cloud-cost / FinOps /
              ML-infra roles — I'd like to do this kind of work full-time.
            </p>
          </FadeIn>
          <FadeIn delay={0.10}>
            <div className="flex flex-wrap gap-3 justify-center">
              <a
                href={GH_URL}
                target="_blank"
                className="inline-flex items-center gap-2 bg-bg-section text-text font-medium px-6 py-3 rounded-md hover:bg-bg-soft transition"
              >
                ↗ View on GitHub
              </a>
              <a
                href="#try"
                className="inline-flex items-center gap-2 border border-zinc-600 text-text-on-deep font-medium px-6 py-3 rounded-md hover:bg-bg-deep-soft transition"
              >
                Try the live demo
              </a>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ────────── FOOTER ────────── */}
      <footer className="bg-bg border-t border-border">
        <div className="max-w-6xl mx-auto px-6 py-10 flex flex-wrap items-center justify-between gap-4 text-sm text-text-soft">
          <div>
            Built by{" "}
            <a
              href="https://github.com/pauti04"
              className="text-text hover:underline"
            >
              @pauti04
            </a>{" "}
            ·{" "}
            <a
              href={GH_URL}
              className="text-text hover:underline"
              target="_blank"
            >
              github.com/pauti04/CostDNA
            </a>
          </div>
          <div>MIT licensed</div>
        </div>
      </footer>
    </main>
  );
}

/* ─────────────────────── helpers ─────────────────────── */

function SectionHeader({
  number,
  title,
  dark = false,
}: {
  number: string;
  title: string;
  dark?: boolean;
}) {
  return (
    <FadeIn>
      <div className="flex items-center gap-3 mb-4">
        <span className={`font-mono text-xs ${dark ? "text-zinc-400" : "text-text-muted"}`}>
          {number}
        </span>
        <span className={`h-px w-10 ${dark ? "bg-zinc-600" : "bg-border-strong"}`} />
      </div>
      <h2 className={`text-3xl md:text-4xl font-bold tracking-tight mb-10 ${dark ? "text-text-on-deep" : "text-text"}`}>
        {title}
      </h2>
    </FadeIn>
  );
}
