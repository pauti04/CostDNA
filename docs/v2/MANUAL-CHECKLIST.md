# 10-Minute Manual Action Checklist

Everything in the repo, the landing page, the docs, and the outreach drafts is
finalized and live. The remaining actions can't be automated for safety reasons
(per-publish approval required). Each takes 1–5 minutes. The whole list is
~30 minutes of manual work — strongly time-boxable, do it across a week.

This is the only thing standing between the current state and "the audit story
is in front of the people who can hire you."

---

## Tier 1 — do these first, this week (cumulative ~20 minutes)

### ✅ A. Update LinkedIn (5 minutes — Monday morning)

LinkedIn → Profile → Edit.

1. **Headline:** replace with the audit-first variant from `docs/outreach/resume-and-linkedin.md`:
   > Open-source ML methodology · GNNs for cloud-cost attribution · catching label leakage in published cloud datasets
2. **About section:** paste the 60-word paragraph from `docs/outreach/resume-and-linkedin.md` §"About-section paragraph"
3. **Featured section:** click "+ Add featured" → "Add a link" → paste `https://cost-dna.vercel.app` → title: "CostDNA: methodology audit on cloud-attribution datasets" → description: paste from `docs/outreach/resume-and-linkedin.md` §"LinkedIn featured post"
4. **Projects section:** add CostDNA with the full description from §"LinkedIn project entry"

Updates surface to recruiters for ~14 days. Do this before posting on the platform.

### ✅ B. Post the LinkedIn featured post (3 minutes — Monday afternoon)

Composer → New post → paste the caption from `docs/outreach/resume-and-linkedin.md` §"LinkedIn featured post". Attach an image — Carbon.now.sh of the pandas one-liner (carbon.now.sh, paste the audit code block, screenshot, save). Add tags: `#FinOps #MachineLearning #GraphNeuralNetworks #OpenSource`. Submit.

### ✅ C. Submit Show HN (5 minutes — Tuesday 8am EST)

https://news.ycombinator.com/submit

- **Title:** copy variant A from `docs/show-hn-draft.md` ("Show HN: I caught label leakage in Microsoft's 2.6M-VM Azure dataset. Here's the audit.")
- **URL:** https://github.com/pauti04/CostDNA
- **Text:** leave blank — body goes in a comment instead
- Submit. **Then within 5 minutes**, post the body from `docs/show-hn-draft.md` §"Body (audit-first)" as a comment on your own submission. This gets the substantive content under the post while keeping the title-and-URL submission clean.
- **Then within 10 minutes**, post the reply-to-self comment from `docs/show-hn-draft.md` §"Reply-to-your-own-thread comment" — the pandas one-liner reusable function. This is the most-screenshotable artifact.

Do not ask anyone to upvote. Do not share the link in any group chat. HN auto-flags off-site traffic.

### ✅ D. Send 1 cold email per day this week (5 minutes/day)

`docs/outreach/cold-emails.md` has 5 drafts. Order: Vantage, Kubecost, ProsperOps, nOps, Datadog. **One per day, Tuesday–Saturday.**

For each:
1. Open LinkedIn, search `{Company} engineering` or `{Company} FinOps`
2. Find a real human — founding engineer, principal/staff engineer, head of product. **Not the recruiter.** ("I built X" lands better with engineers; recruiters relay it after.)
3. Find their email. Some tools: hunter.io free tier, RocketReach trial, or `firstname.lastname@company.com` heuristic.
4. Copy the relevant draft from the doc; replace `{name}`; tweak the first sentence to reference something specific about them (recent talk, blog post, conference) — recruiters notice.
5. Send from your personal email. Subject line is in the draft.

---

## Tier 2 — do these this week or next (cumulative ~10 minutes)

### ✅ E. Publish the blog post (5 minutes)

`docs/blog-post-audit.md` is ready.

Best venues, in order of payoff:
1. **dev.to** — free, ranks well on Google, has a developer audience. Sign up; "Create new post"; paste the markdown; tags: `#machinelearning #python #finops #aws`. Permanent URL.
2. **Medium** — same content, separate audience. Crosspost via the "Import a story" feature using the dev.to URL (so the canonical link points back to dev.to, no SEO penalty).
3. **Hashnode** — same, third audience.
4. **Your personal site if you have one** — the canonical version should live there.

After publishing on dev.to, add the URL as a comment on the Show HN submission.

### ✅ F. Post the Twitter thread (3 minutes — Tuesday 9–11am or 7–9pm EST)

`docs/outreach/twitter-thread/THREAD.md` has the full thread.

1. Open Twitter/X; post Tweet 1 (with `03-audit.png` attached).
2. Reply to it with Tweet 2 (image: screenshot of `pandas` one-liner — use Carbon.now.sh again).
3. Continue 3 → 8.
4. **Within 5 minutes**, post the reply-to-self comment from the same doc.
5. Pin the first tweet to your profile.
6. DM the thread URL to 5 friends and ask for a like + RT. On-platform engagement compounds; off-platform traffic gets flagged as spam.

### ✅ G. DM 10 FinOps engineers asking for feedback (~5 minutes per DM, spread over a week)

LinkedIn search for FinOps engineers at smaller companies (not your cold-email list — avoid double-targeting). Template at the bottom of `docs/field-notes/README.md`:

> Hi {name}, I built an open-source behavioral GNN for cloud-resource attribution and caught label leakage in two published Microsoft datasets. Would you run the CLI on a non-prod AWS account (or synthetic data — no AWS account needed) and tell me what breaks? 15 minutes of your time, I'll add your notes to the field-notes/ directory if you want.

You only need 1–2 replies for this to be worth it. Even one "I ran it, here's what broke" report → quote in the README → categorically stronger credibility.

---

## Tier 3 — optional polish (5–10 minutes, only if you have time)

### ✅ H. Generate the audit-checklist image for the Twitter thread (5 minutes)

`docs/outreach/twitter-thread/THREAD.md` Tweet 6 references `audit-checklist.png` which doesn't exist yet. Generate it:

1. Go to https://carbon.now.sh
2. Paste the `find_deterministic_edges` function from `docs/limitations.md` §Appendix
3. Pick a theme — "Nord" or "One Dark Pro" both work
4. Export → PNG (4x resolution)
5. Save to `docs/outreach/twitter-thread/audit-checklist.png`

If short on time, skip this — Tweet 6's body has the code already, image-less is fine.

### ✅ I. Pin CostDNA on your GitHub profile (1 minute)

github.com/pauti04 → "Customize your pins" → check CostDNA → save.

Recruiters who click your GitHub profile from the cold email find CostDNA above the fold.

### ✅ J. (Optional) Star the repo from a secondary account if you have one (1 minute)

1 star → 2 stars is a categorical visual difference on the repo page. Don't manufacture more — the audit story is enough — but going from 1 to 2 is honest.

---

## Tier 4 — only if Tier 1 doesn't produce 3+ replies in a week

If after sending the 5 cold emails and posting Show HN + LinkedIn + Twitter you have fewer than 3 substantive replies, the framing isn't landing. Iterate:

- Read your sent emails out loud. Is the audit story upfront? Is the ask too vague?
- The Show HN title might have flopped — wait a week, try variant B or C.
- The cold-email "personalization" sentence at the top is the most important. Generic emails get ignored.

Do not double down by sending more emails. Iterate the message instead.

---

## Status of the repo as of now (for your reference when responding to replies)

| Asset | State | Where |
|---|---|---|
| Repo description (audit-first) | Live | github.com/pauti04/CostDNA |
| Repo topics (methodology, label-leakage, etc) | Live | Same |
| README (audit-first restructure) | Live | Same |
| Landing page (audit-first hero, 10-section restructure) | Live | cost-dna.vercel.app |
| Live chat agent (GPT-4o, working) | Live | cost-dna.vercel.app |
| `docs/limitations.md` | In repo | github.com/pauti04/CostDNA/blob/main/docs/limitations.md |
| `docs/blog-post-audit.md` | In repo (draft) | github.com/pauti04/CostDNA/blob/main/docs/blog-post-audit.md |
| `docs/v2/headline-copy.md` | In repo (single source of truth) | Same |
| `docs/v2/results-phase2.md` | In repo (node2vec writeup) | Same |
| `docs/field-notes/` (empty, ready) | In repo | Same |
| 6 GitHub issues for follow-up work | Open | github.com/pauti04/CostDNA/issues |
| Cold-email drafts | In repo (audit-first) | docs/outreach/cold-emails.md |
| Show HN draft | In repo (audit-first) | docs/show-hn-draft.md |
| Twitter thread | In repo (audit-first) | docs/outreach/twitter-thread/THREAD.md |
| Resume/LinkedIn copy | In repo (audit-first) | docs/outreach/resume-and-linkedin.md |
| Tests + build | 16 pytest / 27 vitest / Next build all green | CI |

Repo SHA at this snapshot: `6d8ded4` (Phase 1 + 3 commit on main).

---

## TL;DR

1. **Monday:** LinkedIn update + 1 cold email
2. **Tuesday 8am:** Show HN + LinkedIn featured post + Twitter thread + 1 cold email
3. **Wednesday:** Blog post (dev.to) + 1 cold email
4. **Thursday:** 1 cold email + start DMing FinOps engineers (3/day)
5. **Friday:** Last cold email + continue DMing
6. **Following week:** respond to replies; add field-notes entries from anyone who tried it

Total time investment: ~30 minutes of pushing buttons, spread across a week.

Result: every piece of distribution work that was "drafted but not sent" is in motion. By next Wednesday you should have 3–7 conversations going.

Go.
