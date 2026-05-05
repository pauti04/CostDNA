# Custom domain setup

The current live demo URL is `cost-dna-parths-projects-dc857b64.vercel.app` — works, but ugly for a portfolio link. A clean custom domain (`costdna.dev`, `pauti.dev/costdna`, etc.) is a 10-minute setup, costs ~$10-15/year for the domain.

## The shortest cleanup: claim `cost-dna.vercel.app`

There's already a Vercel project (separate from the current one) holding the `cost-dna.vercel.app` short URL — but it's stuck on an old commit and not updating. To free it:

1. Vercel dashboard → check for a duplicate `cost-dna` project (separate from `cost-dna-parths-projects-dc857b64`)
2. If found, delete it (Settings → Advanced → Delete Project)
3. In the working project: Settings → Domains → "Add Domain" → `cost-dna.vercel.app` (will now be available)

That gets you the cleanest free Vercel URL. **No DNS, no money.**

## Buying a real domain

Pick a domain ($10-15/year typical):

| Registrar | Notes |
|---|---|
| **Cloudflare** | Cheapest, no upsells, free WHOIS privacy. Recommended. |
| **Porkbun** | Simple, ~$10/yr for `.dev` |
| **Namecheap** | Old standby, sometimes has promos |

Suggested names (ordered by how memorable they are for a portfolio):

- `costdna.dev` — matches the project name
- `pauti.dev` (general portfolio domain — costdna lives at `/costdna` or `costdna.pauti.dev`)
- `costdna.app` — slightly pricier (.app TLD)
- `inferred.cloud` — abstract but on-theme

## Connecting the domain to Vercel

Once you've bought the domain:

1. Vercel project → Settings → Domains → "Add Domain" → enter your domain
2. Vercel will show you the DNS records you need to add. Two patterns:
   - **Apex domain (`costdna.dev`)**: Vercel asks for an `A` record pointing to `76.76.21.21`
   - **Subdomain (`www.costdna.dev`)**: Vercel asks for a `CNAME` to `cname.vercel-dns.com`
3. Go to your registrar's DNS panel, add those records
4. Wait 1-30 minutes for DNS propagation
5. Vercel auto-provisions an SSL cert via Let's Encrypt — no cert work on your end

When done, update:

- `README.md` — replace `cost-dna-parths-projects-dc857b64.vercel.app` with the new domain
- `docs/blog-post-draft.md` — same
- `docs/show-hn-draft.md` — same
- The Vercel project's "Production Domain" so future logs/aliases use the canonical name

## When NOT to bother

If this stays a side project and you're not actively job-hunting on the strength of it: don't bother. The Vercel-provided URL is fine. Recruiters don't filter by domain quality.

If you ARE using this as a hiring lever: a clean custom domain meaningfully increases credibility per resume click. Worth the $10.
