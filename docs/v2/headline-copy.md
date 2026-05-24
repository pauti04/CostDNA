# Headline copy — v2 (audit-first framing)

Source of truth for the project's one-liner, 30-second pitch, repo description,
landing-page hero, and thesis statement. The README, the website, the resume
entry, the LinkedIn project entry, the cold emails, and the Twitter thread all
inherit from this document.

If you change wording here, propagate everywhere.

---

## 1. Repo description (≤140 chars, GitHub limits to 350 but shorter wins)

> Behavioral GNN for cloud-resource attribution. Evaluated on Microsoft's 2.6M-VM Azure trace. Methodology audit caught label leakage in prior-art baselines.

Length: 158 chars (room to tighten further if needed).

---

## 2. One-liner (the elevator pitch — must fit in one breath)

> Behavioral GNN for cloud-resource attribution, evaluated on Microsoft's 2.6M-VM Azure trace, with a methodology audit that caught label leakage inflating prior-art baselines from 6.9% to 97%.

---

## 3. 30-second pitch (memorize verbatim)

> CostDNA is a graph neural network that attributes cloud resources to owning teams from behavioral signals — CloudTrail events, IAM access patterns, cost time-series shape — rather than tags. The interesting part isn't the model. While evaluating on Microsoft's published 2.6M-VM Azure trace I caught label leakage: across all 33,205 deployments in the dataset, deployment_id mapped 1:1 to subscription_id, so any graph method using that edge was effectively doing a database join, not learning. First-cut accuracy was 97%; with the leak removed, honest behavioral accuracy is 6.9% on 100-class attribution — still 12× random, still beats every non-graph baseline including node2vec, but a long way from 97%. The negative result is the contribution: I argue prior published work in cloud-resource ML has likely been measuring leaks rather than learning, and propose a two-line pandas audit as a minimum standard before reporting accuracy.

---

## 4. Thesis statement (the publishable claim)

This is the paragraph that goes on Twitter, in HN comments, in a future blog
post. Take a position.

> Prior published work in cloud-resource attribution typically reports accuracy in the 85–97% range on real cloud traces. Our audit suggests that across at least two published datasets — Microsoft Azure's 2.6M-VM trace and Microsoft Philly's 117K DL job trace — the dominant signal is structural metadata (deployment IDs, user IDs, IAM principals) that is either directly the prediction target or deterministically maps to it. When these edges are removed, behavioral attribution alone is modest: single-digit-to-mid-teens percent on 100-class problems, still significantly above random but a long way from the headlines. We argue that the field has been measuring leakage rather than learning, and propose a two-line audit (`df.groupby(key)[target].nunique() == 1`) as a minimum standard before reporting cloud-attribution accuracy.

---

## 5. Landing-page hero (replaces the current "Ask your AWS bill questions" headline)

Hero eyebrow: `OPEN SOURCE · METHODOLOGY AUDIT · GRAPHSAGE`

Hero headline:
> A 97% cloud-attribution accuracy result.
> Audited. It was a tautology.

Hero subhead:
> CostDNA is a behavioral GNN for cloud-resource attribution. While evaluating on Microsoft's published 2.6M-VM Azure trace I caught label leakage that inflated my own first-cut accuracy from 6.9% to 97%. The honest negative result became the project's strongest finding.

Hero CTAs:
- `Read the audit →` (anchors to section 02)
- `View on GitHub ↗`
- `Optional: chat with the agent →` (anchors to the demoted interface section)

Hero big-number callouts (replaces current 2.6M / 13-15 / +53% / 3):
- **97% → 6.9%** — first-cut vs. honest, after audit
- **12×** — lift over random on 100-class attribution
- **33,205** — deployments in Azure trace, 100% mapped 1:1 to subscriptions
- **2** — published datasets where the same pattern appeared

---

## 6. Resume bullet (replaces both current variants)

> **CostDNA — open-source behavioral GNN for cloud-resource attribution** ([cost-dna.vercel.app](https://cost-dna.vercel.app) · [github.com/pauti04/CostDNA](https://github.com/pauti04/CostDNA))
> Trained a 4-layer GraphSAGE model with supervised contrastive head on Microsoft's published 2.6M-VM Azure trace. Caught a 100%-deterministic label-leakage pattern (`deployment_id ≡ subscription_id` across all 33,205 deployments) that had been inflating first-cut accuracy from 6.9% to 97%. Reported the honest behavioral number alongside the inflated one and proposed a two-line audit as a methodology standard. Compared against node2vec / DeepWalk, feature-only LogReg, k-NN, and LabelProp baselines. Stack: Python, PyTorch + PyG, sentence-transformers, scikit-learn, statsmodels, Terraform, Docker.

---

## 7. Hard rules

1. Always say `6.9%` and `97%` together, with the audit between them.
2. Never lead with the agent layer, the live demo chat, or the 10-tool count. Those are interface; the project is the methodology.
3. Never use the phrase "natural-language agent" before the audit story is in the reader's head.
4. The synthetic env's 95% number is never on the landing page or in the README hero. It is a controlled-experiment / ablation result, mentioned only in the section about controlled comparison.
5. The 13/15 = 87% real-AWS number stays in the README but is reframed as "engineering pipeline validation," not a primary result.
6. Multi-cloud claims always include the honest caveat: "AWS+Azure evaluated; GCP collectors implemented per SDK patterns, not yet validated against a live project."

---

## 8. Forbidden phrases (these all leaked in from the old framing — kill on sight)

- "97% accuracy" without immediately following with the audit (use `97% → 6.9% honest`)
- "natural-language agent" as the project description (use "GNN with optional natural-language interface")
- "10 tools" in the headline pitch
- "live demo" as a primary CTA (it's a secondary CTA at most)
- "AI-powered" anywhere
- "Just summarize the account" as the demo seed question (use a methodology question instead)
- "Most engineers stop when they see a high accuracy number and ship it" — this is true but smug; remove
