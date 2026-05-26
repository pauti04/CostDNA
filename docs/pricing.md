# Pricing

The short version is on the landing page at
[cost-dna.vercel.app/#pricing](https://cost-dna.vercel.app/#pricing).
This document is the rationale — why each tier is priced where it
is, what's included, and the value math that makes those numbers
defensible.

---

## Self-hosted — $0, MIT-licensed, forever

| Included | Notes |
|---|---|
| Full CLI (`costdna scan`, `apply`, `diff`, `learn`, `watch`, …) | 14 subcommands, every feature |
| All collectors (AWS, Azure, GCP) | Multi-cloud out of the box |
| GraphSAGE GNN + every baseline + audit module | Reproducible benchmarks |
| Optional natural-language interface | Requires your own OpenAI API key |
| Docker image + Terraform recipes | One-command synthetic demo |
| Community support via GitHub issues | Best-effort, no SLA |

**Why $0:** open source removes the procurement-cycle objection. A
FinOps engineer at a 50-person company can `pip install costdna`
during their lunch break and have a defensible per-team breakdown
of last month's bill by EOD — without filing a vendor-evaluation
ticket. That's the wedge.

**Why no usage cap:** because there's no SaaS to meter against.
Self-hosted CostDNA runs in your environment; we have no idea how
many resources you've scanned and no incentive to find out.

---

## Managed scan — $0.05 per scanned resource · waitlist

| Included | Notes |
|---|---|
| Read-only IAM role assumed from a serverless region you choose | us-east-1, eu-west-1, ap-southeast-2 |
| Monthly scan delivered as PDF executive summary + predictions.csv | Sent to a designated email |
| Drift alerting via Slack/Discord webhook | Optional |
| Email support | 5-business-day response target |
| SOC 2 Type I attestation | In progress — required before GA |

**Why $0.05 per resource scanned:** the marginal cost of running a
scan on an account with N resources is roughly linear in N (CloudTrail
calls, feature extraction, GNN training). At $0.05/resource a typical
1000-resource account costs $50/scan — about 1/3 of what a comparable
manual attribution workshop would cost (5 hours of a $30/hr FinOps
analyst).

**Why a waitlist:** managed scan requires the SOC 2 Type I attestation
to be in flight before we accept paying customers. We are not yet
that. The waitlist is real: when SOC 2 lands, you'll get an
invitation to onboard at the price quoted here.

---

## Enterprise — Talk to us

| Included | Notes |
|---|---|
| Continuous attribution in your VPC | We run nothing; the entire pipeline runs in your environment |
| Custom IAM scope per AWS Organization | Tag write-back gated per OU |
| SLA on inferred-tag accuracy bands | 80% / 90% / 95% confidence-band guarantees |
| Integration with existing FinOps stack | Tag-import for Vantage, CloudHealth, Datadog CCM |
| Drift alerts piped to PagerDuty, Slack, or your incident channel | |
| Quarterly methodology review | Verify the audit module catches any new published-dataset leaks |
| SOC 2 Type II attestation | Post-pilot |
| Named technical point-of-contact | Direct Slack channel |

**Why no public price:** enterprise pricing is a function of (a) how
many AWS accounts are in scope, (b) what integrations you need, and
(c) whether you want continuous drift alerting. A 5-account customer
with Slack-only integration looks very different from a 50-account
customer with PagerDuty + Vantage tag-export + on-call SLA. We
publish a price as soon as we have enough customer data to publish a
defensible one.

**The honest pricing range** (so you can budget):

| Account count | Indicative annual range |
|---|---|
| 1–5 AWS accounts | $24K–$60K/yr |
| 5–25 AWS accounts | $60K–$180K/yr |
| 25–100 AWS accounts | $180K–$480K/yr |
| 100+ accounts (Enterprise+) | Custom |

These numbers are not commitments. They're the range we'd quote
today based on cost-to-deliver plus modest margin. They will harden
once we have 3+ enterprise pilots informing the pricing.

---

## Value sanity check

For an AWS-native customer with $500K/mo of spend and the
industry-typical 40% untagged share:

- **$200K/mo of spend** is currently in the "untagged" bucket on
  the CFO's monthly report.
- **Strategic value of correct attribution on that share:** roughly
  $15K/mo of decision-making clarity (the gap between "we can't
  budget the data team because we don't know what they spend"
  and "the data team's budget is $87K/mo, here's the
  trajectory").
- **CostDNA managed-scan price for a 1000-resource customer:** ~$50/mo
  for a monthly scan.

That's a 300× ratio of value-to-price — the kind of math FinOps
buyers expect from input-layer infrastructure. We're not selling
the dashboard; we're selling the input that makes their existing
dashboard work.

---

## What we don't charge for

- **Trial pilots.** First scan of any new account is free. If
  CostDNA can't surface real value in a single 30-minute walkthrough
  with you, the price stops mattering.
- **Open-source feature requests.** Anyone can open a GitHub issue;
  if it's a reasonable feature we'll consider it on the public
  roadmap. Paying customers get priority on accepted features but
  don't pay extra for them.
- **Methodology updates.** When the audit module catches a new
  published-dataset leak (the way it caught Azure's `vpc_cidr → sub`
  in real time during the v0.3 benchmark re-run), every customer at
  every tier benefits without an upgrade fee. Trust is the product.

---

## How to engage

| If you want to | Do this |
|---|---|
| Try CostDNA on your CUR in 90 seconds | [cost-dna.vercel.app/your-account](https://cost-dna.vercel.app/your-account) |
| Install the CLI on a non-prod account | [`docs/quickstart.md`](quickstart.md) (or `pip install costdna` + `costdna doctor`) |
| Join the managed-scan waitlist | Email parth.auti@gmail.com, subject `managed-scan waitlist` |
| Discuss enterprise terms | Email parth.auti@gmail.com, subject `CostDNA enterprise` |
| Find a bug | [GitHub issues](https://github.com/pauti04/CostDNA/issues) |
| Find a vulnerability | See [`SECURITY.md`](../SECURITY.md) |
