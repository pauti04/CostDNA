# Limitations and what doesn't work

A standalone, deliberately-uncomfortable section. The README has a 6-card
summary; this is the full version, with numbers where I have them.

The structure mirrors the four most-likely critiques of CostDNA from a
sharp technical reader:

1. "Does behavioral attribution actually work?"
2. "Are the numbers reliable?"
3. "Where does the model fail?"
4. "What stops me from running this in production?"

Each section is honest about where the work stops short.

---

## 1. Behavioral attribution has a ceiling, and Azure is below it

The Azure post-audit results — GraphSAGE at **6.9% on 100-class attribution** —
are honestly modest. **The lift over feature-only baselines is small** because
the Azure trace ships only summary CPU statistics (max/avg/p95 per VM), not the
hourly time-series files (140GB total, not ingested). With CloudTrail-rich data
we'd expect the GNN's per-feature signal to be materially larger; the synthetic
env results demonstrate this regime, but we cannot validate the claim on
public real data because the published traces don't have the feature density.

**What this means in practice:**

- On a real production AWS account with full CloudTrail, the model's lift is
  likely larger than what the Azure number suggests — but how much larger is
  not currently quantified outside the controlled synthetic env. We don't have
  a real-data answer between "Azure post-audit (6.9%)" and "synthetic
  (90.5%)."
- The single biggest follow-up experiment would be running CostDNA on a real
  production AWS account with full CloudTrail enabled and at least 20+
  labeled team-resource pairs. That's the missing data point. It's listed
  as a tracked issue in the repo.

## 2. Wide error bars on small label sets

The real-AWS pilot validates engineering, not methodology. Specifically:

- **15 labels** in the Terraform-provisioned account
- **5-fold CV** means 3 samples per fold
- **±27% standard deviation** across folds because each fold's accuracy can
  only take values {0/3, 1/3, 2/3, 3/3} = {0%, 33%, 67%, 100%}
- **The 87% point estimate is real but its 95% CI is roughly 60%-100%**

Don't make production deployment decisions on this number. The synthetic-env
results (5 seeds, 5-fold) have tighter bars because label count is
controllable, but the synthetic env isn't real data.

**What this means in practice:**

- "13/15 = 87%" reads as a strong number; the honest interpretation is
  "13/15 high-confidence predictions correct out of 13, and 2 wrong predictions
  both came back below the 0.7 confidence threshold, which is the active-
  learning workflow working as designed."
- A serious production deployment would need 100+ labels before any
  k-fold accuracy claim is trustworthy.

## 3. Where the model fails

Specific failure modes, not vague disclaimers.

### By resource type

| Resource type | Where it fails | Why |
|---|---|---|
| Lambda | Bursty, short-lived, often shared across teams | Few events per resource → unstable fingerprint |
| S3 buckets | Cold-storage and rarely-accessed buckets | `peak_hour` and `weekend_ratio` features are uninformative without enough events |
| RDS | Shared databases used by multiple teams | The `shared_service` failure mode by design — behavior points to whichever team uses it most, not the owner |
| EC2 (clean) | None observed | Easy case — every model handles these |

### By organizational structure

The model **fails** on accounts that have:

- **Single IAM role for everything.** No per-team role naming → no IAM-edge signal
- **Single VPC.** No VPC-based clustering signal
- **Homogeneous calling patterns.** If every team writes to S3 at 2pm in the same way, there's no temporal signature to extract
- **Too few resources** (< ~100). The graph is too sparse for message-passing to converge meaningfully
- **Too few labels** (< ~20). The supervised learning component degrades to majority-class prediction

### By dataset

| Dataset                         | Behavioral accuracy | Note |
|---------------------------------|---------------------|------|
| Microsoft Azure (post-audit)    | 6.9% on 100 classes | Thin per-resource features (summary CPU only) |
| Microsoft Philly (post-audit)   | 11% on 15 VCs       | User-edge (0.95-deterministic) removed; still ~1.7× random |
| Real-AWS Terraform env (pilot)  | 87% on 15 labels    | Wide CI; engineering validation, not methodology |
| Synthetic env (controlled)      | 90% on 4 teams      | Ablation, by-construction the regime the model was designed for |

The pattern: **CostDNA wins when behavioral features are rich and the graph
topology is informative. Both conditions matter.** Public traces typically
have one or the other but not both.

### Adversarial cases

We can construct cases where the model fails predictably:

- **Decoy resources.** A resource that behaves like team A but has graph edges
  to team B. The GNN predicts team B (graph wins over features). This is
  arguably the correct behavior — graph structure reflects real ownership in
  most cases — but a malicious or unusual setup can exploit this.
- **Tag-only attribution.** If the input pipeline ingests resource tags as
  features (which CostDNA does optionally), and tags are intentionally wrong,
  the model will inherit the wrong labels. Mitigation: tag features are
  weighted lower than behavioral ones by default.
- **CloudTrail blind spots.** Some AWS API calls don't generate CloudTrail
  events (most data-plane S3 operations by default). Resources hit only via
  these calls show up as "idle" to CostDNA.

## 4. Why this isn't production-ready

CostDNA is a research-tone open-source project. It is **not** a deployed
production tool. The gap between current state and production readiness
includes:

| Required for production | Current state | Gap |
|---|---|---|
| Signed binaries | None | Need code-signing certificate; release pipeline change |
| Audited IAM policy with least-privilege | Documented in `docs/evaluation.md` | Not formally audited by a security review |
| Privacy review | None | Customer accounts contain sensitive operational data; need legal review |
| SLA on accuracy | None | Confidence intervals are honest but no SLA |
| User-facing error handling | Partial | Many errors are stack traces, not actionable messages |
| Documentation for non-engineers | Partial | README assumes ML / Python literacy |
| Support for tag-policy enforcement | `costdna policy` generates the Org tag policy + SCP | Generated, not yet applied to a live Organization |
| Customer-deployable installer | Docker image only | No one-click install for non-Docker shops |
| Authentication for the optional web UI | None | Streamlit serves on localhost; no auth |
| Multi-tenant deployment | None | Single-tenant by design |

**The honest framing:** I built this to demonstrate methodology and engineering
on a hard cloud-attribution problem. The pilot study validates that the
pipeline works end-to-end on real CloudTrail. Production deployment would
require ~80–150 additional hours of trust-establishment work on top of the
existing code.

## 5. Things I'd do differently if starting over

- **Lead with the audit from day one.** Spent the first ~2 months building the
  agent layer and the multi-cloud architecture before discovering the audit
  was the strongest finding. Should have audited the published datasets first
  and let the engineering build around the methodological result.
- **Validate on a real production AWS account with full CloudTrail earlier.**
  The Terraform-provisioned account is good but bounded. A real account with
  ambient organic CloudTrail traffic would have caught the "thin features"
  issue much sooner.
- **Treat the agent layer as a separate project.** The 10-tool function-
  calling agent is genuinely a different project from the GNN methodology
  work. Bundling them dilutes signal on both halves for any single reviewer.
- **Skip multi-cloud claims until at least two clouds are live-validated.**
  AWS-only is a cleaner story than "AWS + two implementations awaiting
  validation."

## 6. What would change my mind

I'm publishing the audit claim ("prior published work is measuring leakage
rather than learning") as a thesis statement, not a proven fact. Specific
findings that would update my position:

- **A reproducible cloud-attribution paper that audits its own labels and
  reports honest behavioral accuracy.** If even one published result holds up
  after the `groupby(edge)[target].nunique() == 1` check, the thesis is
  weakened.
- **A real production account where CostDNA's per-resource accuracy on
  unlabeled resources exceeds 80%.** This would demonstrate that with full
  CloudTrail features, behavioral attribution actually works at production
  thresholds.
- **A counterexample dataset** with rich behavioral features AND no
  structural-metadata leak. If such a dataset exists publicly, the thesis
  should be tested there before it generalizes.

If any reader has access to one of these, please open an issue on the repo
or DM. Genuine counterexamples make the contribution sharper, not weaker.

---

## Appendix: the audit check, as a reusable function

Drop this in any cloud-attribution project to surface tautological edges:

```python
def find_deterministic_edges(
    df: pd.DataFrame,
    target_col: str,
    candidate_edge_cols: list[str],
    threshold: float = 0.85,
) -> dict[str, float]:
    """Return edge columns that deterministically encode the target label.

    For each candidate column, compute the fraction of edge-values whose
    target distribution collapses to a single class. If that fraction is
    above `threshold`, the edge is leaking — using it as a graph signal
    will inflate model accuracy because it's effectively a join, not
    learning.
    """
    out = {}
    for col in candidate_edge_cols:
        per_edge = df.groupby(col)[target_col].nunique()
        determinism = (per_edge == 1).mean()
        if determinism >= threshold:
            out[col] = determinism
    return out
```

Run this before training any model on a cloud-attribution dataset. It costs
one function call and catches the failure mode this project documents on the
Azure trace.

## 7. The synthetic env fails its own audit — by construction

Running `find_deterministic_edges` on the synthetic metadata flags
`vpc_cidr` and `iam_role` at 1.000 determinism of team — the identical
numeric pattern we classified as a leak on the Azure trace. It is
deliberate (the env models real org structure: teams own VPCs, role names
follow team conventions), and `build_graph` uses both columns as edge
sources.

What the audit alone cannot decide is whether determinism is a *benchmark
artifact* (Azure: exclude it) or *modeled world-structure* (here: it's the
thing being simulated). By our own numeric standard, both trigger — so we
disclose rather than special-plead. Two mitigations keep the synthetic
numbers meaningful:

1. **The headline doesn't depend on the deterministic edges.** The
   edge-dropout sweep (docs/robustness.md) shows 89.4% with the graph
   entirely removed.
2. **Synthetic results are labeled ablation, not headline** — this is one
   of the reasons why.

`costdna scan` now runs this audit on its own inputs and prints a warning
when a metadata column deterministically encodes the label, so the same
blind spot can't recur silently. Pinned by
`test_synthetic_env_is_known_to_fail_its_own_audit`.
