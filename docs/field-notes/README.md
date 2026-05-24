# Field notes — external usage reports

This directory collects what happens when someone other than the maintainer
runs CostDNA on a real account. The goal: even one honest external report
("I ran it, it broke at step 3, here's what I saw") is a categorically
stronger credibility signal than any number of self-reported benchmarks.

## What goes here

One file per respondent, named `NNN-anonymous-or-name.md` (use anonymous IDs
unless the person explicitly says it's fine to credit them).

Each file should answer five questions:

1. **What did they run it on?** (Real AWS account / Azure subscription / synthetic data)
2. **What was the account shape?** (Resources, teams, tag completeness, how it was structured)
3. **What worked?** (Specific commands, accuracy of predictions, useful tools)
4. **What broke?** (Errors, surprising behavior, missing features)
5. **Honest reaction:** would they use it? recommend it? what's missing?

Brutal honesty is more useful than polite praise. A "didn't work because X"
report is publishable; a "looks neat" report isn't.

## Template

See `_TEMPLATE.md` in this directory.

## How to find respondents

The cold-email and Twitter-thread drafts both end with a soft ask. The most
productive path is direct LinkedIn DM:

> Hi {name}, I built an open-source behavioral GNN for cloud-resource
> attribution and caught label leakage in two published Microsoft datasets.
> Would you run the CLI on a non-prod AWS account (or synthetic data — no
> AWS account needed) and tell me what breaks? 15 minutes of your time, I'll
> add your notes to the field-notes/ directory if you want.

Target FinOps engineers, SREs, and platform engineers — anyone who manages
multi-team AWS spend.

## When this directory has 3+ entries

The README's "External validation" section should:
- Link to this directory
- Quote 1-2 specific findings (with permission)
- Update the "this is not a production-deployed tool" caveat in
  `docs/limitations.md` if appropriate

Empty for now is fine. Empty after 4 weeks of asking is a signal that the
ask isn't landing — iterate on the cold-DM phrasing.
