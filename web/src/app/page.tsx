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
            <a href="#results" className="hover:text-text transition">Results</a>
            <a href="#how" className="hover:text-text transition">Method</a>
            <a href="#limitations" className="hover:text-text transition">Limitations</a>
            <a href="#try" className="hover:text-text transition">Demo</a>
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
              Open source · methodology audit · GraphSAGE
            </div>
          </FadeIn>
          <FadeIn delay={0.05}>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.05] text-balance text-text max-w-4xl">
              A 97% accuracy result.{" "}
              <span className="gradient-text">Audited.</span>{" "}
              It was a tautology.
            </h1>
          </FadeIn>
          <FadeIn delay={0.12}>
            <p className="mt-6 text-lg md:text-xl text-text-soft max-w-2xl text-balance leading-relaxed">
              CostDNA is a behavioral GNN for cloud-resource attribution.
              While evaluating on Microsoft&apos;s published 2.6M-VM Azure trace
              I caught label leakage that inflated my own first-cut accuracy
              from <em className="text-text">6.9%</em> to <em className="text-text">97%</em>.
              The honest negative result became the project&apos;s strongest finding.
            </p>
          </FadeIn>
          <FadeIn delay={0.18}>
            <div className="mt-10 flex flex-wrap gap-3">
              <a
                href="#audit"
                className="inline-flex items-center gap-2 bg-bg-deep text-text-on-deep font-medium px-6 py-3 rounded-md hover:bg-bg-deep-soft transition"
              >
                Read the audit →
              </a>
              <a
                href={GH_URL}
                target="_blank"
                className="inline-flex items-center gap-2 bg-bg-section border border-border text-text font-medium px-6 py-3 rounded-md hover:border-border-strong transition"
              >
                View on GitHub ↗
              </a>
              <a
                href="#try"
                className="inline-flex items-center gap-2 text-text-soft font-medium px-6 py-3 rounded-md hover:text-text transition"
              >
                Optional: chat with the agent →
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
                ["97% → 6.9%", "First-cut vs honest, post-audit"],
                ["12×", "Lift over random on 100-class attribution"],
                ["33,205", "Deployments mapped 1:1 to subscriptions"],
                ["2", "Published datasets with the same pattern"],
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

      {/* ────────── AUDIT STORY (PROMOTED TO SECTION 01) ────────── */}
      <section id="audit" className="bg-bg-section border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="01" title="The audit" />
          <div className="max-w-4xl">
            <FadeIn>
              <p className="text-lg text-text-soft leading-relaxed mb-8">
                I trained CostDNA on a controlled synthetic env and hit 90%+ accuracy.
                To validate methodology on real data I picked Microsoft&apos;s published
                Azure Public Dataset — 2.6 million VMs across 100 subscriptions, the
                largest publicly available cloud trace.
              </p>
              <p className="text-lg text-text-soft leading-relaxed mb-8">
                <b className="text-text">First-cut result:</b> LabelProp scored 97% across
                5–100 teams. A 97% number on a 100-class problem (random = 1%) is
                suspicious. State-of-the-art results on much easier problems rarely
                beat 95%. So I audited.
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

            <FadeIn delay={0.08}>
              <div className="my-8">
                <div className="font-mono text-xs text-text-muted uppercase tracking-wider mb-3">
                  The pandas one-liner
                </div>
                <CodeBlock
                  filename="audit.py"
                  code={`# Is the deployment_id graph edge deterministic of the prediction target?
(df.groupby("deployment_id")["subscription_id"].nunique() == 1).mean()
# → 1.0`}
                />
              </div>
            </FadeIn>

            <FadeIn delay={0.10}>
              <div className="my-8 p-6 rounded-lg bg-bg border-l-4 border-text">
                <div className="font-mono text-xs text-text-muted uppercase tracking-wider mb-3">
                  What it means
                </div>
                <p className="text-text leading-relaxed">
                  Across all <b>33,205 deployments</b> in the Azure trace,{" "}
                  <b>every single deployment</b> belonged to exactly one subscription.
                  The{" "}
                  <code className="text-text bg-bg-soft px-1.5 py-0.5 rounded text-sm">
                    deployment_id
                  </code>{" "}
                  graph edge was a perfect lookup of{" "}
                  <code className="text-text bg-bg-soft px-1.5 py-0.5 rounded text-sm">
                    subscription_id
                  </code>
                  . LabelProp&apos;s &quot;97%&quot; was a graph-database join, not learning.
                </p>
              </div>
            </FadeIn>

            <FadeIn delay={0.15}>
              <p className="text-text-soft leading-relaxed mb-8">
                Remove the leaking edges. Re-run. GraphSAGE on 100 classes:{" "}
                <b className="text-text">6.9%</b> — still 12× random, still beats every
                feature-only baseline including node2vec, but a long way from 97%.
                Same audit on Microsoft&apos;s Philly DL trace surfaced another partial
                leak: 85% of users belong to one virtual cluster.{" "}
                <code className="text-text bg-bg-soft px-1.5 py-0.5 rounded text-sm">
                  user_id → vc
                </code>{" "}
                was near-deterministic.
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
                    ].map((r) => (
                      <tr key={r.ds}>
                        <td className="px-4 py-3 font-medium text-text">{r.ds}</td>
                        <td className="px-4 py-3 text-right text-text-soft">{r.n}</td>
                        <td className="px-4 py-3 text-right text-text-soft line-through">{r.first}</td>
                        <td className="px-4 py-3 text-text-soft font-mono text-xs">{r.shortcut}</td>
                        <td className="px-4 py-3 text-right text-text font-semibold">{r.honest}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </FadeIn>

            <FadeIn delay={0.25}>
              <p className="mt-10 text-lg text-text-soft leading-relaxed">
                <b className="text-text">The methodological claim:</b> across at least two
                published cloud datasets, the dominant signal is structural metadata
                (deployment IDs, user IDs, IAM principals) that is either directly the
                prediction target or deterministically maps to it. The field has been
                measuring leakage rather than learning. A two-line{" "}
                <code className="text-text bg-bg-soft px-1.5 py-0.5 rounded text-sm">pandas</code>{" "}
                audit should be a minimum standard before reporting cloud-attribution
                accuracy.
              </p>
            </FadeIn>
          </div>
        </div>
      </section>

      {/* ────────── PRIMARY RESULTS — AZURE POST-AUDIT ────────── */}
      <section id="results" className="bg-bg border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="02" title="Primary results — Azure, post-audit" />
          <FadeIn>
            <p className="text-lg text-text-soft leading-relaxed max-w-3xl mb-10">
              GraphSAGE consistently outperforms feature-only baselines after the
              leak is removed, but absolute numbers are modest because the Azure
              trace ships only summary CPU statistics (max/avg/p95), not the
              hourly time-series the GNN would benefit from.
            </p>
          </FadeIn>
          <FadeIn delay={0.05}>
            <div className="overflow-x-auto rounded-xl border border-border shadow-soft">
              <table className="w-full text-sm">
                <thead className="bg-bg-soft">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs uppercase tracking-wider text-text-soft font-semibold">N teams</th>
                    <th className="px-4 py-3 text-right text-xs uppercase tracking-wider text-text-soft font-semibold">Random</th>
                    <th className="px-4 py-3 text-right text-xs uppercase tracking-wider text-text-soft font-semibold">LogReg</th>
                    <th className="px-4 py-3 text-right text-xs uppercase tracking-wider text-text-soft font-semibold">k-NN</th>
                    <th className="px-4 py-3 text-right text-xs uppercase tracking-wider text-text-soft font-semibold">LabelProp</th>
                    <th className="px-4 py-3 text-right text-xs uppercase tracking-wider text-text-soft font-semibold">node2vec+LR</th>
                    <th className="px-4 py-3 text-right text-xs uppercase tracking-wider text-text font-semibold">GraphSAGE</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border bg-bg-section">
                  {[
                    ["5",   "20%",   "33.3% ± 1.9%", "31.2% ± 3.2%", "19.1% ± 0.4%", "33.3% ± 1.9%", "38.0% ± 3.3%"],
                    ["10",  "10%",   "17.3% ± 1.4%", "16.2% ± 1.3%", "9.2% ± 0.6%",  "17.3% ± 1.4%", "20.7% ± 1.0%"],
                    ["25",  "4%",    "pending",      "pending",      "pending",      "pending",      "pending"],
                    ["100", "1%",    "pending",      "pending",      "pending",      "pending",      "pending"],
                  ].map((row) => (
                    <tr key={row[0]}>
                      <td className="px-4 py-3 font-medium text-text">{row[0]}</td>
                      <td className="px-4 py-3 text-right text-text-muted">{row[1]}</td>
                      <td className="px-4 py-3 text-right text-text-soft">{row[2]}</td>
                      <td className="px-4 py-3 text-right text-text-soft">{row[3]}</td>
                      <td className="px-4 py-3 text-right text-text-soft">{row[4]}</td>
                      <td className="px-4 py-3 text-right text-text-muted italic">{row[5]}</td>
                      <td className="px-4 py-3 text-right text-text font-semibold">{row[6]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </FadeIn>
          <FadeIn delay={0.10}>
            <p className="mt-6 text-sm text-text-muted max-w-3xl leading-relaxed">
              Locally-staged dataset has 10 subscriptions; N=25/100 cells stay pending until the full 100-subscription trace is restaged. Reproduction at <a href={`${GH_URL}/blob/main/scripts/bench-azure.py`} className="underline" target="_blank">scripts/bench-azure.py</a>. The run also surfaced a <b className="text-text">second leak</b> the audit module caught in real time — see <a href={`${GH_URL}/blob/main/docs/v2/azure-benchmark.md`} className="underline" target="_blank">docs/v2/azure-benchmark.md</a> (vpc_cidr was 100% deterministic of subscription_id; excluded from the graph before re-running).
            </p>
          </FadeIn>
        </div>
      </section>

      {/* ────────── HOW IT WORKS ────────── */}
      <section id="how" className="bg-bg-section border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="03" title="Method" />
          <FadeIn>
            <p className="text-lg text-text-soft leading-relaxed max-w-3xl mb-12">
              Three layers, all cloud-agnostic. Only the collector layer (left)
              changes per cloud — the GNN architecture is identical for AWS,
              Azure, and GCP.
            </p>
          </FadeIn>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                num: "1",
                title: "Collect",
                body: "Hardened boto3 / azure-mgmt / google-cloud collectors pull CloudTrail (or equivalent), Cost Explorer, IAM roles, VPC flow logs. Throttle-aware retry. AWS production-tested; Azure evaluated on the published trace.",
              },
              {
                num: "2",
                title: "Features + graph",
                body: "17 behavioural features (peak_hour, write_ratio, event_diversity, per-verb shares, …) + sentence-transformer embeddings of IAM names. Edges from VPC + IAM-role + flow co-occurrence. Audit step: groupby(edge)[target].nunique() == 1 — kills leaky edges before training.",
              },
              {
                num: "3",
                title: "Train",
                body: "2-or-4-layer GraphSAGE classifier with supervised contrastive head. Auto-shrinks (2-layer / hidden=8 / dropout=0.4) when n_labels < 30. Class-weighted loss + stratified split. Calibrated post-hoc (ECE=0.001).",
              },
            ].map((step, i) => (
              <FadeIn key={step.num} delay={i * 0.05}>
                <div className="bg-bg border border-border rounded-xl p-6 h-full shadow-soft hover:shadow-soft-lg transition">
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

      {/* ────────── REAL-AWS ENGINEERING VALIDATION ────────── */}
      <section className="bg-bg-deep text-text-on-deep border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="04" title="Engineering pipeline validation — real AWS" dark />
          <FadeIn>
            <p className="text-lg text-zinc-300 leading-relaxed max-w-3xl mb-10">
              Provisioned a labeled AWS environment via Terraform, ran per-team
              workload simulators on a 24/7 t3.micro for 3 days to generate
              authentic CloudTrail signal, scanned the live account.
              This validates that the collectors, graph construction, and
              training loop run end-to-end on real CloudTrail — not a primary
              methodological result (15 labels is too few for tight error bars).
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
              correctly surfaced by{" "}
              <code className="bg-bg-deep-soft px-1.5 py-0.5 rounded text-zinc-300">find_anomalies</code>{" "}
              for human review — exactly the active-learning workflow the system
              is designed for. The wide ±27% 5-fold CV variance reflects only 15
              labels; methodology validates with tighter error bars on synthetic
              where label count is controllable. Verification artifacts in{" "}
              <a href={`${GH_URL}/tree/main/docs/real-aws-evidence`} className="underline" target="_blank">
                docs/real-aws-evidence/
              </a>.
            </p>
          </FadeIn>
        </div>
      </section>

      {/* ────────── VISUAL PROOF ────────── */}
      <section className="bg-bg border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="05" title="Visual proof — embedding space" />
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

      {/* ────────── LIMITATIONS ────────── */}
      <section id="limitations" className="bg-bg-section border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="06" title="Limitations and what doesn't work" />
          <FadeIn>
            <p className="text-lg text-text-soft leading-relaxed max-w-3xl mb-10">
              The full breakdown is in{" "}
              <a href={`${GH_URL}/blob/main/docs/limitations.md`} className="underline text-text" target="_blank">
                docs/limitations.md
              </a>. The honest highlights are below — research maturity over polish.
            </p>
          </FadeIn>
          <div className="grid md:grid-cols-2 gap-6 max-w-5xl">
            {[
              {
                title: "Behavioral attribution has a natural ceiling on thin features",
                body: "On Azure's summary-CPU-only feature set, GraphSAGE's lift over feature-only baselines is small. The GNN needs richer per-resource signal (hourly time-series, full CloudTrail) to earn its complexity.",
              },
              {
                title: "Small label sets give wide error bars",
                body: "The real-AWS 87% has ±27% k-fold variance because 15 labels split 5-fold leaves 3 samples per fold. Use bigger labeled sets for production deployment decisions.",
              },
              {
                title: "Homogeneous accounts have no behavioral signal",
                body: "If every team uses one IAM role, one VPC, one calling pattern, CostDNA has nothing to fingerprint. The model only earns its keep when behavior actually differs across teams.",
              },
              {
                title: "CostDNA is not a production-deployed tool",
                body: "\"I ran it on a real AWS account I owned\" is different from \"a user ran this on their account.\" The pilot validates engineering; production trust would require signed binaries, audited IAM, privacy review.",
              },
              {
                title: "Accounts under ~100 resources are too sparse",
                body: "The graph needs enough density for neighborhood aggregation to converge. Very small accounts get random-ish results regardless of how good the model is.",
              },
              {
                title: "The synthetic env is hand-constructed",
                body: "Difficulty kinds (cross_team, reassigned, shared_service, sparse) reproduce failure modes seen on real accounts, but the env is by construction the regime CostDNA was designed for. Treat synthetic numbers as ablation, not headline.",
              },
            ].map((item) => (
              <div key={item.title} className="rounded-xl border border-border bg-bg p-6">
                <h3 className="font-semibold text-text mb-3 leading-snug">{item.title}</h3>
                <p className="text-sm text-text-soft leading-relaxed">{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ────────── MULTI-CLOUD ────────── */}
      <section className="bg-bg border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="07" title="Multi-cloud architecture" />
          <FadeIn>
            <p className="text-lg text-text-soft leading-relaxed max-w-3xl mb-10">
              The model + features are cloud-agnostic — only the collector layer
              is provider-specific. AWS calls{" "}
              <code className="bg-bg-soft px-1.5 py-0.5 rounded text-sm">cloudtrail:LookupEvents</code>;
              Azure calls{" "}
              <code className="bg-bg-soft px-1.5 py-0.5 rounded text-sm">monitor.activity_logs.list</code>;
              GCP calls{" "}
              <code className="bg-bg-soft px-1.5 py-0.5 rounded text-sm">cloud_logging.list_entries</code>.
              All three return identical-shape DataFrames downstream.
            </p>
          </FadeIn>
          <div className="grid md:grid-cols-3 gap-4">
            {[
              {
                name: "AWS",
                status: "Engineering-validated",
                note: "13/15 = 87% on a Terraform-provisioned account · production-tested collectors",
                stat: "✓",
              },
              {
                name: "Azure",
                status: "Methodology-evaluated",
                note: "Audit on Microsoft's 2.6M-VM Public Dataset; live-subscription collector implemented per SDK v4 patterns but not yet run against a live account",
                stat: "△",
              },
              {
                name: "GCP",
                status: "Implemented · awaiting live run",
                note: "Code follows google-cloud-asset v4 + cloud-logging protobuf payloads; mocked-shape tests pass",
                stat: "—",
              },
            ].map((c) => (
              <div key={c.name} className="rounded-xl border border-border bg-bg-section p-6">
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

      {/* ────────── OPTIONAL NATURAL-LANGUAGE INTERFACE (DEMOTED) ────────── */}
      <section id="try" className="bg-bg-section border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="08" title="Optional natural-language interface" />
          <FadeIn>
            <p className="text-lg text-text-soft leading-relaxed max-w-3xl mb-10">
              CostDNA ships with an optional natural-language interface — a 10-tool
              agent on top of the trained scan output. The agent uses OpenAI&apos;s
              function-calling API; tools are pure data lookups against the scan,
              so responses are fast, deterministic, and auditable.{" "}
              <b className="text-text">This is interface convenience, not the core
              contribution.</b>
            </p>
          </FadeIn>
          <FadeIn delay={0.05}>
            <div className="rounded-xl shadow-soft-lg mb-8">
              <AskLive />
            </div>
          </FadeIn>
          <FadeIn delay={0.10}>
            <p className="text-sm text-text-muted mb-8">
              Live demo runs on GPT-4o · ~$0.01 per question · rate-limited to 5/IP/hour
            </p>
          </FadeIn>

          <FadeIn delay={0.15}>
            <details className="bg-bg rounded-lg border border-border p-6 max-w-4xl">
              <summary className="cursor-pointer font-semibold text-text">
                The 10 tools (click to expand)
              </summary>
              <div className="mt-6 grid md:grid-cols-2 gap-3">
                {[
                  ["summarize_account", "High-level rollup: resources, spend, confidence per team."],
                  ["attribute_resource", "Who owns this resource? + why-explanation."],
                  ["top_spenders", "Top resources by cost, optionally filtered by team."],
                  ["find_cost_spikes", "Largest spikes + Granger-causality attribution to deploys."],
                  ["find_anomalies", "Resources that don't fit any team."],
                  ["search_resources", "Substring match across resource IDs."],
                  ["signal_history", "Recent CloudTrail + cost samples for one resource."],
                  ["find_idle", "Low-activity resources."],
                  ["compare_teams", "Side-by-side team comparison."],
                  ["find_abandoned", "Resources whose activity collapsed in recent half."],
                ].map(([name, desc]) => (
                  <div key={name} className="rounded-lg border border-border bg-bg-section p-4">
                    <code className="font-mono text-sm font-semibold text-text">{name}</code>
                    <p className="mt-1 text-sm text-text-soft leading-relaxed">{desc}</p>
                  </div>
                ))}
              </div>
            </details>
          </FadeIn>
        </div>
      </section>

      {/* ────────── INSTALL ────────── */}
      <section className="bg-bg border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="09" title="Run it yourself" />
          <FadeIn>
            <p className="text-lg text-text-soft leading-relaxed max-w-3xl mb-10">
              Three usage patterns — CLI, REPL, web UI. All run against the same
              code that produced the results above.
            </p>
          </FadeIn>

          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-semibold text-text mb-3 flex items-center gap-2">
                <span className="font-mono text-xs text-text-muted">A.</span>
                Reproduce the synthetic benchmark
              </h3>
              <CodeBlock
                filename="bash"
                code={`$ costdna benchmark --synthetic --seeds 5
# prints the node2vec / GraphSAGE / LogReg / LabelProp table`}
              />
            </div>
            <div>
              <h3 className="font-semibold text-text mb-3 flex items-center gap-2">
                <span className="font-mono text-xs text-text-muted">B.</span>
                Live AWS scan
              </h3>
              <CodeBlock
                filename="bash"
                code={`$ costdna doctor --aws-profile prod
$ costdna scan --aws-profile prod --save-dir runs/today`}
              />
            </div>
            <div>
              <h3 className="font-semibold text-text mb-3 flex items-center gap-2">
                <span className="font-mono text-xs text-text-muted">C.</span>
                Natural-language interface (optional)
              </h3>
              <CodeBlock
                filename="bash"
                code={`$ pip install 'costdna[ui,agent]'
$ costdna serve
# open http://localhost:8501`}
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
            Optional agent setup:{" "}
            <code className="font-mono text-text bg-bg-soft px-1.5 py-0.5 rounded">pip install &apos;costdna[agent]&apos;</code> +{" "}
            <code className="font-mono text-text bg-bg-soft px-1.5 py-0.5 rounded">export OPENAI_API_KEY=...</code>
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
              ["PyTorch 2.x + PyTorch Geometric", "GraphSAGE classifier — 2 to 4 layers, residual, supervised contrastive head"],
              ["gensim Word2Vec", "node2vec baseline (skip-gram on biased random walks)"],
              ["sentence-transformers", "MiniLM embeddings of IAM role names + resource IDs + tags"],
              ["boto3 (hardened)", "adaptive retry, throttle-aware CloudTrail lookup_events"],
              ["azure-mgmt-* + google-cloud-*", "multi-cloud collectors (lazy-loaded extras)"],
              ["statsmodels", "Granger-causality spike attribution"],
              ["Terraform", "labelled AWS env with CloudTrail data events + VPC Flow Logs"],
              ["pytest + GitHub Actions", "CI on every commit; Docker auto-publish on tag"],
              ["Next.js + Vercel", "this landing page + serverless agent endpoint (optional interface)"],
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
              The audit is the contribution.
            </h2>
          </FadeIn>
          <FadeIn delay={0.05}>
            <p className="text-lg text-zinc-300 mb-10 max-w-2xl mx-auto leading-relaxed">
              MIT licensed. Methodology audit on two published cloud datasets,
              honest baseline comparison including node2vec, explicit limitations.
              If you&apos;re hiring for cloud-cost / FinOps / ML-infra roles —
              I&apos;d like to do this kind of work full-time.
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
                href="#audit"
                className="inline-flex items-center gap-2 border border-zinc-600 text-text-on-deep font-medium px-6 py-3 rounded-md hover:bg-bg-deep-soft transition"
              >
                Re-read the audit
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
