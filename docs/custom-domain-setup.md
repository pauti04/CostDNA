# Custom domain setup

The live demo is currently at **`cost-dna.vercel.app`** — clean and free. If you want to upgrade to a true custom domain (`costdna.dev`, `pauti.dev/costdna`, etc.) for resume polish, this is the path.

## Buying a domain

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

When done, sweep the URL across the repo:

```bash
# from repo root
grep -rln "cost-dna.vercel.app" --include="*.md" --include="*.tsx" \
  | xargs sed -i '' 's|cost-dna.vercel.app|YOUR-NEW-DOMAIN|g'
```

Then commit, push. Vercel auto-deploys, the new domain goes live, and every link in the README/blog/Show HN drafts updates in one shot.

## When NOT to bother

If this stays a side project and you're not actively job-hunting on the strength of it: don't bother. The Vercel-provided `cost-dna.vercel.app` is fine — it's also short and memorable.

If you ARE using this as a hiring lever: a true custom domain meaningfully increases credibility per resume click. Worth the $10.
