# Resume bullet + LinkedIn project entry

## Resume bullet

Pick the variant that fits the tone of the rest of your resume.

### Variant A — audit-first (lead with the methodological win)

> **CostDNA — open-source AWS cost-attribution agent** ([cost-dna.vercel.app](https://cost-dna.vercel.app) · [github.com/pauti04/CostDNA](https://github.com/pauti04/CostDNA))  
> Built a natural-language agent that infers AWS resource ownership from behavioral patterns using a GraphSAGE GNN + LLM-derived semantic features. Self-audited and documented label leakage in two published cloud datasets (Microsoft Azure 2.6M VMs, Microsoft Philly 117K DL jobs), publishing honest behavioral accuracy alongside inflated first-cut numbers. Stack: Python, PyTorch + PyG, sentence-transformers, OpenAI SDK, Next.js, Vercel, Terraform, Docker.

### Variant B — product-first (lead with the live demo)

> **CostDNA — open-source AWS cost-attribution agent** ([cost-dna.vercel.app](https://cost-dna.vercel.app) · [github.com/pauti04/CostDNA](https://github.com/pauti04/CostDNA))  
> Open-source agent that infers AWS resource ownership from CloudTrail / IAM / cost-time-series behavior using a GraphSAGE GNN; LLM agent layer with 10 callable tools answers natural-language cost questions. Live demo runs on GPT-4o; 14-command Python CLI; Terraform-able test environment. Documented two label-leakage findings in published cloud datasets as part of the methodology.

### Variant C — terse (one line, for resumes already crowded)

> **CostDNA** ([cost-dna.vercel.app](https://cost-dna.vercel.app)): open-source AWS cost-attribution agent. GraphSAGE GNN + LLM tool-calling layer. Audited 2 published cloud datasets for label leakage; published honest behavioral accuracy. Python / PyTorch / Next.js / Terraform.

**Recommendation: variant A.** Recruiters at FinOps companies will recognize "label leakage in Microsoft Azure trace" instantly. That's the line that survives skimming.

---

## LinkedIn project entry

LinkedIn → your profile → "Add profile section" → "Recommended" → "Add featured / Add projects".

**Title:** CostDNA — natural-language agent for AWS cost attribution

**Associated with:** (leave blank — personal project)

**Project URL:** https://cost-dna.vercel.app

**Description:**

> Open-source agent that answers natural-language questions about AWS cloud cost attribution. Live demo at cost-dna.vercel.app — chat with the agent over a synthetic AWS account, no signup.
>
> The agent has 10 callable tools (summarize_account, attribute_resource, top_spenders, find_cost_spikes, find_anomalies, etc.); GPT-4o decides which to chain based on the question. Tools query a pre-computed scan output from a behavioral GraphSAGE Graph Neural Network that infers resource ownership from CloudTrail events, IAM access patterns, VPC flow logs, and cost time-series shape.
>
> The most defensible thing in the project is methodological: I tested CostDNA on two production-scale public cloud datasets (Microsoft's 2.6M-VM Azure trace and Microsoft Philly's 117K-DL-job trace) and audited my own results. Both first-cut high-accuracy numbers turned out to be tautologies — `deployment_id` is 100% deterministic of `subscription_id` on Azure; `user_id` is 85% deterministic of `vc` on Philly. With the leaks removed, behavioral attribution is modest. The audit pattern itself is the contribution: production cloud attribution is mostly a metadata-lookup problem; behavioral fingerprinting matters specifically when metadata is missing or unreliable.
>
> Stack: Python 3.11, PyTorch + PyTorch Geometric (GraphSAGE), sentence-transformers (semantic features), OpenAI SDK (agent loop), boto3 (hardened collectors), Next.js + Tailwind (web demo), Vercel (hosting), Terraform (4-team labeled test environment), Docker + GitHub Actions (release pipeline). 14-command Python CLI.
>
> Looking for cloud-cost / FinOps / ML-infra roles. If this is the kind of work your team does, I'd love to chat.

**Skills (LinkedIn auto-suggests; pick all that apply):**
- Graph Neural Networks
- Machine Learning
- AWS
- Python
- PyTorch
- Cloud Computing
- DevOps
- Cost Optimization
- Cloud FinOps
- Data Engineering
- OpenAI API
- Next.js / React
- Terraform

---

## LinkedIn featured post (optional, but high-leverage)

Pin this to your profile via the Featured section. Treat it like a 1-paragraph elevator pitch with one strong image.

**Image:** the [docs/images/live-demo.gif](../images/live-demo.gif) — recruiters scrolling stop on motion.

**Caption (~100 words):**

> Spent the last few months building CostDNA — an open-source natural-language agent for AWS cost attribution backed by a GraphSAGE GNN.
>
> The interesting part isn't the model. While testing on Microsoft's published 2.6M-VM Azure dataset, my GNN hit 97% accuracy. I audited my own result and discovered it was a label-leakage tautology — every deployment in the dataset mapped 1:1 to its subscription. With the leak removed, honest behavioral accuracy was 6.9%. Documented the audit alongside the original number; the negative result became the project's most-defensible finding.
>
> Live demo (you can chat with it): https://cost-dna.vercel.app
>
> Looking for cloud-cost / FinOps / ML-infra roles — DMs open.

---

## Where to feature CostDNA on your LinkedIn profile

Priority order:

1. **Featured section** — pinned post (above) at top of profile
2. **About section** — add 1-2 sentences linking to CostDNA in your headline summary
3. **Projects section** — full entry above
4. **Experience section** — if you have a "Personal projects / portfolio" entry, add CostDNA there too
5. **Skills section** — add the skill list above; ask 2-3 friends to endorse

The Featured section + a strong About summary is most of the value. Recruiters scan in this order: photo → headline → About first paragraph → Featured. If they see CostDNA in Featured, half the work is done.
