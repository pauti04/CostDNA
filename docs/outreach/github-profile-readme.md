# GitHub profile README

GitHub has a special-repo trick: if you create a public repo named exactly the same as your username (e.g. `pauti04/pauti04`), its `README.md` shows up at the top of your GitHub profile page (github.com/pauti04). Most engineers don't do this; the ones who do stand out instantly.

## Steps

1. Go to https://github.com/new
2. Repository name: **`pauti04`** (exactly your username)
3. Public, "Add a README file" checked
4. Click "Create repository"
5. Edit the README with the content below
6. Commit

That's it — visit github.com/pauti04 and you'll see the README rendered above your repo list.

## Content (paste into the README)

```markdown
## Hi, I'm Parth 👋

I build cloud-cost / FinOps / ML-infra tooling. Currently looking for full-time roles in those areas — feel free to reach out.

### 🧬 [CostDNA](https://github.com/pauti04/CostDNA) — natural-language agent for AWS cost attribution

Live demo: **[cost-dna.vercel.app](https://cost-dna.vercel.app)**

![CostDNA agent answering with real per-team spend](https://raw.githubusercontent.com/pauti04/CostDNA/main/docs/images/live-demo.gif)

Open-source agent that infers AWS resource ownership from behavioral patterns (CloudTrail, IAM, VPC flow, cost time-series) using a GraphSAGE GNN, then exposes the results as a chat interface with 9 callable tools.

The most defensible thing about it: I caught **label leakage in two published cloud datasets** (Microsoft Azure 2.6M VMs, Philly 117K jobs) by auditing my own results before claiming them, and published the honest numbers alongside the inflated first-cut ones.

**Stack:** Python · PyTorch + PyG · sentence-transformers · OpenAI SDK · Next.js · Vercel · Terraform · Docker · GitHub Actions

---

### Reach me

- 📧 parth.auti@gmail.com
- 💼 [LinkedIn](https://linkedin.com/in/<your-linkedin-slug>) ← *replace with your actual URL*
```

## Notes

- The GIF reference uses an absolute URL (`raw.githubusercontent.com/...`) — required because relative paths don't work on the profile README (it's a different repo).
- Replace `<your-linkedin-slug>` with your actual LinkedIn URL before committing.
- If you want a typing/scrolling effect, GitHub README supports `<img>` with `readme-typing-svg` — fun but unnecessary. The CostDNA GIF is enough motion.
- You can extend with sections for "Other things I've built", "What I'm currently exploring", or stats badges. But minimalism wins here — a recruiter reading github.com/pauti04 should see CostDNA, the live demo, and your contact info within 5 seconds.
