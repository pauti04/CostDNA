# Security policy

CostDNA reads CloudTrail events, IAM principals, VPC metadata, and Cost
Explorer data from production AWS accounts. The blast radius of a bug
or misuse is real — this document is what we commit to in exchange
for that trust.

For the full threat model and IAM scope rationale, see
[`docs/security.md`](docs/security.md).

## Reporting a vulnerability

**Do not** open a public GitHub issue for security reports.

Two private channels:

1. **Email:** parth.auti@gmail.com — subject line `[security] CostDNA`
2. **GitHub:** open a [private security advisory](https://github.com/pauti04/CostDNA/security/advisories/new)

Either path reaches the maintainer directly. PGP key available on
request.

## What to include

The more concrete the report, the faster the fix. Useful information:

- Affected version / commit
- Reproduction steps (minimal repro CSV, IAM policy, CLI invocation)
- Impact assessment (read-only data exposure, privilege escalation,
  cost-data tampering, etc.)
- Suggested remediation if you have one

## Response timeline

| Stage | Target |
|---|---|
| Acknowledgement | 72 hours |
| Triage + severity | 5 business days |
| Fix released for confirmed critical | 14 days |
| Public advisory (after fix) | 30 days |

These targets are commitments, not SLAs. For a critical vulnerability
that affects production users, we aim faster.

## Coordinated disclosure

We will:

- Acknowledge your report privately and confirm receipt
- Keep you in the loop while we investigate and fix
- Credit you in the public advisory (unless you prefer anonymity)
- Coordinate the disclosure date with you

We will not:

- Take legal action against good-faith security research
- Disclose your identity without permission

## Scope

In scope for this policy:

- The CostDNA Python package (`src/costdna/`)
- The CostDNA web demo (`web/`)
- The CostDNA Docker image
- The audit-check library (`web/src/lib/audit-check.ts`)
- Any deployment artifacts on `github.com/pauti04/CostDNA`

Out of scope:

- Vulnerabilities in upstream dependencies (PyTorch, OpenAI SDK, etc.)
  unless the way CostDNA uses them creates new exposure. Report those
  upstream.
- Vulnerabilities in customer-deployed copies after modification.
- Issues that require physical access to the customer's machine /
  network beyond what an authenticated AWS principal already has.

## Known limitations

These are documented and accepted, not vulnerabilities:

- **PyPI releases are not yet Sigstore-signed.** Verifying release
  integrity currently means checking the GitHub Actions provenance
  manifest and the SHA-256 in the release notes. Sigstore signing is
  tracked in [issue #8](https://github.com/pauti04/CostDNA/issues/8) (planned).
- **No SOC 2 attestation** for self-hosted deployments. For the
  managed-scan tier (currently invite-only), Type I attestation is in
  progress.
- **The optional natural-language interface** uses OpenAI's API. If
  you enable it, OpenAI is in your data path. The CLI defaults to
  not enabling it.

## Supported versions

We support security fixes for the latest two minor releases:

| Version | Supported |
|---|---|
| 0.3.x (latest) | ✅ |
| 0.2.x | ✅ |
| 0.1.x | ❌ |
| < 0.1.0 | ❌ |

Anyone running an unsupported version: please upgrade. The migration
is documented in [`CHANGELOG.md`](CHANGELOG.md).

## Out-of-bounds requests

We sometimes get reports that are out of scope but worth a public
discussion (e.g. "the docs/limitations doc could include X failure
mode"). Open a regular GitHub issue for those — public discussion is
fine when no exploit is involved.
