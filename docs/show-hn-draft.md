# Show HN draft

*Edit before submitting. The title is the most important thing — HN front-page makes or breaks on the title.*

---

## Title (pick one — A is the strongest)

**A. Show HN: I built a 97% accurate cloud-cost ML model. Then I audited it. (the audit is the project)**

**B. Show HN: CostDNA — natural-language agent for AWS cost attribution (live demo)**

**C. Show HN: Catching label leakage in a 2.6M-VM cloud benchmark (and what that means for cost attribution)**

A leans into the audit story (which is the genuinely-novel contribution). B leans into the demo (more accessible to non-ML readers). C is the most academic.

## URL

https://github.com/pauti04/CostDNA

## Body

Hey HN — I built CostDNA, a natural-language agent for AWS cost attribution backed by a behavioral GraphSAGE model. Live demo: https://cost-dna.vercel.app — chat with the agent over a synthetic 68-resource account, no signup.

The interesting part isn't the agent. It's that I caught two label-leakage bugs in published cloud datasets while building this.

**The setup:** 40-60% of AWS spend is untagged. FinOps tools (CloudHealth, Vantage, Apptio) are tag-based, so they go blind on untagged resources. CostDNA's claim: infer ownership from behavioral fingerprints (CloudTrail / IAM / VPC flow logs / cost time-series shape) using a GNN, write tags back, your existing dashboard suddenly explains 90% instead of 50%.

**The audit:** I tested on Microsoft's published 2.6M-VM Azure trace and Microsoft Philly's 117K-job ML training trace. First-cut accuracy: 97% (Azure) and 89% (Philly). Both were tautologies:

- **Azure:** every `deployment_id` (used as a graph edge) maps 1:1 to a single `subscription_id` across all 33,205 deployments. The "graph" was a perfect lookup of the answer.
- **Philly:** 85% of users belong to exactly one virtual cluster. `user_id → vc` is near-deterministic.

Disable the leaking edges and honest GraphSAGE accuracy drops to 6.9% on Azure (still 12× random across 100 classes) and 14% on Philly. Documented both audits in the repo with the original numbers, the leak, and the honest result.

**The methodological finding:** production cloud attribution is mostly a *metadata-lookup* problem. Deployment IDs, IAM principals, machine assignments — these encode ownership directly. Behavioral fingerprinting matters specifically when metadata is missing or unreliable, which is the gap CostDNA's synthetic environment is designed to reproduce (and where GraphSAGE hits 95%+ on hard cases that break feature-only baselines completely).

**The product layer:** the agent has 9 callable tools (summarize_account, attribute_resource, top_spenders, find_cost_spikes, find_anomalies, etc.). The LLM decides which to chain. GPT-4o (function-calling); backend is pluggable. Tools are pure data lookups against a pre-computed scan.

Stack: Python 3.11, PyTorch + PyG, sentence-transformers (MiniLM for semantic features), boto3 (hardened collectors), Click + Rich for CLI, Next.js 14 for the web demo, Vercel for hosting, Terraform for the labeled test environment.

Looking for: feedback on the audit framing, suggestions for harder hard cases in the synthetic env, and the inevitable "why didn't you try X" replies that make it better.

Self-disclosure: I'm currently looking for cloud-cost / FinOps / ML-infra roles. If this kind of work is interesting to your team, please reach out.

---

## Comment-prep

Anticipate these questions and have answers ready:

**"Why GNN over a simpler model?"**
LogReg gets 90% overall on synthetic — but 0% on cross-team across 5 seeds, and 60% ±49% on shared-services. The graph propagation handles cross-team / shared-service / reassigned cases that feature-only methods can't separate. See the ablation table in the README.

**"What if I don't have CloudTrail data events?"**
Management events are ~free (1.5% of API call volume) and they include the IAM role + source IP that drive most of the behavioral signal. Data events (S3 object-level, Lambda invoke) cost more — CostDNA falls back gracefully to management-only.

**"How do you handle the 100% subscription label leak in production?"**
You don't — if the metadata is deterministic, just use it. CostDNA's value prop is the behavioral fallback for resources where metadata is missing or has drifted. The audit makes that scope explicit instead of papering over it with inflated numbers.

**"Live demo costs?"**
~$0.01/question on OpenAI. Rate-limited to 5 questions/IP/hour. Cap at $5/day on the OpenAI key.

**"Is the synthetic env realistic?"**
It's a Terraform-able 4-team AWS account with deliberate hard cases (shared services, cross-team resources, reassigned ownership). The feature density matches what real CloudTrail provides. It's not a substitute for production data, but it's where the methodology validates cleanly without the metadata-lookup tautologies that dominate real cloud datasets.

---

## Submission timing

- **Best windows for HN front page:** Tuesday-Thursday, 9-11am EST. Avoid weekends (lower traffic) and Mondays (post-weekend backlog).
- **Frontload engagement:** comment on your own post within 5 minutes with one substantive reply (not "thanks for reading"). Replies push posts up the new page.
- **Don't ask people to upvote.** HN auto-flags posts that get sudden traffic from off-site.
- **Have a friend or two upvote in the first 30 minutes** — getting from 1 to 5 votes fast is the hardest part. After 5, momentum carries.

---

## Other places to post

| Channel | Link/path | Notes |
|---|---|---|
| **r/MachineLearning** | self-post | Lead with the audit, not the demo |
| **r/devops** | self-post | Lead with the demo, audit is secondary |
| **r/aws** | self-post | Frame as "here's the thing your tagging strategy is missing" |
| **lobste.rs** | submit | More technical audience than HN — audit story plays well |
| **dev.to / Hashnode** | crosspost the blog | Good for SEO, slow burn |
| **Twitter/X thread** | thread the audit | One image per tweet — the per-team spend table, the leak chart, the honest accuracy table |
| **LinkedIn** | post the blog link | Mention you're job-hunting in the same post |

---

## Cold-email template (for FinOps / cloud-cost companies)

Subject: built an open-source cost-attribution agent — would it interest your team?

Hi {name},

I noticed {company} is hiring for {role}. I built CostDNA as a portfolio piece — it's a natural-language agent that infers AWS resource ownership from behavioral patterns (CloudTrail / IAM / cost time-series), backed by a GraphSAGE GNN. The novel contribution is a self-audit that caught label leakage in two published cloud datasets, including Microsoft's 2.6M-VM Azure trace.

Live demo: https://cost-dna.vercel.app
Repo: https://github.com/pauti04/CostDNA

Would the work be relevant to {team}? Happy to walk through the methodology if useful.

Thanks,
Parth

---

**Companies to target** (FinOps + cost attribution focus):

- Vantage
- Cloudability (Apptio)
- CloudHealth (VMware)
- Kubecost (now part of IBM)
- Spot.io (NetApp)
- Harness (FinOps module)
- ProsperOps
- nOps
- Yotascale
- Cast.ai
- AWS itself (Cost Explorer / Compute Optimizer teams)
- Datadog (Cloud Cost Management)
- New Relic (similar)
- Snowflake (cost intelligence)
