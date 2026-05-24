# 5 personalized cold-email drafts — audit-first version

*Send 1-2 per day this week. Find a specific human on LinkedIn before sending — "Hi {real name}" beats "Hi team" 5:1.*

**Where to find names:**
- LinkedIn → search "{Company} engineering" or "{Company} FinOps"
- For each, look for: founding engineer, head of engineering, principal/staff engineer, head of product
- For a hiring email specifically, target a recruiter or hiring manager — but lead with "I found X" not "I want a job"

**Format note:** keep every one under 150 words. Recruiters get hundreds of cold emails; the ones that get replies are short and specific.

**Framing pivot:** v1 of these emails led with the product ("I built an agent that infers tags"). v2 leads with the methodology finding ("I caught label leakage in a published 2.6M-VM dataset"). Methodology-first reads as research credibility; product-first reads as another portfolio piece. The audit story is the differentiator.

---

## 1. Vantage

**Subject:** I audited Microsoft's published 2.6M-VM Azure trace — found a label-leakage pattern that might interest Vantage

Hi {name},

I've been a long-time admirer of how Vantage handles tag-based attribution — the "Active Resources" view is the cleanest in the space.

While building an open-source behavioral GNN for cloud-resource attribution, I tested on Microsoft's published 2.6M-VM Azure trace and hit 97% accuracy on a 100-class problem. The number was too good. A two-line `pandas` check revealed that across all 33,205 deployments in the dataset, `deployment_id` mapped 1:1 to `subscription_id` — my graph edge was a database join. Honest GraphSAGE accuracy with the leak removed: **6.9%**.

I think the pattern generalizes: prior published work in cloud-attribution likely measures leakage. Posted the full audit + a reusable check at github.com/pauti04/CostDNA (MIT-licensed).

The methodology might be relevant to anyone evaluating attribution models. I'm currently looking for cloud-cost / FinOps roles — would the work fit anything you're hiring for?

Thanks,
Parth

---

## 2. Kubecost (IBM)

**Subject:** label leakage in published cloud-attribution datasets — might be relevant to Kubecost's research

Hi {name},

Kubecost does pod-level attribution beautifully. While building an open-source behavioral GNN for the non-k8s gap (Lambda / RDS / S3 / plain EC2), I ran into something I think is structurally relevant to any cloud-attribution work.

Tested on Microsoft's published 2.6M-VM Azure trace. First-cut GraphSAGE accuracy: 97% across 100 classes. A two-line check exposed it: across all 33,205 deployments, `deployment_id` mapped 1:1 to `subscription_id`. The graph edge was a perfect lookup of the answer. With the leak removed, honest accuracy was **6.9%** (still 12× random but a long way from 97%). Same pattern on Microsoft Philly's 117K-job trace with `user_id → vc`.

Argument: published cloud-attribution work has likely been measuring leakage rather than learning. Audit + reusable check: github.com/pauti04/CostDNA · cost-dna.vercel.app

If Kubecost or IBM Research is interested in methodology critiques of cloud-attribution datasets, I'd love to chat. I'm currently job-hunting for FinOps / ML-infra roles.

Thanks,
Parth

---

## 3. ProsperOps

**Subject:** team attribution makes commitment optimization auditable — and a methodology finding you might appreciate

Hi {name},

ProsperOps does autonomous commitment optimization, but the value of those optimizations is only legible if you can report savings per team. That requires resource-to-team attribution, which falls apart on the ~50% of AWS resources that aren't tagged.

I built CostDNA, an open-source behavioral GNN for that gap. The behind-the-curtain story: while evaluating on Microsoft's published 2.6M-VM Azure trace I caught a 100% label-leakage bug. `deployment_id` mapped 1:1 to `subscription_id` across all 33,205 deployments — my graph was doing a database join, not learning. Documented the audit and the honest 6.9% number, plus a two-line check to catch the same pattern in other datasets.

Demo: cost-dna.vercel.app · Repo: github.com/pauti04/CostDNA · Audit writeup: in the README

Looking for FinOps / ML-infra roles. Would the methodology + the behavioral attribution work fit anything you're building?

Thanks,
Parth

---

## 4. nOps

**Subject:** multi-cloud attribution + a methodology audit you might recognize

Hi {name},

nOps does multi-cloud cost intelligence, which means you've almost certainly hit the same kind of label-leakage issue I did when I tested an open-source behavioral GNN on Microsoft's published 2.6M-VM Azure trace.

The short version: `deployment_id` (which I was using as a graph edge) maps 1:1 to `subscription_id` across all 33,205 deployments in the dataset. So my GNN's "97% accuracy" was a graph-database join, not learning. Honest GraphSAGE accuracy with the leak removed: **6.9%** on 100 classes — still 12× random and beats every non-graph baseline (including node2vec), but a long way from 97%.

Same audit on Microsoft Philly's 117K-job trace exposed an 85%-deterministic `user_id → vc` shortcut. Two datasets, same finding: structural metadata dominates real cloud attribution.

Open-source repo + audit writeup: github.com/pauti04/CostDNA. I'm currently job-hunting — happy to chat if you're working in this space.

Thanks,
Parth

---

## 5. Datadog Cloud Cost Management

**Subject:** a methodology audit on cloud-attribution datasets — might inform CCM

Hi {name},

Datadog CCM is excellent at slicing and dashboarding cost data; its accuracy is a function of tag completeness, and most accounts I've seen are 40-60% untagged.

I built CostDNA as an open-source upstream layer: a behavioral GNN that infers ownership from CloudTrail, IAM, and cost-time-series patterns. But the actually-interesting part isn't the model — it's that while evaluating on Microsoft's published 2.6M-VM Azure trace I caught label leakage that inflated first-cut accuracy from 6.9% to 97%. `deployment_id` mapped 1:1 to `subscription_id` across all 33,205 deployments. Two-line `pandas` check catches it. Same pattern on Microsoft Philly.

I argue prior published cloud-attribution work likely measures leakage. Full audit + reusable check + honest numbers: github.com/pauti04/CostDNA. Demo: cost-dna.vercel.app.

I'm looking for cloud-cost / FinOps roles. If anything in the CCM org or Datadog Research is hiring (or exploring tag-inference upstream), I'd love to hear about it.

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

- **"Interesting, send a calendar link"** — send your Calendly. Have a 15-min walkthrough ready that opens with the audit (90 seconds), not the demo.
- **"We're not hiring right now"** — reply with one sentence: "Totally understand — would you forward to anyone in your network who is?" Networks compound.
- **"What does your IAM policy look like?"** — link to `docs/evaluation.md` which has the exact JSON. Read-only `cloudtrail:LookupEvents`, `ec2:Describe*`, `iam:List*`, `ce:Get*`, `rds:Describe*`, `s3:List*`. No write perms unless explicitly opted in via `costdna apply --apply`.
- **"Have you run it on a real production account?"** — honest answer: "I ran it on a Terraform-provisioned account I owned, 13/15 = 87% on 15 labels. The methodology validates on the Azure published trace. I haven't run it on a production customer account yet — that's exactly the kind of pilot I'd love to do."
- **No reply after 7 days** — one polite follow-up referencing the audit specifically ("did the methodology finding land?"), then drop it. Don't double-follow-up.

## When the audit framing might not be right

If the company is more product-focused than research-focused (e.g., the recipient is a hands-on PM, not an engineer), lead with the demo and the 87% on real AWS. Use the audit story as the second paragraph. Specifically:

- **Product-leading version of any email above:** Replace the second paragraph with: *"Live demo at cost-dna.vercel.app — chat with the agent over a 68-resource AWS account. The technical interesting bit is a methodology audit I ran while evaluating on Microsoft's 2.6M-VM Azure trace; details in the README."*

The audit is the strongest *technical* signal. The demo is the strongest *immediately-graspable* signal. Most engineers respond to the first; most non-engineers respond to the second.
