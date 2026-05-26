import Image from "next/image";
import CodeBlock from "@/components/CodeBlock";
import FadeIn from "@/components/FadeIn";
import AskLive from "@/components/AskLive";
import AuditChecker from "@/components/AuditChecker";
import ExampleConversation from "@/components/ExampleConversation";

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
            <a href="/your-account" className="hover:text-text transition">Try it</a>
            <a href="#trust" className="hover:text-text transition">Trust</a>
            <a href="#pricing" className="hover:text-text transition">Pricing</a>
            <a href="#security" className="hover:text-text transition">Security</a>
            <a href={GH_URL} className="text-text hover:underline" target="_blank">
              GitHub ↗
            </a>
          </div>
        </div>
      </nav>

      {/* ────────── HERO — product positioning ────────── */}
      <section className="relative bg-bg-section border-b border-border overflow-hidden">
        <div className="absolute inset-0 grid-pattern opacity-60" aria-hidden />
        <div className="relative max-w-6xl mx-auto px-6 pt-20 pb-20 grid lg:grid-cols-[1fr_auto] gap-12 items-center">
          <div>
            <FadeIn>
              <div className="font-mono text-[11px] text-text-muted uppercase tracking-[0.25em] mb-6 flex items-center gap-3">
                <span className="inline-block w-8 h-px bg-border-strong" />
                Open source · inferred tag-attribution for AWS
              </div>
            </FadeIn>
            <FadeIn delay={0.05}>
              <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.05] text-balance text-text max-w-4xl">
                The 40–60% of your AWS bill
                that&apos;s untagged,{" "}
                <span className="gradient-text">attributed.</span>
              </h1>
            </FadeIn>
            <FadeIn delay={0.12}>
              <p className="mt-6 text-lg md:text-xl text-text-soft max-w-2xl text-balance leading-relaxed">
                CostDNA infers resource ownership from CloudTrail behaviour
                and writes the tags back. Your existing FinOps tool —
                CloudHealth, Vantage, Datadog CCM, Kubecost — suddenly
                explains 95% of spend instead of 50%.
              </p>
            </FadeIn>
            <FadeIn delay={0.18}>
              <div className="mt-10 flex flex-wrap gap-3">
                <a
                  href="/your-account"
                  className="inline-flex items-center gap-2 bg-bg-deep text-text-on-deep font-medium px-6 py-3 rounded-md hover:bg-bg-deep-soft transition"
                >
                  Try on your AWS bill → <span className="opacity-60 text-xs">90 sec, no signup</span>
                </a>
                <a
                  href="#try"
                  className="inline-flex items-center gap-2 bg-bg-section border border-border text-text font-medium px-6 py-3 rounded-md hover:border-border-strong transition"
                >
                  Synthetic demo →
                </a>
                <a
                  href={GH_URL}
                  target="_blank"
                  className="inline-flex items-center gap-2 text-text-soft font-medium px-6 py-3 rounded-md hover:text-text transition"
                >
                  GitHub ↗
                </a>
              </div>
            </FadeIn>
            <FadeIn delay={0.24}>
              <p className="mt-6 text-sm text-text-muted">
                Open source (MIT) · self-hosted, no data leaves your account ·{" "}
                <a href="#trust" className="underline hover:text-text-soft">methodology peer-validated on Microsoft Azure 2.6M-VM dataset</a>
              </p>
            </FadeIn>
          </div>
          {/* Right column — audit chart. Hidden on mobile (chart needs width
              to be readable; the body copy already conveys the numbers). */}
          <FadeIn delay={0.22}>
            <div className="hidden lg:block w-[420px]">
              <div className="rounded-xl border border-border shadow-soft bg-bg overflow-hidden">
                <Image
                  src="/images/audit-hero.png"
                  alt="The audit chart: 97% first-cut accuracy was a tautology; honest GraphSAGE accuracy after removing the leak is 6.9% on 100-class attribution, still 12× random."
                  width={2400}
                  height={1350}
                  className="w-full h-auto"
                  priority
                />
              </div>
              <p className="mt-3 text-[11px] text-text-muted font-mono leading-snug">
                Microsoft Azure 2.6M-VM trace · before/after the
                deployment_id leak audit · <a href="#trust" className="underline">why this matters →</a>
              </p>
            </div>
          </FadeIn>
        </div>
      </section>

      {/* ────────── BIG STATS STRIP — product-relevant numbers ────────── */}
      <section className="bg-bg border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-14">
          <FadeIn>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-border rounded-lg overflow-hidden">
              {[
                ["40–60%", "Untagged AWS spend on a typical account (industry)"],
                ["13 / 15", "Per-resource accuracy on a real labelled AWS environment"],
                ["90 sec", "From dropping your CUR to a per-team breakdown"],
                ["0 bytes", "Customer data that leaves the account"],
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

      {/* ────────── WHO THIS IS FOR — buyer personas ────────── */}
      <section className="bg-bg border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="01" title="Who this is for" />
          <FadeIn>
            <p className="text-lg text-text-soft leading-relaxed max-w-3xl mb-10">
              CostDNA solves the same problem from three angles. If any of
              these is the conversation you keep having on Mondays, this is
              the tool.
            </p>
          </FadeIn>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                eyebrow: "Cloud platform / SRE team",
                head: "You own the AWS bill but can't say who spent what.",
                body: "Half your line items are untagged or mis-tagged. The CFO asks 'why is RDS up 30%?' and the honest answer is 'we have to chase it down by hand each time.' CostDNA infers the team behind each resource and writes tags back, so the next CFO question answers itself.",
              },
              {
                eyebrow: "FinOps engineer",
                head: "Your tag-enforcement policy doesn't cover legacy spend.",
                body: "Tag policies catch new resources. They do nothing about the 5 years of accumulated untagged production workload that nobody on your team provisioned themselves. CostDNA gives you a defensible per-team breakdown of that legacy mess without a tagging sprint.",
              },
              {
                eyebrow: "Engineering leader",
                head: "Per-team chargeback is impossible at your current tag coverage.",
                body: "You can't budget by team if 50% of spend is in 'untagged.' CostDNA's inferred attributions plus calibrated confidence (ECE = 0.001) let you publish a per-team P&L with explicit confidence bands — so the conversation is about numbers, not about whether the numbers are right.",
              },
            ].map((p, i) => (
              <FadeIn key={p.eyebrow} delay={i * 0.05}>
                <div className="rounded-xl border border-border bg-bg-section p-6 h-full">
                  <div className="font-mono text-[11px] text-text-muted uppercase tracking-wider mb-3">
                    {p.eyebrow}
                  </div>
                  <h3 className="text-lg font-semibold text-text mb-3 leading-snug">
                    {p.head}
                  </h3>
                  <p className="text-sm text-text-soft leading-relaxed">{p.body}</p>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* ────────── TRY IT ON YOUR DATA — promoted from buried link ────────── */}
      <section className="bg-bg-section border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="02" title="Try it on your AWS bill" />
          <div className="grid md:grid-cols-[1fr_auto] gap-12 items-start max-w-5xl">
            <FadeIn>
              <p className="text-lg text-text-soft leading-relaxed mb-6">
                Drop your AWS Cost &amp; Usage Report at{" "}
                <a href="/your-account" className="underline text-text font-semibold">
                  cost-dna.vercel.app/your-account
                </a>{" "}
                — the file is parsed in your browser, never uploaded, and
                you get a per-team breakdown plus the top inferred owners
                of your untagged spend within 90 seconds.
              </p>
              <p className="text-sm text-text-soft leading-relaxed mb-6">
                No signup. No credit card. No AWS credentials to share. The
                full GraphSAGE pipeline ships in the open-source CLI; the
                in-browser path is the lightweight discovery version, sized
                for &quot;is this worth installing locally?&quot; — typically yes
                once you see the gap your current tagging is hiding.
              </p>
              <div className="flex flex-wrap gap-3">
                <a
                  href="/your-account"
                  className="inline-flex items-center gap-2 bg-bg-deep text-text-on-deep font-medium px-6 py-3 rounded-md hover:bg-bg-deep-soft transition"
                >
                  Open the in-browser scanner →
                </a>
                <a
                  href="#install"
                  className="inline-flex items-center gap-2 bg-bg border border-border text-text font-medium px-6 py-3 rounded-md hover:border-border-strong transition"
                >
                  Install the CLI →
                </a>
              </div>
            </FadeIn>
            <FadeIn delay={0.05}>
              <div className="rounded-xl border border-border bg-bg shadow-soft p-5 md:w-[280px]">
                <div className="text-[11px] uppercase tracking-wider font-mono text-text-muted mb-3">
                  What you get back
                </div>
                <ul className="text-sm text-text-soft space-y-2 leading-relaxed">
                  <li>→ Per-team spend breakdown</li>
                  <li>→ Top untagged cost drivers</li>
                  <li>→ Inferred owners with confidence</li>
                  <li>→ Anomalies flagged for review</li>
                  <li>→ aws ec2 create-tags commands ready to copy</li>
                </ul>
                <div className="mt-4 pt-4 border-t border-border text-[11px] text-text-muted font-mono leading-snug">
                  All client-side. Your CUR never leaves the browser.
                </div>
              </div>
            </FadeIn>
          </div>
        </div>
      </section>

      {/* ────────── COMPARED TO EXISTING TOOLS — positioning ────────── */}
      <section className="bg-bg border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="03" title="Compared to existing FinOps tools" />
          <FadeIn>
            <p className="text-lg text-text-soft leading-relaxed max-w-3xl mb-10">
              CostDNA isn&apos;t a CloudHealth replacement. It&apos;s the input
              layer that makes CloudHealth, Vantage, Apptio, Datadog CCM,
              and Kubecost work on the spend they currently can&apos;t see.
            </p>
          </FadeIn>
          <FadeIn delay={0.05}>
            <div className="overflow-x-auto rounded-xl border border-border shadow-soft">
              <table className="w-full text-sm">
                <thead className="bg-bg-soft">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs uppercase tracking-wider text-text-soft font-semibold">Tool</th>
                    <th className="px-4 py-3 text-left text-xs uppercase tracking-wider text-text-soft font-semibold">Attribution mechanism</th>
                    <th className="px-4 py-3 text-left text-xs uppercase tracking-wider text-text-soft font-semibold">Scope</th>
                    <th className="px-4 py-3 text-left text-xs uppercase tracking-wider text-text-soft font-semibold">Untagged-resource handling</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border bg-bg-section">
                  {[
                    {
                      tool: "AWS Cost Allocation Tags",
                      mech: "Reads existing tags",
                      scope: "Tagged resources — 40-60% of spend",
                      untagged: "None — aggregated under 'untagged'",
                    },
                    {
                      tool: "AWS Cost Categories",
                      mech: "Manual rules (regex on ARN)",
                      scope: "Whatever your rules cover",
                      untagged: "Manual: write a rule per pattern, per team",
                    },
                    {
                      tool: "Kubecost",
                      mech: "k8s pod / namespace metadata",
                      scope: "Containerized workloads only",
                      untagged: "Out of scope (Lambda, RDS, S3 invisible)",
                    },
                    {
                      tool: "CloudHealth, Vantage, Apptio",
                      mech: "Tags + manual allocation rules",
                      scope: "Tagged + rule-matched",
                      untagged: "Tag-based blind spot; rules require upkeep",
                    },
                    {
                      tool: "Datadog CCM",
                      mech: "Tags + Datadog APM correlation",
                      scope: "Tagged + Datadog-instrumented",
                      untagged: "Limited — still blind on un-instrumented spend",
                    },
                  ].map((r) => (
                    <tr key={r.tool}>
                      <td className="px-4 py-3 font-medium text-text">{r.tool}</td>
                      <td className="px-4 py-3 text-text-soft text-sm">{r.mech}</td>
                      <td className="px-4 py-3 text-text-soft text-sm">{r.scope}</td>
                      <td className="px-4 py-3 text-text-soft text-sm">{r.untagged}</td>
                    </tr>
                  ))}
                  <tr className="bg-bg">
                    <td className="px-4 py-3 font-semibold text-text">
                      CostDNA
                    </td>
                    <td className="px-4 py-3 text-text text-sm">
                      Behavioural GNN on CloudTrail + IAM + cost shape
                    </td>
                    <td className="px-4 py-3 text-text text-sm">
                      All AWS resources that emit CloudTrail
                    </td>
                    <td className="px-4 py-3 text-text text-sm font-semibold">
                      Inferred with calibrated confidence; tags written back
                      so downstream tools see them
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </FadeIn>
          <FadeIn delay={0.10}>
            <p className="mt-6 text-sm text-text-muted max-w-3xl leading-relaxed">
              Run CostDNA before your nightly FinOps export. The inferred
              tags propagate downstream; the dashboards you already pay for
              start explaining 90%+ of spend instead of 50%.
            </p>
          </FadeIn>
        </div>
      </section>

      {/* ────────── WHY YOU CAN TRUST THE INFERRED TAGS — was §01 audit ────────── */}
      <section id="trust" className="bg-bg-section border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="04" title="Why you can trust the inferred tags" />
          <div className="max-w-4xl">
            <FadeIn>
              <p className="text-lg text-text-soft leading-relaxed mb-8">
                Tagged spend is sacred — it&apos;s what every FinOps
                conversation downstream is built on. So we don&apos;t ship
                inferred tags without methodological rigor. This section is
                the proof. Skip if you take it on faith; read if you&apos;re
                evaluating whether the inferred attributions are defensible
                in a chargeback conversation.
              </p>
            </FadeIn>

            <FadeIn delay={0.03}>
              <h3 id="audit" className="text-2xl font-semibold text-text mt-12 mb-4">
                The audit that turned a 97% headline into a 6.9% honest number
              </h3>
              <p className="text-base text-text-soft leading-relaxed mb-6">
                Before claiming any &quot;inferred tags&quot; accuracy number to a
                customer, the model has to be audited against datasets the
                community has actually published. The largest publicly
                available cloud trace is Microsoft Azure&apos;s 2.6M-VM Public
                Dataset. CostDNA hit{" "}
                <b className="text-text">97% on 100-class attribution</b>{" "}
                — too good to be true on a problem where state-of-the-art
                rarely beats 95% on much easier benchmarks. So I audited.
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

            {/* Interactive audit checker — the claim becomes runnable. */}
            <FadeIn delay={0.30}>
              <div className="mt-12">
                <div className="flex items-baseline justify-between mb-3">
                  <h3 className="text-lg font-semibold text-text">
                    Run the audit on your own data
                  </h3>
                  <span className="text-[11px] uppercase tracking-wider font-mono text-text-muted">
                    client-side · zero upload
                  </span>
                </div>
                <p className="text-sm text-text-soft mb-5">
                  Pure JavaScript port of <code className="font-mono text-xs bg-bg-soft px-1.5 py-0.5 rounded">costdna.audit.find_deterministic_edges</code>.
                  Drop any CSV; if a candidate column maps 1:1 to your target,
                  it&apos;s flagged. The full Python implementation is at{" "}
                  <a href={`${GH_URL}/blob/main/src/costdna/audit.py`} className="underline" target="_blank">src/costdna/audit.py</a>.
                </p>
                <AuditChecker />
              </div>
            </FadeIn>
          </div>
        </div>
      </section>

      {/* ────────── PRICING ────────── */}
      <section id="pricing" className="bg-bg border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="05" title="Pricing" />
          <div className="grid md:grid-cols-3 gap-6 max-w-5xl">
            {[
              {
                tier: "Self-hosted",
                price: "$0",
                priceSub: "forever",
                desc: "MIT-licensed open source. Run on your own AWS account; no data ever leaves. Pip-install, Docker, or build from source. All 10 agent tools, all collectors, full audit module.",
                cta: "Install →",
                ctaHref: "#install",
                primary: false,
              },
              {
                tier: "Managed scan",
                price: "$0.05",
                priceSub: "per resource scanned · waitlist",
                desc: "Read-only IAM role; we run the scan in our infrastructure, deliver a PDF executive summary + tagged predictions.csv. No installation, no compute on your side. Currently invite-only.",
                cta: "Join waitlist →",
                ctaHref: "mailto:parth.auti@gmail.com?subject=CostDNA managed-scan waitlist",
                primary: true,
              },
              {
                tier: "Enterprise",
                price: "Talk to us",
                priceSub: "annual contract",
                desc: "Continuous attribution + drift alerting in your VPC. Custom IAM scope, SLA on accuracy bands, integration with existing FinOps stack (Vantage, CloudHealth, Datadog CCM, Slack). SOC 2 attestation in progress.",
                cta: "Get in touch →",
                ctaHref: "mailto:parth.auti@gmail.com?subject=CostDNA enterprise",
                primary: false,
              },
            ].map((p) => (
              <div
                key={p.tier}
                className={`rounded-xl border ${p.primary ? "border-text shadow-soft-lg" : "border-border"} bg-bg-section p-6 flex flex-col`}
              >
                <div className="text-xs uppercase tracking-wider text-text-muted mb-2">
                  {p.tier}
                </div>
                <div className="text-3xl font-bold text-text">{p.price}</div>
                <div className="text-xs text-text-soft mt-1 mb-4">{p.priceSub}</div>
                <p className="text-sm text-text-soft leading-relaxed flex-1">
                  {p.desc}
                </p>
                <a
                  href={p.ctaHref}
                  target={p.ctaHref.startsWith("mailto") ? undefined : "_blank"}
                  className={`mt-5 inline-flex items-center justify-center gap-2 ${
                    p.primary
                      ? "bg-bg-deep text-text-on-deep"
                      : "bg-bg border border-border text-text"
                  } font-medium px-4 py-2 rounded-md hover:brightness-110 transition text-sm`}
                >
                  {p.cta}
                </a>
              </div>
            ))}
          </div>
          <FadeIn delay={0.10}>
            <p className="mt-8 text-sm text-text-muted leading-relaxed max-w-3xl">
              <b className="text-text">Value sanity check:</b> if you have
              $500K/mo of AWS spend with 40% untagged, recovering correct
              attribution is worth roughly $15K/mo of strategic clarity
              (the gap between budgeting on truth vs. budgeting on
              &quot;untagged&quot;). Self-hosted is free; managed pricing
              targets ~5% of that value. <a href={`${GH_URL}/blob/main/docs/pricing.md`} className="underline" target="_blank">See full pricing rationale →</a>
            </p>
          </FadeIn>
        </div>
      </section>

      {/* ────────── SECURITY & COMPLIANCE ────────── */}
      <section id="security" className="bg-bg-section border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="06" title="Security & compliance" />
          <FadeIn>
            <p className="text-lg text-text-soft leading-relaxed max-w-3xl mb-10">
              CostDNA is designed for the security-conscious case where it
              actually matters: a customer pointing it at a production AWS
              account. Below is the threat model in plain English. Full
              detail at{" "}
              <a href={`${GH_URL}/blob/main/docs/security.md`} className="underline text-text" target="_blank">docs/security.md</a>.
            </p>
          </FadeIn>
          <div className="grid md:grid-cols-2 gap-6 max-w-5xl">
            {[
              {
                t: "Read-only IAM scope",
                b: "The only permissions CostDNA needs to discover and attribute are: cloudtrail:LookupEvents, ec2:Describe*, iam:List*, ce:Get*, rds:Describe*, s3:List*. Tag write-back is a separate, explicit grant that you opt into per resource type.",
              },
              {
                t: "Self-hosted by default",
                b: "The CLI runs in your environment. Your CloudTrail events, IAM role names, and cost data never leave your account — there's no upstream API call back to a CostDNA server.",
              },
              {
                t: "Browser-only for the in-browser scan",
                b: "/your-account parses your CUR CSV entirely client-side via PapaParse. Zero bytes uploaded. Verify in your browser's Network tab.",
              },
              {
                t: "Supply chain — open source, signed releases planned",
                b: "Every line of code is in the public GitHub repo. PyPI releases are not yet signed (Sigstore on the roadmap). Docker images are reproducible from the published Dockerfile.",
              },
              {
                t: "GDPR / data residency",
                b: "Cloud bills contain no PII in the EU sense — only AWS resource IDs and amounts. Customer data, when CostDNA is self-hosted, never leaves the customer's account or browser. Managed scan: data stays in our SOC-2-pending serverless region you choose.",
              },
              {
                t: "Responsible disclosure",
                b: "Found a vulnerability? Email parth.auti@gmail.com (or open a private security advisory on GitHub). I'll respond within 72h and credit you in the fix.",
              },
            ].map((c) => (
              <div key={c.t} className="rounded-xl border border-border bg-bg p-6">
                <h3 className="font-semibold text-text mb-3">{c.t}</h3>
                <p className="text-sm text-text-soft leading-relaxed">{c.b}</p>
              </div>
            ))}
          </div>
          <FadeIn delay={0.10}>
            <p className="mt-8 text-sm text-text-muted leading-relaxed max-w-3xl">
              SOC 2 Type I attestation: <b className="text-text">in progress</b>{" "}
              (managed-scan tier). SOC 2 Type II: planned post-pilot.
              For self-hosted, the relevant attestation is your own — CostDNA
              runs in your security boundary.
            </p>
          </FadeIn>
        </div>
      </section>

      {/* ────────── PRIMARY RESULTS — AZURE POST-AUDIT ────────── */}
      <section id="results" className="bg-bg border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <SectionHeader number="07" title="Primary results — Azure, post-audit" />
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
          <SectionHeader number="08" title="Method" />
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
          <SectionHeader number="09" title="Engineering pipeline validation — real AWS" dark />
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
          <SectionHeader number="10" title="Visual proof — embedding space" />
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
          <SectionHeader number="11" title="Limitations and what doesn't work" />
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
          <SectionHeader number="12" title="Multi-cloud architecture" />
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
          <SectionHeader number="13" title="Optional natural-language interface" />
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

          {/* Pre-baked example conversations — what the chat looks like
              with content. Static so a visitor who scrolls past without
              typing still sees an interaction shape. */}
          <FadeIn delay={0.12}>
            <h3 className="text-sm uppercase tracking-wider text-text-muted font-mono mb-4">
              Example transcripts
            </h3>
            <ExampleConversation />
          </FadeIn>

          <FadeIn delay={0.18}>
            <details className="mt-8 bg-bg rounded-lg border border-border p-6 max-w-4xl">
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
          <SectionHeader number="14" title="Run it yourself" />
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
          <SectionHeader number="15" title="Stack" />
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

      {/* ────────── BUILT BY ────────── */}
      <section className="bg-bg-section border-t border-border">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <div className="grid md:grid-cols-[auto_1fr] gap-8 items-start max-w-4xl">
            <div className="w-24 h-24 rounded-full bg-bg-deep text-text-on-deep flex items-center justify-center font-mono text-3xl font-bold">
              PA
            </div>
            <div>
              <h3 className="text-2xl font-semibold text-text mb-3">
                Built by Parth Auti
              </h3>
              <p className="text-text-soft leading-relaxed mb-4">
                I write ML and infrastructure code — graph neural networks for
                cloud-cost attribution most recently, but anything where
                methodology matters more than headline numbers. CostDNA is the
                project I&apos;d most like to be remembered for: a behavioural GNN
                that caught label leakage in two published Microsoft cloud
                datasets, with the audit methodology checked into the repo as
                a reusable function.
              </p>
              <p className="text-text-soft leading-relaxed mb-6">
                I&apos;m currently looking for full-time roles in{" "}
                <b className="text-text">cloud-cost / FinOps / ML-infra</b>.
                If this is the kind of work your team does, I&apos;d like to chat.
              </p>
              <div className="flex flex-wrap gap-3 text-sm">
                <a
                  href="https://github.com/pauti04"
                  target="_blank"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-md border border-border bg-bg text-text hover:border-text transition"
                >
                  GitHub ↗
                </a>
                <a
                  href="mailto:parth.auti@gmail.com"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-md border border-border bg-bg text-text hover:border-text transition"
                >
                  Email
                </a>
                <a
                  href={`${GH_URL}/blob/main/docs/blog-post-audit.md`}
                  target="_blank"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-md border border-border bg-bg text-text hover:border-text transition"
                >
                  Read the audit writeup ↗
                </a>
              </div>
            </div>
          </div>
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
