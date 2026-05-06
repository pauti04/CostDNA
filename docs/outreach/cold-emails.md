# 5 personalized cold-email drafts

*Send 1-2 per day this week. Find a specific human on LinkedIn before sending — "Hi {real name}" beats "Hi team" 5:1.*

**Where to find names:**
- LinkedIn → search "{Company} engineering" or "{Company} FinOps"
- For each, look for: founding engineer, head of engineering, principal/staff engineer, head of product
- For a hiring email specifically, target a recruiter or hiring manager — but lead with "I built X" not "I want a job"

**Format note:** keep every one under 150 words. Recruiters get hundreds of cold emails; the ones that get replies are short and specific.

---

## 1. Vantage

**Subject:** the inferred-tags layer Vantage is missing — open-source

Hi {name},

I've been a long-time admirer of how Vantage built tag-based attribution into a clean dashboard — the "Active Resources" view is the cleanest in the space.

I built **CostDNA** as a portfolio piece: an open-source agent that *infers* missing tags from behavioral patterns (CloudTrail, IAM, cost time-series shape) using a GraphSAGE GNN. It's the layer that runs upstream of a tool like Vantage so the 40-60% of resources that aren't tagged actually show up correctly.

The novel contribution is a self-audit that caught label leakage in two published cloud datasets, including Microsoft's 2.6M-VM Azure trace.

Live demo (chat with the agent over a synthetic 68-resource account): https://cost-dna.vercel.app  
Repo: https://github.com/pauti04/CostDNA

I'm looking for cloud-cost / FinOps roles. Would the work be relevant to Vantage's engineering team? Happy to walk through the methodology.

Thanks,  
Parth

---

## 2. Kubecost (IBM)

**Subject:** the non-k8s gap, behavioral attribution, audit story

Hi {name},

Kubecost solves k8s pod-level attribution beautifully. The gap I've been noodling on: most teams I've worked with run Lambda + RDS + S3 + plain EC2 alongside their k8s workloads, and that spend is invisible to pod-level tooling.

I built **CostDNA** to fill that gap — open-source, GraphSAGE GNN that infers ownership of *non*-k8s AWS resources from behavioral fingerprints (CloudTrail / IAM / cost-time-series shape). The output (predicted team + confidence) plugs in as input to anything that consumes tags.

There's a more interesting methodological story buried in the repo: I caught label leakage in two published cloud datasets (Microsoft Azure 2.6M VMs, Philly 117K jobs) and documented honest behavioral accuracy alongside the inflated first-cut numbers — turned a 97% headline into a careful negative result.

Demo: https://cost-dna.vercel.app · Repo: https://github.com/pauti04/CostDNA

If Kubecost is exploring complement-to-pod attribution or a public engineering blog post on dataset audits, I'd love to chat.

Thanks,  
Parth

---

## 3. ProsperOps

**Subject:** team attribution makes commitment optimization auditable

Hi {name},

ProsperOps does autonomous commitment optimization — but the value of those optimizations is only legible if you can report savings *per team*. That requires resource-to-team attribution, which falls apart on the ~50% of AWS resources that aren't tagged.

I built **CostDNA**: an open-source agent that infers ownership for the unattributed half from behavioral patterns. It's the layer that turns "ProsperOps saved you 23% on commitments" into "ProsperOps saved team-A $4.2k/mo, team-B $2.1k/mo, team-platform $0.9k/mo".

The behind-the-curtain story: I audited my own results on Microsoft's published Azure dataset and caught a 100% label-leakage bug that inflated my first-cut accuracy from 6.9% to 97%. Documented and published. The audit pattern itself is the most defensible thing in the project.

Demo: https://cost-dna.vercel.app · Repo: https://github.com/pauti04/CostDNA

I'm looking for FinOps / ML-infra roles — would the work fit anything you're building?

Thanks,  
Parth

---

## 4. nOps

**Subject:** multi-cloud attribution + a label-leakage finding you might appreciate

Hi {name},

nOps does multi-cloud cost intelligence, which means you've almost certainly run into the same label-leakage issue I did when I tested CostDNA on Microsoft's published 2.6M-VM Azure trace.

The short version: `deployment_id` (which I was using as a graph edge) maps 1:1 to subscription_id across all 33,205 deployments. So my GNN's "97% accuracy" was a graph-database join, not learning. Honest accuracy with the leak removed: 6.9% on 100 classes — still 12× random and beating every feature-only baseline, but a long way from 97%.

The same audit on Microsoft Philly's 117K-job trace surfaced an 85%-deterministic user-to-VC shortcut. Two datasets, same finding: structural metadata dominates real cloud attribution.

I think nOps's product is well-positioned to make this finding actionable. CostDNA itself is the open-source companion: behavioral fallback for resources where structural metadata fails.

Demo: https://cost-dna.vercel.app · Repo: https://github.com/pauti04/CostDNA

I'm job-hunting — happy to chat if you're exploring this kind of work.

Thanks,  
Parth

---

## 5. Datadog Cloud Cost Management

**Subject:** the input layer for CCM tag-quality

Hi {name},

Datadog CCM is excellent at slicing and dashboarding cost data — but its accuracy is a function of tag completeness, and most accounts I've seen are 40-60% untagged on real workloads.

I built **CostDNA** as an open-source upstream layer that closes that gap: a GraphSAGE GNN inferring resource ownership from CloudTrail, IAM, and cost-time-series patterns, then writing AWS tags back so CCM (or any tag-consuming tool) suddenly has full visibility.

There's also a methodological story I'm proud of: I caught two label-leakage bugs in published cloud datasets (Microsoft Azure 2.6M VMs, Philly 117K jobs) by auditing my own results before claiming them, and published the honest numbers alongside the inflated first-cut ones.

Live demo: https://cost-dna.vercel.app  
Repo: https://github.com/pauti04/CostDNA

I'm looking for cloud-cost / FinOps roles. If anything in the CCM org is hiring (or exploring tag-inference upstream), I'd love to hear about it.

Thanks,  
Parth

---

## Sending checklist

Before each send:

- [ ] Replace `{name}` with a real human's first name
- [ ] Tweak the first sentence so it references something specific to that person (recent post, talk, blog) — recruiters notice
- [ ] Make sure the URLs work (test them in an incognito tab)
- [ ] Check Anthropic / OpenAI key is funded (if they click the demo)
- [ ] Send from your personal email, not a Gmail you set up just for this

## Response handling

- **"Interesting, send a calendar link"** — send your Calendly. Have a 15-min walkthrough ready.
- **"We're not hiring right now"** — reply with one sentence: "Totally understand — would you forward to anyone in your network who is?" Networks compound.
- **No reply after 7 days** — one polite follow-up, then drop it. Don't double-follow-up.
