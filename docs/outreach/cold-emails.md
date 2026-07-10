# Cold-email playbook

Two distinct outreach tracks. Don't confuse them — the ask is different.

- **Track 1 — FinOps vendor partnership/feedback** (Vantage, Kubecost,
  ProsperOps, nOps, Datadog CCM). CostDNA is the *input layer* upstream
  of these tools; the ask is "is this interesting to your eng team / would
  you point users at it." Audit is the credibility hook. Emails 1–5 below.
- **Track 2 — design-partner pilots** (FinOps engineers / platform leads
  at companies that would *use* CostDNA). The ask is "run it on a non-prod
  account, give me 30 min of feedback." Template at the bottom. **This is
  the higher-value track for a product launch** — one real user-report is
  worth more than any vendor reply.

*Send 1–2 per day. Find a specific human on LinkedIn before sending — "Hi {real name}" beats "Hi team" 5:1.*

**Format note:** under 150 words each. The ones that get replies are short and specific.

**Framing:** lead with the product wedge (untagged-spend attribution — the pain they have *right now*), use the audit as the credibility proof. Pure-audit framing reads as research; pure-product framing reads as another portfolio piece. Product-pain + audit-proof is the combination that converts.

---

## 1. Vantage

**Subject:** I audited Microsoft's published 2.6M-VM Azure trace — found a label-leakage pattern that might interest Vantage

Hi {name},

I've been a long-time admirer of how Vantage handles tag-based attribution — the "Active Resources" view is the cleanest in the space.

While building an open-source behavioral GNN for cloud-resource attribution, I tested on Microsoft's published 2.6M-VM Azure trace and hit 97% accuracy on a 100-class problem. The number was too good. A two-line `pandas` check revealed that across all 33,205 deployments in the dataset, `deployment_id` mapped 1:1 to `subscription_id` — my graph edge was a database join. Honest GraphSAGE accuracy with the leak removed: **6.9%**.

The product angle: it's the inferred-tags layer upstream of Vantage — it attributes the 40–60% of resources your users can't tag, then writes the tags back so they show up correctly in your "Active Resources" view. The audit is why those inferred tags are trustworthy enough to write back. MIT-licensed, self-hosted, read-only IAM: github.com/pauti04/CostDNA · cost-dna.vercel.app

Would this be interesting to your eng team — as a complement, or just as a methodology read? Happy to walk through it.

Thanks,
Parth

---

## 2. Kubecost (IBM)

**Subject:** label leakage in published cloud-attribution datasets — might be relevant to Kubecost's research

Hi {name},

Kubecost does pod-level attribution beautifully. While building an open-source behavioral GNN for the non-k8s gap (Lambda / RDS / S3 / plain EC2), I ran into something I think is structurally relevant to any cloud-attribution work.

Tested on Microsoft's published 2.6M-VM Azure trace. First-cut GraphSAGE accuracy: 97% across 100 classes. A two-line check exposed it: across all 33,205 deployments, `deployment_id` mapped 1:1 to `subscription_id`. The graph edge was a perfect lookup of the answer. With the leak removed, honest accuracy was **6.9%** (still ~7× random but a long way from 97%). Same pattern on Microsoft Philly's 117K-job trace with `user_id → vc`.

Argument: published cloud-attribution work has likely been measuring leakage rather than learning. Audit + reusable check: github.com/pauti04/CostDNA · cost-dna.vercel.app

CostDNA fills Kubecost's non-k8s gap (Lambda / RDS / S3 / plain EC2) by inferring ownership and writing tags back — it plugs in upstream of anything that consumes tags. If a complement-to-pod-attribution layer is interesting to your eng team, or you just want the methodology read, I'd love to chat.

Thanks,
Parth

---

## 3. ProsperOps

**Subject:** team attribution makes commitment optimization auditable — and a methodology finding you might appreciate

Hi {name},

ProsperOps does autonomous commitment optimization, but the value of those optimizations is only legible if you can report savings per team. That requires resource-to-team attribution, which falls apart on the ~50% of AWS resources that aren't tagged.

I built CostDNA, an open-source behavioral GNN for that gap. The behind-the-curtain story: while evaluating on Microsoft's published 2.6M-VM Azure trace I caught a 100% label-leakage bug. `deployment_id` mapped 1:1 to `subscription_id` across all 33,205 deployments — my graph was doing a database join, not learning. Documented the audit and the honest 6.9% number, plus a two-line check to catch the same pattern in other datasets.

Demo: cost-dna.vercel.app · Repo: github.com/pauti04/CostDNA · Audit writeup: in the README

The product fit: ProsperOps's commitment optimization is only legible per-team if you can attribute the untagged half of the account. CostDNA does that and writes the tags back. Would the attribution layer be useful upstream of what you're building? Happy to walk through it.

Thanks,
Parth

---

## 4. nOps

**Subject:** multi-cloud attribution + a methodology audit you might recognize

Hi {name},

nOps does multi-cloud cost intelligence, which means you've almost certainly hit the same kind of label-leakage issue I did when I tested an open-source behavioral GNN on Microsoft's published 2.6M-VM Azure trace.

The short version: `deployment_id` (which I was using as a graph edge) maps 1:1 to `subscription_id` across all 33,205 deployments in the dataset. So my GNN's "97% accuracy" was a graph-database join, not learning. Honest GraphSAGE accuracy with the leak removed: **6.9%** on 100 classes — still ~7× random and beats every non-graph baseline (including node2vec), but a long way from 97%.

Same audit on Microsoft Philly's 117K-job trace exposed a ~95%-deterministic `user_id → vc` shortcut. Two datasets, same finding: structural metadata dominates real cloud attribution.

Open-source, self-hosted, read-only: github.com/pauti04/CostDNA · cost-dna.vercel.app. CostDNA is the behavioural-fallback attribution layer for the resources where structural metadata fails — upstream of a multi-cloud intelligence product like nOps. Worth a conversation?

Thanks,
Parth

---

## 5. Datadog Cloud Cost Management

**Subject:** a methodology audit on cloud-attribution datasets — might inform CCM

Hi {name},

Datadog CCM is excellent at slicing and dashboarding cost data; its accuracy is a function of tag completeness, and most accounts I've seen are 40-60% untagged.

I built CostDNA as an open-source upstream layer: a behavioral GNN that infers ownership from CloudTrail, IAM, and cost-time-series patterns. But the actually-interesting part isn't the model — it's that while evaluating on Microsoft's published 2.6M-VM Azure trace I caught label leakage that inflated first-cut accuracy from 6.9% to 97%. `deployment_id` mapped 1:1 to `subscription_id` across all 33,205 deployments. Two-line `pandas` check catches it. Same pattern on Microsoft Philly.

I argue prior published cloud-attribution work likely measures leakage. Full audit + reusable check + honest numbers: github.com/pauti04/CostDNA. Demo: cost-dna.vercel.app.

CostDNA writes inferred tags back to AWS, so CCM would see the previously-untagged 40–60% with no change on your side. If tag-inference upstream of CCM is interesting — as a complement or an acquisition-of-idea — I'd love to hear about it.

Thanks,
Parth

---

## Sending checklist

Before each send:

- [ ] Replace `{name}` with a real human's first name (LinkedIn search "{Company} {role}")
- [ ] Tweak the first sentence so it references something specific to that person (recent post, talk, blog) — recruiters notice
- [ ] Make sure the URLs work (test them in an incognito tab)
- [ ] Check that the OpenAI key on the live demo is funded (if they click through)
- [ ] Send from your personal email, not a Gmail you set up just for this

## Response handling

- **"Interesting, send a calendar link"** — send your scheduling link. Have a 15-min walkthrough ready that opens with the live `/your-account` scan on *their* data if they'll share a redacted CUR, else the synthetic demo, then the audit as the trust proof.
- **"What does your IAM policy look like?"** — link to [`docs/security.md`](../security.md) which has the exact JSON. Read-only `cloudtrail:LookupEvents`, `ec2:Describe*`, `iam:List*`, `ce:Get*`, `rds:Describe*`, `s3:List*`. No write perms unless explicitly opted in via `costdna apply --apply`.
- **"Have you run it on a real production account?"** — honest answer: "On a Terraform-provisioned account I owned, 13/15 = 87% on 15 labels, all 13 high-confidence correct. The methodology validates on the Azure published trace. I haven't run it on a *customer* production account yet — that's exactly the design-partner pilot I'm looking for."
- **No reply after 7 days** — one polite follow-up ("did the untagged-spend angle land?"), then drop it. Don't double-follow-up.

---

## Track 2 — design-partner pilot outreach (the high-value track)

Target FinOps engineers, platform/SRE leads, and cloud-cost owners at
companies that would *use* CostDNA — not vendors. LinkedIn search
"FinOps", "Cloud cost", "Platform engineering" + a mid-size company
(big enough to have an untagged-spend problem, small enough to move
without procurement).

**The ask is feedback, not a sale.** Feedback is easy to say yes to.

**Subject:** does your AWS account have a big "untagged" bucket?

Hi {name},

Quick one — I built an open-source tool (CostDNA, MIT) that infers
ownership of untagged AWS resources from CloudTrail behaviour and writes
the tags back, so your existing cost dashboard explains the 40–60% that's
currently invisible.

I'm looking for a couple of design partners before calling it
production-ready. Would you run it on a non-prod account (read-only IAM,
self-hosted, nothing leaves your account) and tell me what breaks? 30
minutes of your time; I'll fix whatever you hit and credit you in the
field notes if you want.

You can also see results on your own bill in 90 seconds without installing
anything — drop a Cost & Usage Report at cost-dna.vercel.app/your-account
(parsed in your browser, nothing uploaded).

No sales pitch. I want the bug report.

Thanks,
Parth

**Why this converts better than the vendor emails:** you're asking for
feedback, not a job or a deal. A FinOps engineer with an untagged-spend
problem and 30 free minutes says yes to "tell me what breaks" far more
readily than to anything that smells like sales. One completed pilot →
a field note → social proof for every subsequent email and launch post.
