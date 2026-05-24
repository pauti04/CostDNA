# Show HN draft — audit-first version

*Edit before submitting. The title is the most important thing — HN front-page makes or breaks on the title.*

---

## Title (pick one — A and C are strongest for the new framing)

**A. Show HN: I caught label leakage in Microsoft's 2.6M-VM Azure dataset. Here's the audit. (preferred)**

**B. Show HN: A two-line pandas check that turned my 97% accuracy into 6.9%**

**C. Show HN: CostDNA — methodology audit on two published cloud-attribution datasets**

D. Show HN: Behavioral GNN for cloud-cost attribution (and the audit that made the negative result the contribution)

A is the strongest because it leads with the specific finding (Microsoft Azure 2.6M VMs, a recognized dataset) and the active verb ("caught"). B leans into the pandas one-liner which is the most-screenshotable artifact. C is the most academic; use for lobste.rs / r/MachineLearning. D is the longest but most accurate.

## URL

https://github.com/pauti04/CostDNA

## Body (audit-first)

I built [CostDNA](https://github.com/pauti04/CostDNA), an open-source graph neural network for cloud-resource attribution. While evaluating on Microsoft's published 2.6M-VM Azure trace I hit 97% accuracy on a 100-class problem. That number was too good. I ran a two-line audit:

```python
(df.groupby("deployment_id")["subscription_id"].nunique() == 1).mean()
# → 1.0
```

Across all 33,205 deployments in the dataset, every single one belonged to exactly one subscription. The graph edge I was using was a perfect lookup of the prediction target. With the leak removed, honest GraphSAGE accuracy on 100 classes was **6.9%** — still 12× random, still beats every non-graph baseline including node2vec, but a long way from 97%.

I ran the same audit on Microsoft Philly's 117K-DL-job trace. Found another partial leak: 85% of users belong to exactly one virtual cluster. With user edges removed: 15%.

Two unrelated public datasets, same pattern. I argue prior published work in cloud-resource attribution has likely been measuring leakage rather than learning, and propose a two-line pandas check as a minimum standard before reporting cloud-attribution accuracy:

```python
def find_deterministic_edges(df, target_col, candidate_edge_cols, threshold=0.85):
    out = {}
    for col in candidate_edge_cols:
        determinism = (df.groupby(col)[target_col].nunique() == 1).mean()
        if determinism >= threshold:
            out[col] = determinism
    return out
```

**What this means in practice:** if your cloud-attribution paper uses `deployment_id` (or `request_id`, or `user_id`, or `cluster_id`) as a graph signal without running the audit, your reported accuracy is probably inflated. Behavioral attribution on its own — without the structural shortcuts — is much harder than the headlines suggest. The synthetic environment in the repo demonstrates the regime where behavioral GNNs actually earn their complexity (and where they don't).

**About the project itself:** CostDNA is a research-tone open-source project documenting the audit. It includes proper baselines (LogReg, k-NN, LabelProp, node2vec+LogReg, GraphSAGE), an explicit limitations doc, and the 2.6M-VM-trace post-audit results table. There's an optional natural-language interface (10-tool agent on GPT-4o function-calling) but that's not the contribution — the audit is.

Stack: Python 3.11, PyTorch + PyG, gensim (node2vec), sentence-transformers (MiniLM), scikit-learn, statsmodels, boto3 (hardened), Next.js + Vercel (optional UI), Terraform (labeled test env).

Live demo: https://cost-dna.vercel.app
Audit writeup: https://github.com/pauti04/CostDNA#the-audit
Limitations: https://github.com/pauti04/CostDNA/blob/main/docs/limitations.md
Blog post: https://github.com/pauti04/CostDNA/blob/main/docs/blog-post-audit.md

Looking for: counterexamples (public cloud datasets that are rich in behavioral features AND don't have the structural-metadata leak — I'd love to test there), and feedback on the methodology thesis. Genuine counterexamples make the contribution sharper, not weaker.

Self-disclosure: I'm currently job-hunting for cloud-cost / FinOps / ML-infra roles. If this kind of work is interesting to your team, please reach out.

---

## Reply-to-your-own-thread comment (post within 5 minutes)

The substantive first-reply that pushes the thread up:

```
For anyone wanting to run the audit on their own dataset, the entire check is:

  (df.groupby("edge_column")["target_column"].nunique() == 1).mean()

If that returns close to 1.0, your "edge" is a tautological lookup of the
answer. I checked four edge candidates on the Azure trace — deployment_id was
1.000, the others were under 0.20. One value above 0.85 is enough to invalidate
a benchmark accuracy claim.

The full check function with a threshold is in docs/limitations.md §6.
```

---

## Comment-prep — anticipate these and have answers ready

**"Isn't this just standard label leakage?"**
Yes — label leakage is well-known. What's specific to cloud-attribution is the *form* of the leak: structural metadata (deployment IDs, IAM principals, user IDs) is so close to the prediction target in published cloud datasets that it's easy to accidentally include as a graph edge. The audit pattern is general; the application to cloud-data is the contribution.

**"6.9% on 100 classes is bad. Why publish?"**
6.9% is 12× random (random = 1%), and it beats every feature-only baseline including node2vec on the same regime. The point isn't that 6.9% is good — it's that 6.9% is honest. The 97% wasn't. Reporting the honest negative number, plus the audit methodology that caught the inflated one, is the contribution.

**"Why GNN over a simpler model?"**
On the synthetic env, GraphSAGE doesn't dominate node2vec+LR overall (both around 92%). It earns its complexity *specifically* on the two hardest kinds — cross_team and reassigned resources. Honest comparison table in docs/v2/results-phase2.md.

**"How do you handle the 100% subscription leak in production?"**
You don't — if the metadata is deterministic, just use it. CostDNA's value prop is the behavioral fallback for resources where metadata is missing or has drifted. The audit makes that scope explicit instead of papering over it with inflated numbers.

**"What if I don't have CloudTrail data events?"**
Management events are ~free (1.5% of API call volume) and they include the IAM role + source IP that drive most of the behavioral signal. Data events (S3 object-level, Lambda invoke) cost more — CostDNA falls back gracefully to management-only.

**"Is the synthetic env realistic?"**
It's a Terraform-able 4-team AWS account with deliberate hard cases (shared services, cross-team resources, reassigned ownership). The feature density matches what real CloudTrail provides. It's not a substitute for production data, but it's where the methodology validates cleanly without the metadata-lookup tautologies that dominate real cloud datasets. Honest framing: treat synthetic numbers as ablation, not headline.

**"Live demo costs?"**
~$0.01/question on OpenAI. Rate-limited to 5 questions/IP/hour. Cap at $5/day on the OpenAI key.

**"Why is multi-cloud only partially validated?"**
AWS is engineering-validated (Terraform pilot, 13/15 = 87%). Azure is methodology-validated via the published trace. GCP collectors exist but await a live run. Honest scope statement in the README and docs/limitations.md §4.

---

## Submission timing

- **Best windows for HN front page:** Tuesday-Thursday, 9-11am EST. Avoid weekends (lower traffic) and Mondays (post-weekend backlog).
- **Frontload engagement:** comment on your own post within 5 minutes with the substantive reply above (the pandas one-liner block). Replies push posts up the new page.
- **Don't ask people to upvote.** HN auto-flags posts that get sudden traffic from off-site.
- **Have a friend or two upvote in the first 30 minutes** — getting from 1 to 5 votes fast is the hardest part. After 5, momentum carries.

---

## Other places to post (in priority order)

| Channel | Best title variant | Notes |
|---|---|---|
| **lobste.rs** | A or C | Most technical audience; audit story plays best here |
| **r/MachineLearning** | B (the pandas one-liner) | Lead with the methodology, not the product |
| **dev.to / Hashnode** | A (full blog post) | Crosspost the docs/blog-post-audit.md; permanent SEO |
| **r/devops** | A | Cloud-attribution angle |
| **r/aws** | "the thing your tagging strategy is missing" | Lead with the FinOps framing |
| **Twitter/X thread** | A | Image-attached, see docs/outreach/twitter-thread/THREAD.md |
| **LinkedIn** | A as a featured post | Mention you're job-hunting in the same post |
| **Hacker Newsletter** | inbound after HN front page | If A makes the front page |
| **TLDR Newsletter / Pointer** | inbound after HN front page | Same |
