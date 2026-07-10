# Twitter / X thread — copy-paste ready

Two threads. Pick by audience:

- **Thread A — product-first** (DevOps/FinOps Twitter, general dev
  audience). Leads with the untagged-spend pain. Audit is the
  credibility beat. **Use this for the main launch.**
- **Thread B — audit-first** (ML Twitter, researchers). Leads with the
  "I audited my own 97% and it was a tautology" arc. Further down.

Char counts under each tweet (270 max for 280-limit safety margin).

**Best time to post**: Tuesday-Thursday, 9-11am or 7-9pm EST. Reply to
your own first tweet within 5 minutes with a substantive comment to
push the thread up the timeline.

**Post-thread checklist**:
- [ ] DM the tweet URL to 5 friends asking for a like+retweet (off-Twitter
       traffic gets flagged as spam; on-platform engagement compounds).
- [ ] Cross-post tweet 1 to LinkedIn with the same image.
- [ ] Pin the thread to your profile.

---

# THREAD A — product-first (main launch)

## A1 (the hook)

**Image:** screenshot of `/your-account` per-team breakdown, or `01-hero.png`

```
40–60% of your AWS bill is on resources nobody tagged.

Your cost dashboard shows it as one giant "untagged" bucket. The CFO asks
"why is RDS up 30%?" and you chase it down by hand.

I built an open-source tool that infers the missing owners. 🧵
```

(264 chars)

## A2 (how it works)

```
CostDNA infers which team owns each untagged resource from behaviour —
who calls its API, with what IAM role, at what times, in what cost-shape
— using a graph neural network. Then it writes the tags back to AWS.

Your existing FinOps tool suddenly sees 95% of spend instead of 50%.
```

(269 chars)

## A3 (try it — the killer CTA)

**Image:** the `/your-account` drop-zone + result

```
You can see it on your own bill in 90 seconds, no signup:

Drop your Cost & Usage Report → cost-dna.vercel.app/your-account

Parsed in your browser. Nothing uploaded. You get a per-team breakdown
of the spend your tags are currently hiding.
```

(255 chars)

## A4 (it's not a dashboard replacement)

```
It's not a CloudHealth/Vantage/Kubecost replacement.

It's the input layer *upstream* of them — it attributes the untagged
resources those tools can't see, writes the tags back, and then your
dashboard works on 100% of spend instead of the tagged half.
```

(269 chars)

## A5 (the trust beat — audit as proof)

**Image:** `03-audit.png` (97% → 6.9%)

```
Why trust inferred tags in a chargeback conversation?

Because I audited the model hard. On Microsoft's published 2.6M-VM Azure
dataset I caught label leakage that had inflated my own accuracy from
6.9% to 97% — and checked the audit into the repo so you can run it too.
```

(268 chars)

## A6 (the close)

```
Open source (MIT). Self-hosted. Read-only IAM. Nothing leaves your account.

Real-AWS test: 13/15 resources correct, all 13 high-confidence right.

Try it: cost-dna.vercel.app
Code: github.com/pauti04/CostDNA

Looking for design-partner pilots 👇
```

(252 chars)

## Reply-to-self (post within 5 min)

```
The IAM scope is read-only and short — usually the first question:

cloudtrail:LookupEvents, ec2:Describe*, iam:List*, ce:Get*,
rds:Describe*, s3:List*

Tag write-back is separate, gated behind --dry-run, and only touches
resources marked managed_by=costdna. Full threat model in the repo.
```

(263 chars)

---

# THREAD B — audit-first (ML Twitter / researchers)

## Tweet 1 (the hook)

**Image:** `03-audit.png` (the 97% → 6.9% transition image)

```
I trained a behavioral GNN for cloud-resource attribution on Microsoft's
published 2.6M-VM Azure trace.

97% accuracy on a 100-class problem.

I audited my own result. It was a tautology.

A thread on what went wrong, what's honest, and what it implies for prior work 🧵
```

(266 chars)

---

## Tweet 2 (the pandas one-liner — the most-screenshotable artifact)

**Image:** screenshot of the pandas check + 1.0 output

```
The check was two lines:

  (df.groupby("deployment_id")["subscription_id"].nunique() == 1).mean()
  → 1.0

Across all 33,205 deployments in the dataset, every single one belonged to
exactly one subscription. My graph edge was a perfect lookup of the answer.
```

(269 chars)

---

## Tweet 3 (the honest number)

**Image:** the Azure post-audit baseline table (screenshot of README results section)

```
Remove the leaking edges. Re-run.

GraphSAGE on 100 classes: 6.9%.

Still ~7× random. Still beats every non-graph baseline including node2vec.

But a long way from the 97% headline. The honest negative is the project's
strongest finding.
```

(244 chars)

---

## Tweet 4 (the second dataset — generalizing the pattern)

```
I ran the same audit on Microsoft Philly's 117K-DL-job trace.

Same pattern. ~95% of users belong to exactly one virtual cluster. user_id → vc
was near-deterministic.

Two unrelated public datasets. Two different structural shortcuts. One
consistent finding.
```

(260 chars)

---

## Tweet 5 (the thesis — take a position)

```
The claim:

Prior published work in cloud-resource attribution has likely been measuring
leakage rather than learning.

Structural metadata (deployment IDs, user IDs, IAM principals) deterministically
encodes ownership in published cloud datasets. Without auditing, models exploit
this directly.
```

(269 chars)

---

## Tweet 6 (the two-line standard)

**Image:** `audit-checklist.png` (the find_deterministic_edges code block, syntax-highlighted)

```
Propose a two-line minimum standard before reporting cloud-attribution accuracy:

  for col in candidate_edges:
      determinism = (df.groupby(col)[target].nunique() == 1).mean()
      if determinism > 0.85: print(f"{col} is leaking")

One function call. Catches dataset-level label leakage.
```

(266 chars)

---

## Tweet 7 (the project — research-tone, not product hype)

**Image:** `01-hero.png` (the new audit-themed hero, or screenshot of the new landing page)

```
The repo is CostDNA — open-source, MIT.

It has the audit writeup, proper baselines (LogReg / k-NN / LabelProp /
node2vec / GraphSAGE), the synthetic env that demonstrates where graph
methods actually earn their complexity, and an explicit limitations doc.

cost-dna.vercel.app
```

(258 chars)

---

## Tweet 8 (the close — methodology takeaway + soft CTA)

```
What I'd love feedback on:

→ Public cloud datasets that have rich behavioral features AND no
  structural-metadata leak. I'd love to test there.

→ Counterexamples to the thesis.

Open source: github.com/pauti04/CostDNA

I'm looking for cloud-cost / FinOps / ML-infra roles. DMs open.
```

(264 chars)

---

## Reply-to-your-own-thread comment (post within 5 min)

This is the one substantive reply that pushes the thread up. The pandas
one-liner is the most-RT-able artifact in the whole thread.

**No image — let the code be the star:**

```
The full audit check, as a reusable function:

  def find_deterministic_edges(df, target, candidates, threshold=0.85):
      out = {}
      for col in candidates:
          det = (df.groupby(col)[target].nunique() == 1).mean()
          if det >= threshold: out[col] = det
      return out

Drop in any cloud-attribution project before reporting accuracy.
```

(268 chars)

---

## Variants if Tweet 1 doesn't land in 30 min

**Variant A — academic framing (more for ML Twitter):**
```
PSA for anyone training ML on cloud-cost / cloud-attribution data:

Two of the most-cited public cloud datasets (Microsoft Azure 2.6M VMs,
Microsoft Philly 117K jobs) have label-leakage patterns that inflate
first-cut model accuracy by 60-90 percentage points.

Here's the audit and the honest numbers 🧵
```

**Variant B — engineering framing (more for HN / dev Twitter):**
```
Suspicious of a "too good" ML result? Two-line pandas check:

  (df.groupby("possible_edge")["target"].nunique() == 1).mean()

If that returns close to 1.0, your model isn't learning — it's doing a
database join.

I caught this on a 2.6M-VM cloud dataset. Thread 🧵
```

**Variant C — hiring-direct (only if A and B both flop):**
```
Two months of evening engineering on a portfolio piece. Behavioral GNN
for cloud-resource attribution. Caught label leakage in two published
Microsoft datasets along the way. Now looking for cloud-cost / FinOps /
ML-infra roles.

Here's what's in it 🧵
```

---

## Image file inventory

| Filename | Status | Content |
|---|---|---|
| `01-hero.png` | exists from v1 | Replace with audit-themed hero or new landing screenshot for Tweet 7 |
| `02-live-chat.png` | exists | Not used in v2 thread (chat is demoted) |
| `03-audit.png` | exists | Use for Tweet 1 — the audit screenshot |
| `04-real-aws.png` | exists | Optional fallback if the baseline-table screenshot isn't generated yet |
| `05-your-account.png` | exists | Not used in v2 thread |
| `audit-checklist.png` | TODO before posting | Generate from the find_deterministic_edges code block — a Carbon.now.sh export, ~5 min |

If short on time, skip `audit-checklist.png` and post Tweet 6 image-less. The
code block in the tweet body is the artifact; an image makes it
share-friendlier but the thread still works without one.

> ⚠ **Do NOT post `walkthrough.gif` / `walkthrough.mp4`.** They were recorded
> before the "12× random" → "~7× random" correction and have the stale (wrong)
> number baked into a frame. Re-record from the live demo before using either,
> or leave them out — the thread doesn't need them.
