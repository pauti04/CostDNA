# Launch kit — channel-segmented

The single most important lesson about launching this: **the framing
that wins depends on the channel.** HN and r/MachineLearning reward the
audit (a methodology critique with a pandas one-liner is catnip there).
r/aws, r/devops, Product Hunt, and FinOps communities reward the
product (untagged-spend attribution they can try in 90 seconds).

Don't post the same copy everywhere. Pick the track per channel.

| Channel | Track | Why |
|---|---|---|
| Hacker News | **Audit-first** | HN upvotes rigour and contrarian methodology findings |
| lobste.rs | Audit-first | Same, more technical |
| r/MachineLearning | Audit-first | The label-leakage thesis is the hook |
| r/aws | **Product-first** | They have the untagged-spend pain right now |
| r/devops | Product-first | Same |
| r/FinOps | Product-first | Exactly the buyer |
| Product Hunt | Product-first | Product audience, not research |
| LinkedIn | Product-first (audit as proof) | Mixed audience; lead product, prove with audit |
| Twitter/X | Either — see THREAD.md | Thread can carry both arcs |

---

# TRACK A — Product-first (r/aws, r/devops, r/FinOps, Product Hunt, LinkedIn)

## Title

**A1. CostDNA — attribute the 40–60% of your AWS bill that's untagged (open source)** ← preferred
**A2. I built an open-source tool that infers ownership of untagged AWS resources from CloudTrail**
**A3. Show HN: CostDNA — the inferred-tags layer that makes your FinOps dashboard work on 100% of spend**

(A3 only if posting to HN as the product — but for HN, Track B usually wins.)

## URL

https://cost-dna.vercel.app  (Product Hunt / Reddit)
https://github.com/pauti04/CostDNA  (Show HN)

## Body

Every FinOps team hits the same wall: 40–60% of AWS spend is on
resources nobody tagged. Tags drift, engineers leave, resources get
created in a hurry. Your CloudHealth / Vantage / Datadog CCM dashboard
is only as good as your tags — so half your bill shows up as one giant
"untagged" bucket, and the CFO's "why is RDS up 30%?" gets answered by
hand every month.

CostDNA infers the missing ownership from behaviour — who calls the
resource's API, with what IAM role, at what times, in what cost-shape —
using a graph neural network, then writes the inferred tags back to
AWS. Your existing dashboard suddenly explains 95% of spend instead of
50%. It's not a CloudHealth replacement; it's the input layer that
makes CloudHealth work on the spend it currently can't see.

**Try it in 90 seconds, no signup:** drop your Cost & Usage Report at
https://cost-dna.vercel.app/your-account — it's parsed in your browser,
nothing uploaded, and you get a per-team breakdown of your untagged
spend. The full GraphSAGE pipeline is in the open-source CLI
(`pip install costdna`, runs read-only against your account, nothing
leaves it).

On a real labelled AWS environment it hit 13/15 = 87% per-resource
accuracy, with all 13 high-confidence predictions correct. Confidence is
calibrated post-hoc via temperature scaling, so the confidence column is
something you can actually threshold on in a chargeback conversation.

The part I'm proudest of is the honesty: while validating on Microsoft's
published 2.6M-VM Azure dataset I caught label leakage that had inflated
my own accuracy from 6.9% to 97% — and I checked the audit into the repo
as a reusable function so you can run it on your own data. That's why I
trust the inferred tags enough to write them back.

MIT licensed. Self-hosted. Read-only IAM. Security model at
https://github.com/pauti04/CostDNA/blob/main/docs/security.md

Looking for design-partner pilots: if your team owns an AWS bill with a
big untagged bucket and you'd run this on a non-prod account for 30
minutes of feedback, I'd love to talk.

## Reply-to-self comment (post within 5 min)

The IAM policy is read-only and short — that's usually the first
question:

```
cloudtrail:LookupEvents, ec2:Describe*, iam:List*, ce:Get*,
rds:Describe*, s3:List*
```

Tag write-back is a separate, explicit grant gated behind `--dry-run`
by default, and it only ever touches resources already marked
`managed_by=costdna`. Full threat model: docs/security.md.

---

# TRACK B — Audit-first (Hacker News, lobste.rs, r/MachineLearning)

## Title

**B1. Show HN: I caught label leakage in Microsoft's 2.6M-VM Azure dataset. Here's the audit.** ← preferred for HN
**B2. A two-line pandas check that turned my 97% accuracy into 6.9%**
**B3. Show HN: CostDNA — methodology audit on two published cloud-attribution datasets**

B1 leads with the specific finding + active verb. B2 leans on the
most-screenshotable artifact. B3 is the academic framing for lobste.rs.

## URL

https://github.com/pauti04/CostDNA

## Body

I built [CostDNA](https://github.com/pauti04/CostDNA), an open-source
graph neural network that infers ownership of untagged AWS resources.
While validating on Microsoft's published 2.6M-VM Azure trace I hit 97%
accuracy on a 100-class problem. That number was too good. I ran a
two-line audit:

```python
(df.groupby("deployment_id")["subscription_id"].nunique() == 1).mean()
# → 1.0
```

Across all 33,205 deployments in the dataset, every single one belonged
to exactly one subscription. The graph edge I was using was a perfect
lookup of the prediction target. With the leak removed, honest GraphSAGE
accuracy on 100 classes was **6.9%** — still ~7× random, still beats
every non-graph baseline including node2vec, but a long way from 97%.

I ran the same audit on Microsoft Philly's 117K-DL-job trace. Found
another partial leak: ~95% of users belong to exactly one virtual
cluster. With the user edge removed, GraphSAGE at 15 VCs drops from
34% to 11% (still ~1.7× random).

Two unrelated public datasets, same pattern. I argue prior published
work in cloud-resource attribution has likely been measuring leakage
rather than learning, and propose a two-line pandas check as a minimum
standard before reporting cloud-attribution accuracy:

```python
def find_deterministic_edges(df, target_col, candidate_edge_cols, threshold=0.85):
    out = {}
    for col in candidate_edge_cols:
        determinism = (df.groupby(col)[target_col].nunique() == 1).mean()
        if determinism >= threshold:
            out[col] = determinism
    return out
```

**What this means in practice:** if your cloud-attribution work uses
`deployment_id` (or `request_id`, `user_id`, `cluster_id`) as a graph
signal without running the audit, your reported accuracy is probably
inflated. Behavioural attribution on its own — without the structural
shortcuts — is much harder than the headlines suggest.

The repo is a real product (it infers untagged-resource ownership and
writes tags back so your FinOps dashboard works on 100% of spend), but
the contribution I care about is the audit. Proper baselines (LogReg,
k-NN, LabelProp, node2vec, GraphSAGE), an explicit limitations doc, and
the audit checked in as a reusable function you can run on your own data
at https://cost-dna.vercel.app/#trust

Stack: Python 3.11, PyTorch + PyG, gensim (node2vec), sentence-
transformers, scikit-learn, statsmodels, boto3, Next.js + Vercel,
Terraform.

Looking for: counterexamples — public cloud datasets that are rich in
behavioural features AND don't have the structural-metadata leak. I'd
love to test there. Genuine counterexamples make the contribution
sharper, not weaker.

## Reply-to-self comment (post within 5 min)

The full audit check as a reusable function lives at
`src/costdna/audit.py`, and there's an in-browser version at
cost-dna.vercel.app/#trust — drop a CSV, it flags any column that maps
1:1 to your target. Two lines of pandas; catches the failure mode that
inflated two published Microsoft datasets.

---

# Comment-prep — answers ready for both tracks

**"Isn't this just standard label leakage?"**
Yes. What's specific to cloud-attribution is the *form*: structural
metadata (deployment IDs, IAM principals, user IDs) sits so close to the
prediction target in cloud datasets that it's trivially easy to include
as a graph edge. The audit pattern is general; the application is the
contribution.

**"6.9% on 100 classes is bad. Why ship it?"**
6.9% is ~7× random and beats every feature-only baseline including
node2vec. The point isn't that 6.9% is good — it's that it's honest.
The 97% wasn't. On a real AWS account with full CloudTrail (not Azure's
summary-stats-only trace) the lift is materially larger; that's the
synthetic env's controlled result.

**"How is this different from Vantage / CloudHealth / Kubecost?"**
Those read tags (or k8s metadata). CostDNA *infers* tags for the 40–60%
that don't have them, then writes them back so those tools work. It's
upstream of them, not competing.

**"What's the IAM policy?"**
Read-only: `cloudtrail:LookupEvents`, `ec2:Describe*`, `iam:List*`,
`ce:Get*`, `rds:Describe*`, `s3:List*`. Write-back is separate, gated
behind `--dry-run`, scoped to `managed_by=costdna` resources.

**"Does my data leave my account?"**
Self-hosted CLI: no. In-browser CUR scan: no (client-side PapaParse).
The only network path is the optional GPT-4o natural-language interface,
which is off by default.

**"Live demo cost?"**
~$0.01/question on OpenAI, rate-limited to 5/IP/hour, $5/day cap.

---

# Submission timing

- **HN:** Tuesday–Thursday, 8–10am EST. Comment your substantive
  reply-to-self within 5 minutes. Never ask for upvotes (auto-flagged).
- **Reddit:** weekday mornings in the target sub's timezone. r/aws and
  r/devops are US-heavy; post 9–11am EST.
- **Product Hunt:** launch at 12:01am PST (PH day boundary) for a full
  24h on the leaderboard.
- **LinkedIn:** Tue–Thu, 8–10am in your network's timezone.

Don't launch everywhere the same day. Stagger: HN/lobste.rs first
(audit), then a week later Reddit/PH (product) once you have the HN
discussion to point to as social proof.
