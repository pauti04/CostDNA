# Upstream issue drafts — Microsoft dataset repos

Two copy-paste-ready GitHub issues. **Framing is everything here:** the 1:1
mapping is almost certainly a *true architectural property* (Azure deployments
live in one subscription by design), not a defect in the dataset. These
datasets were published for capacity/scheduling research, not attribution
benchmarks. So the issue is a **helpful note for downstream users doing
attribution/prediction**, phrased with respect. Filed wrong (as "your dataset
is broken") it looks naive; filed right it's a genuine contribution that the
maintainers — and other researchers — will appreciate.

**Before filing:** search the repo's existing issues for "leak" / "attribution"
so you're not duplicating. Post from your real GitHub account. Expect it to be
low-traffic; the value is the public, timestamped, named record and the small
chance a maintainer or researcher engages.

---

## 1. Azure/AzurePublicDataset

**Repo:** https://github.com/Azure/AzurePublicDataset

**Title:** Note for attribution/prediction users: `deployment_id` is 1:1 with `subscription_id` (structural, worth documenting)

**Body:**

> Thanks for maintaining this trace — it's been genuinely useful.
>
> A heads-up that may help others who use it for **resource-attribution or
> ownership-prediction** tasks (rather than the capacity-planning use it was
> published for): `deployment_id` maps 1:1 to `subscription_id` across the
> whole trace. Verified with:
>
> ```python
> (df.groupby("deployment_id")["subscription_id"].nunique() == 1).mean()
> # → 1.0   (all 33,205 deployments belong to exactly one subscription)
> ```
>
> This is presumably a true architectural property — deployments are scoped to
> a single subscription — not a data issue. But it has a sharp consequence for
> ML: if you use `deployment_id` as a graph edge or feature when predicting
> `subscription_id` (or team/owner derived from it), the "model" is doing a
> deterministic lookup, not learning. In my case a graph-attribution baseline
> scored 97% via this shortcut; with the edge removed the honest number was
> ~7%.
>
> Might be worth a one-line note in the README/schema docs for anyone using the
> trace for attribution benchmarks. I wrote up the finding and a small check
> here if useful: <link to CostDNA#the-audit and/or the leakcheck package>.
>
> Not a defect report — just trying to save the next person the surprise.
> Thanks again for publishing the data.

---

## 2. msr-fiddle/philly-traces

**Repo:** https://github.com/msr-fiddle/philly-traces

**Title:** Note for attribution/prediction users: `user_id` is ~85% deterministic of virtual cluster

**Body:**

> Thanks for releasing this trace.
>
> For anyone using it for **team/cluster attribution or ownership prediction**
> (vs. the scheduling analysis it was published for): `user_id` is ~85%
> deterministic of the virtual cluster — most users appear in exactly one VC.
>
> ```python
> (df.groupby("user_id")["vc"].nunique() == 1).mean()
> # → ~0.85
> ```
>
> That's not a defect — it reflects how people are organized — but it means a
> model using `user_id` as a signal to predict `vc` is mostly exploiting a
> near-deterministic mapping rather than learning behavioral structure. On a
> graph-attribution baseline it took accuracy from ~89% (with the user edge) to
> ~14% (without). Same pattern I found on the Azure public trace, which is what
> prompted me to check here too.
>
> Flagging in case it's useful to note for attribution-benchmark users. Writeup
> + a small reusable check: <link>.
>
> Thanks for the data.

---

## After filing

- If a maintainer or researcher replies, that exchange is **external
  validation from the source** — screenshot it, and (with permission) it's a
  quotable line for the CostDNA README / your résumé.
- Cross-link the issues from the CostDNA audit writeup once they're live.
- If both get closed as "wontfix / known," that's fine — the public record with
  your name and the reproduction still stands.
