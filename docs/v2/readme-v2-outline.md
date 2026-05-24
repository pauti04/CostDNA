# README v2 — outline + section spec

The current README leads with the chat agent and treats the audit as section 3
of 18. This is wrong for the new identity. v2 leads with the audit, demotes the
agent to a single section near the bottom, and adds explicit
limitations/methodology sections.

Execute this in Phase 1 (~12h of writing + 6h of supporting copy). Do not
implement the new node2vec baseline (Phase 2) until this restructure lands —
the new baseline table sits inside section 04 of the new README.

---

## Section order (v2)

| # | Section | Goal | Approx length |
|---|---------|------|---------------|
| 00 | Hero (logo, headline, badges, ONE big GIF) | Audit hook in 5s | 30 lines |
| 01 | The 30-second pitch | One paragraph, memorizable | 6 lines |
| 02 | The audit — what I found, with the pandas one-liner | The headline finding | 80 lines |
| 03 | Honest numbers — primary results table (Azure, post-audit) | The believable number | 60 lines |
| 04 | Baselines — including node2vec / DeepWalk | The number means something | 50 lines |
| 05 | Why GraphSAGE here — features, architecture, why it beats embedding-only | The methodological substance | 80 lines |
| 06 | Calibration, anomaly detection, active learning | The rigor signals | 60 lines |
| 07 | Controlled experiment — the synthetic environment | Ablation, not main result | 50 lines |
| 08 | Engineering validation — real AWS pipeline run | Pipeline works end-to-end | 40 lines |
| 09 | Limitations and what doesn't work | Research maturity signal | 60 lines |
| 10 | Methodology thesis — prior work measures leaks | The publishable claim | 30 lines |
| 11 | Multi-cloud architecture note | Honest scope statement | 25 lines |
| 12 | Optional natural-language interface | Demoted from sections 01+05 of v1 | 50 lines |
| 13 | Repo layout, install, quickstart, license | Standard | 80 lines |

**Total: ~700 lines.** Current README is ~510 lines. The new one is longer but the proportions are radically different — section 02–04 alone is 190 lines (the audit + results), versus 30 lines in v1.

---

## Section 00 — Hero

Replace current logo + tagline + "Ask your AWS bill questions" with:

```markdown
<p align="center">
  <img src="docs/images/logo.svg" alt="CostDNA" width="120">
</p>

<h2 align="center">A 97% cloud-attribution accuracy result. Audited. It was a tautology.</h2>

<p align="center">
  CostDNA is a behavioral GNN for cloud-resource attribution. While evaluating on Microsoft's published 2.6M-VM Azure trace I caught label leakage that inflated my own first-cut accuracy from 6.9% to 97%. The honest negative result became the project's strongest finding.
</p>

<p align="center">
  <a href="#02-the-audit">Read the audit →</a> ·
  <a href="https://cost-dna.vercel.app">Live demo</a> ·
  <a href="https://github.com/pauti04/CostDNA">GitHub</a>
</p>

<p align="center">
  <!-- badges: tests, docker, python, license, demo -->
</p>

![CostDNA — the audit screenshot, before/after numbers on Azure trace](docs/images/audit-hero.png)
```

Note: hero image becomes a **new graphic** showing the 97% → 6.9% transition,
not the live-chat GIF. The chat GIF moves to section 12.

---

## Section 01 — 30-second pitch

Copy exactly from `docs/v2/headline-copy.md` § 3. Do not paraphrase.

---

## Section 02 — The audit (THE headline section)

Spec:

1. **Setup** (2 paragraphs)
   - "I trained CostDNA on the synthetic env and hit 95% accuracy. To validate methodology on real data I picked Microsoft's published Azure Public Dataset — 2.6 million VMs across 100 subscriptions, the largest publicly available cloud trace."
   - "First-cut result: LabelProp baseline scored 97% across 5–100 teams. A 97% number on a 100-class problem (random = 1%) is suspicious. State-of-the-art results on much easier problems rarely beat 95%. So either the model is groundbreaking or something is wrong."

2. **The pandas one-liner** (code block, prominent)
   ```python
   # The check
   (df.groupby("deployment_id")["subscription_id"].nunique() == 1).mean()
   # → 1.0
   ```

3. **What it means** (1 paragraph)
   - "Across all 33,205 deployments in the dataset, every single deployment belonged to exactly one subscription. The `deployment_id` graph edge — which I was using as a structural signal — was a perfect lookup of the answer. LabelProp's 97% was a graph-database join, not learning."

4. **The fix and the honest result** (2 paragraphs)
   - "Remove the leaking edges. Re-run. GraphSAGE on 100 classes: 6.9% — still 12× random, still beats every feature-only baseline including node2vec, but a long way from 97%."
   - "Ran the same audit on Microsoft Philly's 117K-DL-job trace. Found a partial leak: 85% of users belong to exactly one virtual cluster. `user_id → vc` was near-deterministic. With user edges removed: 15% (still 2× random)."

5. **The methodological claim** (1 paragraph)
   - Pull from `docs/v2/headline-copy.md` § 4. Bold the key sentence: "we argue the field has been measuring leakage rather than learning."

6. **Audit checklist** (numbered list, the prescription)
   - Step 1: list every column that could be the prediction target
   - Step 2: for every other column / graph edge, check `groupby(edge)[target].nunique() == 1`
   - Step 3: if any are deterministic, that edge is leaking
   - Step 4: re-run with the leaking edges removed
   - Step 5: report both numbers; lead with the honest one

---

## Section 03 — Primary results table (Azure, post-audit)

This is the table that replaces the current "Azure scale honest" table.

```markdown
| N teams | Random | LogReg | k-NN | LabelProp | node2vec | GraphSAGE |
|---------|--------|--------|------|-----------|----------|-----------|
| 5       | 20%    | 31.3%  | 28.6%| 20.0%     | TBD      | 34.6%     |
| 10      | 10%    | 18.3%  | 17.3%| 10.0%     | TBD      | 22.4%     |
| 25      | 4%     | 9.2%   | 10.0%| 4.0%      | TBD      | 10.6%     |
| 100     | 1%     | 3.4%   | 3.8% | 1.0%      | TBD      | 6.9%      |
```

TBD entries get filled in during Phase 2 after node2vec implementation.

Below the table: 1 paragraph noting that GraphSAGE consistently wins but the
margins are smaller on this dataset than on synthetic. Honest explanation: the
Azure trace ships only summary CPU stats (max/avg/p95), not hourly time-series,
so the per-VM features are thinner than what real CloudTrail would provide.

---

## Section 04 — Baselines spec

Each baseline gets a 2-3 sentence description + a one-line summary of "where it
fails." Reuse from the current "Baselines and why they're not enough" table but
add node2vec/DeepWalk.

---

## Section 05 — Why GraphSAGE here

Move the current "Why behavioral fingerprints work" content here. Rename to
"Why GraphSAGE here." Add a paragraph contrasting GraphSAGE vs node2vec:
"node2vec learns embeddings from random walks but doesn't aggregate node
features, so it can't exploit the behavioral signal we computed. GraphSAGE's
message passing combines neighbor aggregation with the input features, which is
the right inductive bias for this task."

---

## Section 06 — Calibration / anomaly / active learning

Compress current sections "Active learning," "Anomaly detection," "Calibrated
confidence" into one section. Keep the ECE = 0.001 number, keep the active
learning curve, keep the anomaly examples. ~60 lines total.

---

## Section 07 — Synthetic environment (demoted)

Current "Synthetic environment" content moves here, plus the current "On
synthetic AWS data (controlled experiment)" section. Frame as: "These results
exist for controlled comparison where label leakage is impossible. The
synthetic env is hand-constructed with five difficulty levels (clean,
cross_team, reassigned, shared_service, sparse). GraphSAGE wins on the hard
levels by design — the env is built to show where graph methods are necessary.
Treat as ablation, not as a primary result."

---

## Section 08 — Real AWS engineering validation

Reframe current "Real AWS deployment" section. Headline changes from "Real AWS
deployment — labeled Terraform env, 3-day window" to "Engineering pipeline
validation on real AWS."

Body change: emphasize that this validates the collectors and the end-to-end
pipeline run, not the model. Keep the 13/15 = 87% number but note that the
small label set means ±27% k-fold variance. Honest interpretation.

---

## Section 09 — Limitations (NEW, written in Phase 3)

Stub for now. Real content lands in Phase 3 (`docs/limitations.md`). Section
in README is a 60-line summary that links out.

---

## Section 10 — Methodology thesis (NEW)

Use `docs/v2/headline-copy.md` § 4 verbatim. 30 lines including 2 paragraphs of
context.

---

## Section 11 — Multi-cloud architecture (demoted)

Compress the current multi-cloud section. New length: 25 lines.
The honest scope statement is in bold: "AWS production-tested; Azure evaluated
on Microsoft's published dataset; GCP collectors implemented per SDK patterns,
not yet validated against a live project."

---

## Section 12 — Optional natural-language interface (DEMOTED from headline)

This is where the agent goes. New section text:

> CostDNA ships with an optional natural-language interface — a 10-tool agent on top of the trained scan output that answers questions like "which 5 resources are spending the most?" and "why did the bill spike Tuesday?". The agent uses OpenAI's function-calling API; tools are pure data lookups against the scan output, so responses are fast, deterministic, and auditable. This is an interface convenience, not the core contribution.
>
> Live demo at [cost-dna.vercel.app](https://cost-dna.vercel.app). Self-host with `costdna serve`.

Includes:
- Brief mention of the 10 tools (one-line each, not a table)
- The chat GIF (moved here from hero)
- One screenshot of the live-demo response

Total length: ~50 lines. (Was ~150 lines split across sections 01+05 in v1.)

---

## Section 13 — Quickstart / install / repo layout

Mostly the same as current README's quickstart + repo layout. Move install
commands above the directory layout (people install before reading layout).

---

## Acceptance criteria for Phase 1

The new README ships when:

- [ ] A FinOps recruiter reading the first screen (sections 00 + 01 + 02 first
      paragraph) sees the audit story, not the chat box.
- [ ] The word "audit" appears in the README within the first 200 chars.
- [ ] The word "Claude" does not appear anywhere (already done, verify).
- [ ] The phrase "natural-language agent" does not appear before section 12.
- [ ] The synthetic 95% number does not appear in sections 00–06.
- [ ] The new Azure-post-audit baseline table is in section 03 with node2vec
      column populated.
- [ ] `docs/v2/headline-copy.md` rules are satisfied throughout.
- [ ] Landing page (`web/src/app/page.tsx`) is restructured to match.
- [ ] Live demo continues to work end-to-end (smoke test the agent endpoint).
