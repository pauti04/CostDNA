# Resume bullet + LinkedIn project entry — audit-first

## Resume bullet

Pick the variant that fits the tone of the rest of your resume.

### Variant A — audit-first (recommended — lead with the methodological finding)

> **CostDNA — open-source behavioral GNN for cloud-resource attribution** ([cost-dna.vercel.app](https://cost-dna.vercel.app) · [github.com/pauti04/CostDNA](https://github.com/pauti04/CostDNA))
> Trained a GraphSAGE classifier on Microsoft's published 2.6M-VM Azure trace. Caught a 100%-deterministic label-leakage pattern (`deployment_id ≡ subscription_id` across all 33,205 deployments) that had been inflating first-cut accuracy from 6.9% to 97%. Reported the honest behavioral number alongside the inflated one and proposed a two-line `pandas` audit as a methodology standard. Confirmed the same pattern in Microsoft Philly's 117K-job trace. Compared against node2vec / DeepWalk, feature-only LogReg, k-NN, and LabelProp baselines; documented limitations and adversarial failure modes. Stack: Python, PyTorch + PyG, gensim, sentence-transformers, scikit-learn, statsmodels, Terraform, Docker.

### Variant B — engineering-first (lead with the deliverable, audit as the bullet)

> **CostDNA — open-source GraphSAGE GNN for cloud-resource attribution** ([cost-dna.vercel.app](https://cost-dna.vercel.app) · [github.com/pauti04/CostDNA](https://github.com/pauti04/CostDNA))
> Behavioral attribution model + 10-tool function-calling agent layer. Hardened multi-cloud collectors (AWS production-tested at 13/15 = 87% on a Terraform-provisioned environment; Azure methodology-evaluated on a 2.6M-VM published trace; GCP implemented per SDK patterns). Caught and documented label leakage in two published cloud datasets as part of the evaluation. Stack: Python 3.11, PyTorch + PyG, gensim (node2vec), sentence-transformers, OpenAI SDK, Next.js, Vercel, Terraform, Docker.

### Variant C — terse (one line, for resumes already crowded)

> **CostDNA** ([cost-dna.vercel.app](https://cost-dna.vercel.app)): open-source behavioral GNN for cloud-resource attribution. Caught label leakage in 2 published Microsoft cloud datasets; published honest behavioral baselines including node2vec. Python / PyTorch / PyG / Terraform.

**Recommendation: Variant A.** Recruiters at FinOps companies will recognize "label leakage in Microsoft Azure trace" instantly. That's the line that survives skimming. Variant B is the right fallback if the target role is more engineering-than-research.

---

## LinkedIn project entry

LinkedIn → your profile → "Add profile section" → "Recommended" → "Add featured / Add projects".

**Title:** CostDNA — methodology audit on published cloud-attribution datasets

**Associated with:** (leave blank — personal project)

**Project URL:** https://cost-dna.vercel.app

**Description:**

> Open-source behavioral graph neural network for cloud-resource attribution. Live demo at cost-dna.vercel.app.
>
> The technical contribution isn't the model — it's a methodology audit. While evaluating on Microsoft's published 2.6M-VM Azure trace, I caught a 100%-deterministic label-leakage pattern: across all 33,205 deployments in the dataset, `deployment_id` mapped 1:1 to `subscription_id`, so any graph method using that edge was doing a database join rather than learning. First-cut accuracy: 97%. With the leak removed, honest GraphSAGE accuracy on 100-class attribution: 6.9% — still ~7× random, still beats every non-graph baseline including node2vec, but a long way from 97%.
>
> Confirmed the same pattern on Microsoft Philly's 117K-DL-job trace (`user_id → vc` is 85% deterministic). Two unrelated published datasets, same finding. The project argues that prior published work in cloud-resource attribution has likely been measuring leakage rather than learning, and proposes a two-line `pandas` audit as a minimum methodology standard before reporting accuracy.
>
> Includes proper baselines (LogReg, k-NN, LabelProp, node2vec+LR, GraphSAGE), an explicit limitations document, the Azure post-audit results table, post-hoc confidence calibration via temperature scaling (Guo et al.), and an optional natural-language interface layer (10-tool function-calling agent on GPT-4o). The agent is interface convenience; the audit is the contribution.
>
> Stack: Python 3.11, PyTorch + PyTorch Geometric (GraphSAGE), gensim (node2vec biased random walks), sentence-transformers (MiniLM semantic features), scikit-learn (baselines), statsmodels (Granger causality), boto3 (hardened collectors), Next.js + Vercel (landing page + optional serverless agent endpoint), Terraform (4-team labeled test environment), Docker + GitHub Actions (release pipeline). 14-command Python CLI.
>
> Looking for cloud-cost / FinOps / ML-infra roles. If this kind of work is the kind of work your team does, I'd love to chat.

**Skills (LinkedIn auto-suggests; pick all that apply):**
- Graph Neural Networks
- PyTorch
- PyTorch Geometric
- Machine Learning
- ML Methodology
- AWS
- Azure
- Python
- Cloud Computing
- DevOps
- Cost Optimization
- Cloud FinOps
- Data Engineering
- node2vec
- Next.js / React
- Terraform

---

## LinkedIn featured post (high-leverage — pin to profile)

Pin this to your profile via the Featured section. Treat it like a one-paragraph elevator pitch with one strong image.

**Image:** Carbon.now.sh export of the pandas one-liner. The pandas one-liner is the most-shareable image — a screenshot of the README's audit section also works.

**Caption (~120 words):**

> I trained a GraphSAGE GNN for cloud-resource attribution on Microsoft's published 2.6M-VM Azure trace and got 97% accuracy on a 100-class problem.
>
> The number was too good. I ran a two-line pandas check:
>
>   `(df.groupby("deployment_id")["subscription_id"].nunique() == 1).mean()`
>
> → 1.0. Across all 33,205 deployments, my graph edge was a perfect lookup of the prediction target. The 97% was a database join, not learning. Honest behavioral accuracy with the leak removed: 6.9% — still ~7× random but a long way from the headline.
>
> Same audit on a second Microsoft dataset (Philly 117K jobs) — same pattern. I argue prior published cloud-attribution work has likely been measuring leakage.
>
> Open-source: https://github.com/pauti04/CostDNA
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

The Featured section + a strong About summary is most of the value. Recruiters scan in this order: photo → headline → About first paragraph → Featured. If they see the pandas one-liner in Featured, half the work is done.

## Headline tweak (LinkedIn) — optional but high-leverage

**Current default:** "Software Engineer at X" or "Recent CS Grad" or similar.

**Audit-first variant:** "Open-source ML methodology · GNNs for cloud-cost attribution · catching label leakage in published cloud datasets"

The headline shows up in recruiter search results and on every comment you make. Specific > generic.

---

## About-section paragraph (LinkedIn)

Add this to the LinkedIn "About" section, near the top. ~60 words:

> I work on graph neural networks and cloud-cost attribution. Most recently I caught label leakage in two published Microsoft cloud datasets (2.6M-VM Azure trace; 117K-job Philly trace) and published the honest post-audit baselines — including a two-line pandas check to catch the same pattern elsewhere. Open-source: github.com/pauti04/CostDNA. Currently looking for cloud-cost / FinOps / ML-infra roles.
