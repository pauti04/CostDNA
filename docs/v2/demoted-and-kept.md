# What gets demoted, what gets kept, what gets deleted

The new identity is "behavioral GNN + methodology audit." Everything in the
repo gets sorted into one of three buckets relative to that identity.

---

## KEPT — promoted to headline

| Thing | Old role | New role |
|---|---|---|
| Azure audit story | Section 03 of 18 | Section 02, the headline |
| Pandas one-liner check | Buried in README | Section 02 hero code block |
| Honest Azure baseline table | "Azure scale honest" section, mid-README | Section 03, primary results |
| Calibration / ECE | "Calibrated confidence" sub-section | Section 06, methodological rigor |
| Active learning | Sub-section | Section 06 |
| Anomaly detection | Sub-section | Section 06 |
| Synthetic env (4 teams × 5 kinds) | Headline result section | Section 07, demoted to ablation |
| Real-AWS 13/15 | "Real AWS deployment" headline section | Section 08, reframed as engineering validation |

## KEPT — but demoted from headline

| Thing | Old role | New role |
|---|---|---|
| 10-tool agent | Sections 01 + 05 of landing page, headline of README | Section 12 "Optional interface", brief |
| Live chat box | Hero CTA, first interactive thing | Secondary CTA, in section 12 |
| Live demo GIF | Hero image | Section 12 |
| Streaming responses (NDJSON) | "Update" headline feature | Footnote in section 12, possibly removed |
| `/your-account` drop-CSV path | Hero CTA "Run on your AWS bill" | Single paragraph in section 12 or 13 |
| Multi-cloud collectors (Azure, GCP) | "Multi-cloud architecture" headline section | Section 11, honest caveats first |
| 1-day real-AWS sandbox | Mid-README sub-section | Footnote in section 08 |
| Cost-spike Granger explanation | Sub-section | Section 06 sub-section |
| Drift detection (`costdna watch`) | Sub-section | Brief mention in section 13 |

## DELETED — does not survive the cut

| Thing | Reason |
|---|---|
| "Ask your AWS bill questions. In English." landing hero | Replaced with audit hero |
| "OPEN SOURCE · LLM AGENT OVER GRAPHSAGE" eyebrow | Replaced with "METHODOLOGY AUDIT" |
| Big-number callouts (2.6M, 13/15, +53%, 3 clouds) on hero | Replaced with audit numbers (97%→6.9%, ~7×, 33205, 2 datasets) |
| Tool comparison table ("CostDNA vs CloudHealth/Kubecost/etc") | Positioning fluff, not a real comparison; removed pending real benchmark |
| "Most engineers stop when they see a high accuracy number and ship it" | Smug; remove |
| Marketing language ("ready", "forkable", "ship") | Replaced with neutral research-tone copy |
| Twitter card / OG meta proclaiming agent | Replaced with audit hook |

## NEW — added in Phases 2–4

| Thing | Phase | Status |
|---|---|---|
| `Node2VecBaseline` class in baselines.py | 2 | Not started |
| Node2vec column in primary results table | 2 | Not started |
| `docs/limitations.md` (brutal, specific, numbered) | 3 | Not started |
| Adversarial synthetic case (decoy resources) | 3 | Not started |
| Methodology thesis paragraph in README | 1 (uses copy from headline-copy.md § 4) | Drafted |
| `docs/field-notes/` directory + external feedback | 4 | Not started |
| New hero graphic (audit before/after) | 1 | Not started |
| Reproducibility script (`make reproduce-azure`) | 5 (optional polish) | Not started |
| Calibration sweep across class counts | 5 | Not started |

---

## Hard rule

When in doubt: if a sentence in the README does not directly support the
methodology-audit identity, it belongs in a sub-page (`docs/agent.md`,
`docs/multi-cloud.md`) rather than the main README. The main README must be
readable in 5 minutes and must hand the reader the audit story before they
hit section 5.
