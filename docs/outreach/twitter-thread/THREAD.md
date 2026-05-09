# Twitter / X thread — copy-paste ready

8 tweets. Image attachments noted. Char counts under each tweet (270 max
to stay under the 280 limit with safety margin).

**Best time to post**: Tuesday-Thursday, 9-11am or 7-9pm EST. Reply to
your own first tweet within 5 minutes with one substantive comment to
push the thread up the timeline.

**Post-thread checklist**:
- [ ] DM the tweet URL to 5 friends asking for a like+retweet (off-Twitter
       traffic gets flagged as spam; on-platform engagement compounds).
- [ ] Cross-post tweet 1 to LinkedIn with the same image.
- [ ] Pin the thread to your profile.

---

## Tweet 1 (the hook)

**Image:** `01-hero.png`

```
I built a 97% accurate cloud-cost ML model.

Then I audited it.

It was a tautology.

A thread on what I learned, and what CostDNA actually does today 🧵
```

(258 chars)

---

## Tweet 2 (the catch)

**Image:** `03-audit.png`

```
Tested on Microsoft's published 2.6M-VM Azure trace.

Across all 33,205 deployments — 100% mapped 1:1 to a single subscription.

The "graph edge" was a perfect lookup of the answer. My GNN's 97% wasn't learning behaviour — it was reading the answer off a database join.
```

(263 chars)

---

## Tweet 3 (the second dataset)

**No image — just numbers:**

```
Checked Microsoft Philly's 117K-job trace next.

Same pattern. 85% of users belong to exactly one virtual cluster. user_id → vc was near-deterministic.

Two datasets. Two different shortcuts. One consistent finding:

Production cloud attribution is mostly a metadata-lookup problem.
```

(269 chars)

---

## Tweet 4 (the honest number)

```
Disable the leaking edges. Run again.

GraphSAGE on Microsoft Azure (100 classes): 6.9%.

Still 12× random. Still beats every feature-only baseline. But a long way from the 97% headline.

The negative result is the actually-defensible thing in the project.
```

(254 chars)

---

## Tweet 5 (the live demo)

**Image:** `02-live-chat.png`

```
The product is the agent on top.

10 callable tools. The LLM picks which to chain based on your question. GPT-4o on the live demo.

You can chat with it over a synthetic 68-resource AWS account: cost-dna.vercel.app
```

(216 chars)

---

## Tweet 6 (real-AWS numbers)

**Image:** `04-real-aws.png`

```
Real-AWS test: 13/15 = 87% accuracy on a labeled Terraform-provisioned account.

13/13 high-confidence (≥0.79) predictions correct. The 2 wrong ones came back with confidence < 0.7 — exactly what find_anomalies is designed to surface for human review.
```

(263 chars)

---

## Tweet 7 (the drop-CSV path)

**Image:** `05-your-account.png`

```
You can run it on YOUR AWS bill, in your browser, no signup, no upload:

cost-dna.vercel.app/your-account

Drop your Cost & Usage Report → instant per-team breakdown via the same heuristic the full version uses for discovery. Everything stays local.
```

(255 chars)

---

## Tweet 8 (the close — methodology takeaway + CTA)

```
The takeaway:

If your benchmark accuracy is suspiciously high, audit the labels. If your dataset has a column that maps near-1:1 to the target, you have a leak.

Open source: github.com/pauti04/CostDNA

Built for hiring — looking for cloud-cost / FinOps / ML-infra roles.
```

(263 chars)

---

## Reply-to-your-own-thread comment (post within 5 min)

This is the one substantive reply that pushes the thread up. Don't say "thanks for reading."

```
For the curious: the audit was just one pandas line.

  (df.groupby("deployment_id")["subscription_id"].nunique() == 1).mean()
  → 1.0

If you do ML on cloud / time-series data, run this on your dataset before celebrating any 90%+ number.
```

(248 chars)

---

## Variants if Tweet 1 doesn't land in 30 min

**Variant A — methodology framing (more academic):**
```
PSA for anyone training ML on cloud-cost data:

Two of the most-cited public cloud datasets (Microsoft Azure 2.6M VMs, Philly 117K jobs) have label-leakage patterns that inflate first-cut model accuracy.

Here's the audit, the honest numbers, and what to do about it 🧵
```

**Variant B — product framing (more practical):**
```
Most of your AWS bill is "untagged" — the 40-60% of resources nobody bothered to tag.

I built CostDNA: an open-source agent that infers ownership from behaviour (CloudTrail, IAM, cost shape). Live demo, 87% on a real account.

Plus: the audit story 🧵
```

**Variant C — hiring-direct (only if A and B both flop):**
```
Two months of evening engineering on a portfolio piece. Cost-attribution agent. Live demo. Audit-caught label leakage in two published datasets. Now looking for cloud-cost / FinOps / ML-infra roles.

Here's what's in it 🧵
```
