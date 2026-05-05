# CostDNA — landing page (Next.js)

Polished marketing/portfolio site for the [CostDNA project](../).

## Stack

- Next.js 14 (App Router, static export-friendly)
- TypeScript + Tailwind CSS
- Framer Motion for scroll-driven animations
- No backend — pre-baked content, deployable as static

## Develop

```bash
cd web
npm install
npm run dev          # http://localhost:3000
npm run build        # production build
```

## Deploy to Vercel

The fastest route — **import the GitHub repo at https://vercel.com/new**:

1. Pick `pauti04/CostDNA`
2. **Set "Root Directory"** to `web` (Vercel will auto-detect Next.js)
3. Build command: `npm run build` (default)
4. Output directory: `.next` (default)
5. Click Deploy

Vercel will assign a URL like `costdna-pauti04.vercel.app`. To use a custom
domain, add it in Vercel's project settings.

## Layout

```
src/
  app/
    layout.tsx       # root layout, fonts, OG tags
    page.tsx         # the actual landing page (hero, audit, tools, etc.)
    globals.css      # Tailwind + CSS vars + grid pattern
  components/
    AskDemo.tsx      # animated terminal demo of `costdna chat`
    CodeBlock.tsx    # styled code block with copy-to-clipboard
    FadeIn.tsx       # framer-motion scroll-triggered reveal
public/
  images/            # synced from ../docs/images on build
```

The static `docs/index.html` page in the repo root remains as a GitHub Pages
fallback. Vercel deployment is the production site.
