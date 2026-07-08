# CostDNA and the AWS Well-Architected Framework

How CostDNA's design maps to the six Well-Architected pillars. This isn't a
formal WAF review — it's the design rationale stated in WAF terms, so a cloud
architect can see the tradeoffs at a glance.

## Security

- **Least privilege.** The scan role ([`deploy/`](../deploy/)) grants exactly
  18 read-only actions and nothing else. Tag write-back is a *separate*,
  opt-in grant scoped to `managed_by=costdna` resources — CostDNA can never
  modify a resource it didn't mark.
- **Confused-deputy mitigation.** Cross-account (managed-scan) assumption
  supports an `ExternalId` condition on the trust policy.
- **No data exfiltration.** Self-hosted: the scan runs in the customer's
  account and nothing is transmitted upstream. In-browser CUR analysis
  ([`/your-account`](https://cost-dna.vercel.app/your-account)) parses
  client-side; zero bytes uploaded.
- **Provenance.** Every tag CostDNA writes carries `costdna:inferred=true`, so
  an inferred tag is always distinguishable from a human-authored one.

## Cost Optimization

- **This is the product.** CostDNA attributes the 40–60% of spend that ships
  untagged, so per-team chargeback works on the whole bill instead of half.
- **Cheap to run.** Read-only scans use CloudTrail `LookupEvents` + Cost
  Explorer queries; the real-AWS validation ran at **$0 incremental spend**
  (Free Tier + credits). Inference is offline — no per-prediction API cost.
- **Confidence-gated writes.** Tags are only written above the confidence
  threshold, so low-confidence guesses don't create cleanup cost downstream.

## Operational Excellence

- **Everything as code.** The scan role deploys via CloudFormation *or*
  Terraform; the test environment is Terraform; releases ship via GitHub
  Actions + Docker. Nothing is click-ops.
- **Observability of the model itself.** `costdna diff` surfaces attribution
  drift between runs; `costdna self-eval` re-checks accuracy on a labeled set
  with Wilson-CI-gated alerts, so a real regression fires but sample noise
  doesn't. Digests post to Slack/Discord.
- **Preflight.** `costdna doctor` validates IAM permissions and region
  availability before a scan, failing early with an actionable message.

## Reliability

- **Throttle-aware collection.** The boto3 collectors use adaptive retry and
  respect CloudTrail's ~2 req/s/region limit, with pagination checkpointing so
  a large-account scan resumes rather than restarts.
- **Graceful degradation.** A robustness sweep ([`docs/robustness.md`](robustness.md))
  shows the model tolerates ~10–20% label noise and loses only ~7 points with
  the graph entirely removed — it doesn't collapse on incomplete data.
- **Cloud-agnostic core.** AWS / Azure / GCP collectors return identical-shape
  DataFrames, so a provider outage or SDK change is isolated to one collector.

## Performance Efficiency

- **Right-sized model.** GraphSAGE auto-shrinks (2 layers / hidden=8) on small
  label sets to avoid overfit, scaling up only when labels justify it.
- **Local inference.** Sentence-transformer embeddings and node2vec run
  on-device; no external inference service in the hot path.
- **Bounded scans.** Scans operate on a configurable CloudTrail window
  (`--days`) rather than the full history, trading completeness for latency
  on demand.

## Sustainability

- **No always-on compute.** CostDNA runs on demand (or on a schedule) rather
  than a standing service; the self-hosted path adds zero idle infrastructure.
- **Minimal data movement.** Client-side CUR parsing and self-hosted scans
  avoid shipping large cost/CloudTrail datasets across the network.

---

**Honest scope.** AWS is production-validated; Azure is methodology-validated
on the public dataset; GCP collectors follow SDK patterns but await a live run.
CostDNA is an open-source portfolio project, not a SOC-2-attested managed
service — see [`docs/limitations.md`](limitations.md) for what that means.
