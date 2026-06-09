# Pilot-outreach kit — get one real user in a week

The single highest-leverage thing left for CostDNA is **one external person
running it on a real account and telling you what broke.** One field note >
any accuracy point. This doc makes that a 20-minute/day mechanical task for
one week.

It deliberately does **not** ship a list of named strangers with fabricated
titles and emails — that's how you send a "Hi {wrong name}, {wrong company}"
email and torch your credibility. Instead: the exact places to find real
candidates, the exact searches, the profile to look for, the message, and a
tracker to fill in as you go.

---

## The ideal pilot (recognize one in 5 seconds)

You want someone who **has the pain and can act without procurement**:

- **Title:** Platform Engineer, SRE, DevOps lead, Cloud Engineer, or
  "FinOps" anything. *Not* a CFO, *not* a procurement manager.
- **Company size:** ~50–500 people. Big enough to have a real untagged-AWS
  problem; small enough that one engineer can run a tool on a sandbox
  without a security-review committee.
- **Signal they have the pain:** posts/comments about AWS cost, tagging,
  Cost Explorer, "untagged," chargeback, showback, FinOps.
- **Reachability:** active on LinkedIn / a FinOps community / Twitter in
  the last ~month (so a DM actually gets seen).

**Avoid:** FOAANG-scale companies (they have dedicated FinOps platforms and
won't run a stranger's tool), and the FinOps *vendors* themselves (that's
the separate Track-1 list in `cold-emails.md` — different ask).

---

## Where to find them (real channels, ranked)

| # | Channel | How to get in | Why it works |
|---|---|---|---|
| 1 | **FinOps Foundation Slack** | Free join at finops.org → Community | Literally everyone here owns a cloud bill. Highest hit rate. |
| 2 | **r/FinOps** + **r/aws** + **r/devops** | Public; sort "new" for cost/tagging posts | People posting about untagged spend are pre-qualified |
| 3 | **LinkedIn search** | See exact strings below | Lets you target title + company-size precisely |
| 4 | **CNCF Slack #finops** | slack.cncf.io | k8s-cost crowd; CostDNA's non-k8s angle resonates |
| 5 | **Locally Optimistic / Rands Leadership Slack** | invite-based | Eng leaders who own budgets |
| 6 | **Twitter/X** | search `#FinOps` + "untagged" / "AWS cost" | DM people venting about cost attribution |

Start with #1 and #2 — highest density of the exact pain, lowest friction
to message.

---

## Exact LinkedIn search strings (copy-paste into LinkedIn search)

Run each, filter to "People", then 2nd/3rd-degree connections:

```
"FinOps" AND "AWS"
"platform engineer" AND "cost"
"SRE" AND "cloud cost"
"cloud cost" AND ("untagged" OR "tagging" OR "chargeback")
"devops" AND "cost optimization" AND "AWS"
```

For each result that fits the ideal-pilot profile, note them in the tracker
below. Aim to collect 10 before you start sending — momentum matters.

**Twitter/X equivalent:** search `FinOps untagged`, `AWS cost attribution`,
`Cost Explorer untagged` and look at who's posting (not just the big
accounts — the replies are where the practitioners are).

---

## The message (ready to send — pulled from cold-emails.md Track 2)

**LinkedIn DM / Slack DM version (short — these channels reward brevity):**

> Hi {name} — saw your {post/comment about AWS cost / role at {company}}.
> Quick one: I built an open-source tool (CostDNA, MIT) that infers
> ownership of *untagged* AWS resources from CloudTrail behaviour and writes
> the tags back, so your existing cost dashboard explains the 40–60% that's
> currently invisible.
>
> I'm looking for 1–2 design partners before calling it production-ready.
> Would you run it on a non-prod account (read-only IAM, self-hosted,
> nothing leaves your account) and tell me what breaks? 30 min of your time;
> I'll fix whatever you hit. No pitch — I want the bug report.
>
> You can also see it on your own bill in 90s without installing anything:
> cost-dna.vercel.app/your-account (parsed in-browser, nothing uploaded).

**Email version (if you find an email):** use the full Track-2 template in
[`cold-emails.md`](cold-emails.md) → "Track 2 — design-partner pilot."

**Why this converts:** the ask is *feedback*, not a sale or a job. "Tell me
what breaks" is easy to say yes to. The 90-second in-browser demo lets them
get value before committing to anything.

---

## Tracker — fill in 10, then work the list

Collect 10 real candidates first (names from the searches above), then send
2/day. Mark outcomes so you don't double-message.

| # | Name | Where found | Role / company | Channel (LI/Slack/email/X) | Sent? | Reply? | Notes |
|---|------|-------------|----------------|----------------------------|-------|--------|-------|
| 1 |  |  |  |  | ☐ | ☐ |  |
| 2 |  |  |  |  | ☐ | ☐ |  |
| 3 |  |  |  |  | ☐ | ☐ |  |
| 4 |  |  |  |  | ☐ | ☐ |  |
| 5 |  |  |  |  | ☐ | ☐ |  |
| 6 |  |  |  |  | ☐ | ☐ |  |
| 7 |  |  |  |  | ☐ | ☐ |  |
| 8 |  |  |  |  | ☐ | ☐ |  |
| 9 |  |  |  |  | ☐ | ☐ |  |
| 10 |  |  |  |  | ☐ | ☐ |  |

---

## One-week cadence

| Day | Action | Time |
|---|---|---|
| Mon | Join FinOps Foundation Slack + r/FinOps. Collect 10 candidates into the tracker. | 30 min |
| Tue | Send DMs 1–2. Personalize the first line for each. | 15 min |
| Wed | Send DMs 3–4. Reply to anything from Tue. | 15 min |
| Thu | Send DMs 5–6. | 15 min |
| Fri | Send DMs 7–8. | 15 min |
| Mon (wk2) | Send DMs 9–10. One polite follow-up to non-repliers from last Tue. | 20 min |

Expected: from 10 well-targeted DMs, 2–4 replies, 1–2 willing to actually
run it. You only need **one** to complete a pilot.

---

## When someone says yes

1. Send them the quickstart: `pip install costdna` → `costdna doctor
   --aws-profile <their-sandbox>` → `costdna scan`. Or just have them drop a
   CUR at cost-dna.vercel.app/your-account for the zero-install version.
2. Offer a 30-min screen-share — drive the install yourself if they'll let
   you. Friction kills pilots.
3. **Whatever breaks, fix it the same day.** Their bug report is the product.
4. Afterward, ask: "Can I write this up (anonymized) in the repo's field
   notes?" Point them at the field-note issue template.
5. Add the result to [`docs/field-notes/`](../field-notes/) — that's your
   first social proof, and it makes every subsequent outreach + the launch
   land harder.

---

## What a completed pilot unlocks

- A real quote/field note in the README → credibility no benchmark provides
- A concrete "used by a real team" line (with permission) for the résumé
- The bug list that tells you what to actually build next
- Social proof that makes the HN / Reddit / Product Hunt launch convert

One pilot changes the project from "impressive solo build" to "a thing
someone other than the author has run." That's the gap worth closing.
