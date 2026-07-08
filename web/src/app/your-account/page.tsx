"use client";

import { useCallback, useState } from "react";

import { analyzeCsv, type Analysis } from "@/lib/cur-analyze";
import {
  buildRequireTagScp,
  buildTagPolicy,
  downloadJson,
  teamsFromAnalysis,
} from "@/lib/policy-gen";

const MAX_FILE_BYTES = 50 * 1024 * 1024;   // 50 MB — covers most monthly CURs


export default function YourAccountPage() {
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filename, setFilename] = useState<string | null>(null);

  const onFile = useCallback(async (file: File) => {
    setError(null);
    setBusy(true);
    setFilename(file.name);
    try {
      if (file.size > MAX_FILE_BYTES) {
        throw new Error(
          `File is ${(file.size / 1024 / 1024).toFixed(1)} MB — over the 50 MB ` +
          `safety cap. Try sub-setting the CUR (a single billing period) before uploading.`,
        );
      }
      const text = await file.text();
      // Yield a frame so the busy spinner paints before we block on parse.
      await new Promise((r) => setTimeout(r, 0));
      const result = analyzeCsv(text);
      setAnalysis(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to read file");
    } finally {
      setBusy(false);
    }
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) void onFile(f);
  }, [onFile]);

  const onPick = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) void onFile(f);
  }, [onFile]);

  const tryWithSample = useCallback(async () => {
    setError(null);
    setBusy(true);
    setFilename("sample-cur.csv");
    try {
      const r = await fetch("/sample-cur.csv");
      if (!r.ok) throw new Error(`couldn't load sample (HTTP ${r.status})`);
      const text = await r.text();
      // Yield a frame so the busy state paints.
      await new Promise((res) => setTimeout(res, 0));
      const result = analyzeCsv(text);
      setAnalysis(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load sample");
    } finally {
      setBusy(false);
    }
  }, []);

  return (
    <main className="min-h-screen bg-bg">
      {/* Nav */}
      <nav className="sticky top-0 z-50 backdrop-blur-md bg-bg/80 border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <a href="/" className="font-mono font-semibold tracking-tight text-text">
            ● CostDNA
          </a>
          <div className="flex gap-6 text-sm text-text-soft">
            <a href="/" className="hover:text-text transition">Home</a>
            <a href="/#try" className="hover:text-text transition">Live demo</a>
            <a href="https://github.com/pauti04/CostDNA"
               target="_blank" rel="noreferrer"
               className="text-text hover:underline">GitHub ↗</a>
          </div>
        </div>
      </nav>

      <section className="bg-bg-section border-b border-border">
        <div className="max-w-4xl mx-auto px-6 pt-16 pb-12">
          <div className="font-mono text-[11px] text-text-muted uppercase tracking-[0.25em] mb-6 flex items-center gap-3">
            <span className="inline-block w-8 h-px bg-border-strong" />
            Run on your own data
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight leading-tight text-text">
            Drop your AWS Cost &amp; Usage Report.<br/>
            <span className="text-text-soft">Get back a per-team breakdown.</span>
          </h1>
          <p className="mt-6 text-lg text-text-soft leading-relaxed max-w-3xl">
            Everything runs in your browser. Your CSV is parsed, aggregated, and
            classified locally — nothing transmitted, no signup, no account.
            CostDNA infers ownership using the same name-pattern heuristics
            the full version uses for its discover step.
          </p>
          <p className="mt-3 text-sm text-text-muted">
            ⓘ This is the lightweight, in-browser path — heuristic team-discovery
            only, no GraphSAGE training. For full behavioural attribution
            (including unowned-resource detection), point the Python CLI at
            your account: <code className="font-mono text-xs bg-bg-soft px-1.5 py-0.5 rounded">costdna scan --aws-profile prod</code>.
          </p>
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-6 py-10">
        {!analysis && (
          <DropZone busy={busy} error={error} filename={filename}
                    onDrop={onDrop} onPick={onPick}
                    onTrySample={tryWithSample} />
        )}
        {analysis && (
          <Results
            filename={filename!}
            analysis={analysis}
            onReset={() => { setAnalysis(null); setFilename(null); }}
          />
        )}
      </section>

      <section className="max-w-4xl mx-auto px-6 pb-20">
        <h2 className="text-xl font-semibold text-text mb-3">Where does the CUR come from?</h2>
        <ol className="text-text-soft text-sm leading-relaxed list-decimal pl-5 space-y-1.5">
          <li>AWS Console → <b className="text-text">Billing &amp; Cost Management</b> → <b className="text-text">Data Exports</b> (formerly &ldquo;Cost &amp; Usage Reports&rdquo;).</li>
          <li>Create an export with <b className="text-text">resource IDs</b> enabled. Save to S3.</li>
          <li>Download a single month&rsquo;s gzipped CSV from the bucket. Decompress.</li>
          <li>Drop the resulting <code className="font-mono text-xs bg-bg-soft px-1.5 py-0.5 rounded">.csv</code> here.</li>
        </ol>
        <p className="mt-4 text-xs text-text-muted">
          Don&rsquo;t want to set up a CUR? You can also export a small slice from
          <i> Cost Explorer → Reports → Custom → CSV</i>, but the resource-ID
          column will be missing on most line items. Some inference will work,
          most won&rsquo;t.
        </p>
      </section>
    </main>
  );
}


function DropZone({
  busy, error, filename, onDrop, onPick, onTrySample,
}: {
  busy: boolean;
  error: string | null;
  filename: string | null;
  onDrop: (e: React.DragEvent) => void;
  onPick: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onTrySample: () => void;
}) {
  return (
    <div>
      <label
        htmlFor="cur-file"
        onDrop={onDrop}
        onDragOver={(e) => e.preventDefault()}
        className="flex flex-col items-center justify-center gap-3 py-16 px-6 border-2 border-dashed border-border-strong rounded-xl bg-bg-section hover:border-text transition cursor-pointer text-center"
      >
        <div className="text-4xl">📎</div>
        <div className="text-lg font-medium text-text">
          {busy ? "Parsing…" : "Drop your CUR CSV here"}
        </div>
        <div className="text-sm text-text-soft">
          or click to pick a file
        </div>
        <div className="text-xs text-text-muted mt-2">
          ⛯ Everything runs locally — nothing is uploaded
        </div>
        <input
          id="cur-file"
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={onPick}
          disabled={busy}
        />
      </label>

      {/* Sample-data fallback. Visitors without an AWS account (most
          recruiters reading the demo) can click this and see the output
          shape in one click. The sample is a 44 KB CSV at /sample-cur.csv
          — generated by scripts/gen-sample-cur.py, gitignore-safe to commit. */}
      <div className="mt-4 flex items-center gap-3 text-sm text-text-soft">
        <span className="flex-1 h-px bg-border" />
        <span className="text-xs uppercase tracking-wider">or</span>
        <span className="flex-1 h-px bg-border" />
      </div>
      <button
        type="button"
        onClick={onTrySample}
        disabled={busy}
        className="mt-4 w-full py-3 px-6 rounded-xl border border-border bg-bg text-text font-medium hover:border-text hover:bg-bg-section transition disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {busy ? "Loading sample…" : "Try with sample data →"}
      </button>
      <p className="mt-2 text-xs text-text-muted">
        44&nbsp;KB synthetic CUR — multi-team account, mix of services,
        ~50% tag completeness. Demonstrates the output shape on data
        the heuristic can&apos;t fully attribute.
      </p>

      {filename && !busy && !error && (
        <div className="mt-3 text-sm text-text-soft">Loaded: <span className="text-text font-mono">{filename}</span></div>
      )}
      {error && (
        <div className="mt-3 p-4 rounded-lg bg-bg-soft border-l-4 border-bad text-sm text-text">
          <b>Error:</b> {error}
        </div>
      )}
    </div>
  );
}


function Results({
  filename, analysis, onReset,
}: {
  filename: string;
  analysis: Analysis;
  onReset: () => void;
}) {
  const taggedPct = analysis.resource_count > 0
    ? Math.round(100 * analysis.tagged_count / analysis.resource_count) : 0;
  const attributedPct = analysis.resource_count > 0
    ? Math.round(100 * analysis.attributed_count / analysis.resource_count) : 0;
  const unattributedSpend = analysis.unattributed_top.reduce((s, r) => s + r.total_cost, 0);

  return (
    <div className="space-y-10">
      <div className="flex items-baseline justify-between gap-4">
        <div>
          <div className="text-xs font-mono text-text-muted uppercase tracking-wider">Result</div>
          <div className="text-text font-mono text-sm mt-1">{filename}</div>
        </div>
        <button
          onClick={onReset}
          className="text-sm text-text-soft hover:text-text border border-border rounded-md px-3 py-1.5"
        >
          ← Drop another
        </button>
      </div>

      {analysis.warnings.length > 0 && (
        <div className="p-4 rounded-lg bg-bg-soft border-l-4 border-text text-sm text-text-soft">
          {analysis.warnings.map((w, i) => <div key={i}>⚠ {w}</div>)}
        </div>
      )}

      {/* Big stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-border rounded-lg overflow-hidden">
        <Stat value={`$${analysis.total_cost.toLocaleString(undefined, { maximumFractionDigits: 2 })}`}
              label="Total spend (CUR window)" />
        <Stat value={analysis.resource_count.toLocaleString()}
              label="Distinct resources" />
        <Stat value={`${taggedPct}%`}
              label="Already tagged" />
        <Stat value={`${attributedPct}%`}
              label="Attributable (tag + heuristic)" />
      </div>

      {/* By team */}
      <div>
        <h2 className="text-xl font-semibold text-text mb-3">By team (inferred)</h2>
        <div className="rounded-lg border border-border overflow-hidden bg-bg-section">
          <table className="w-full text-sm">
            <thead className="bg-bg-soft">
              <tr>
                <th className="px-4 py-2.5 text-left text-xs uppercase tracking-wider text-text-soft font-semibold">Team</th>
                <th className="px-4 py-2.5 text-right text-xs uppercase tracking-wider text-text-soft font-semibold">Resources</th>
                <th className="px-4 py-2.5 text-right text-xs uppercase tracking-wider text-text-soft font-semibold">Cost</th>
                <th className="px-4 py-2.5 text-right text-xs uppercase tracking-wider text-text-soft font-semibold">Share</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {analysis.by_team.map((t) => (
                <tr key={t.team}>
                  <td className="px-4 py-2.5 font-semibold text-text">{t.team}</td>
                  <td className="px-4 py-2.5 text-right font-mono text-text-soft">{t.n_resources}</td>
                  <td className="px-4 py-2.5 text-right font-mono text-text">${t.total_cost.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
                  <td className="px-4 py-2.5 text-right font-mono text-text-muted">{(t.share * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Unattributed top */}
      {analysis.unattributed_top.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold text-text mb-1">Unattributed — top spenders</h2>
          <p className="text-sm text-text-soft mb-3">
            ${unattributedSpend.toLocaleString(undefined, { maximumFractionDigits: 2 })}{" "}
            of spend across {analysis.unattributed_top.length} resources couldn&rsquo;t
            be attributed via tag or name pattern. <b>This is the gap CostDNA&rsquo;s
            full GraphSAGE behavioural model fills</b> — point the Python CLI at
            this account for end-to-end behavioural inference.
          </p>
          <div className="rounded-lg border border-border overflow-hidden bg-bg-section">
            <table className="w-full text-sm">
              <thead className="bg-bg-soft">
                <tr>
                  <th className="px-4 py-2.5 text-left text-xs uppercase tracking-wider text-text-soft font-semibold">Resource</th>
                  <th className="px-4 py-2.5 text-left text-xs uppercase tracking-wider text-text-soft font-semibold">Service</th>
                  <th className="px-4 py-2.5 text-right text-xs uppercase tracking-wider text-text-soft font-semibold">Cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {analysis.unattributed_top.map((r) => (
                  <tr key={r.resource_id}>
                    <td className="px-4 py-2.5 font-mono text-xs text-text break-all">{r.resource_id}</td>
                    <td className="px-4 py-2.5 text-text-soft text-xs">{r.product_code || "—"}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-text">${r.total_cost.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* By service */}
      {analysis.by_service.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold text-text mb-3">By service</h2>
          <div className="rounded-lg border border-border overflow-hidden bg-bg-section">
            <table className="w-full text-sm">
              <thead className="bg-bg-soft">
                <tr>
                  <th className="px-4 py-2.5 text-left text-xs uppercase tracking-wider text-text-soft font-semibold">Service</th>
                  <th className="px-4 py-2.5 text-right text-xs uppercase tracking-wider text-text-soft font-semibold">Cost</th>
                  <th className="px-4 py-2.5 text-right text-xs uppercase tracking-wider text-text-soft font-semibold">Share</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {analysis.by_service.map((s) => (
                  <tr key={s.service}>
                    <td className="px-4 py-2.5 font-mono text-text">{s.service}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-text-soft">${s.total_cost.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-text-muted">{(s.share * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <PolicyCard analysis={analysis} />

      <div className="pt-6 border-t border-border">
        <p className="text-sm text-text-soft">
          Want to keep going? The full Python CLI does behavioural-fingerprint
          inference (GraphSAGE), anomaly detection, and tag write-back:{" "}
          <code className="font-mono text-xs bg-bg-soft px-1.5 py-0.5 rounded">
            pip install costdna && costdna scan --aws-profile prod
          </code>
        </p>
      </div>
    </div>
  );
}


/** Close the loop in-browser: from the team breakdown, generate the AWS
 *  Organizations enforcement artifacts (tag policy + SCP) and download them.
 *  Same output shapes as `costdna policy`; the "unattributed" bucket never
 *  becomes policy. */
function PolicyCard({ analysis }: { analysis: Analysis }) {
  let teams: string[] = [];
  let unavailable: string | null = null;
  try {
    teams = teamsFromAnalysis(analysis);
  } catch (e: unknown) {
    unavailable = e instanceof Error ? e.message : "no attributed teams";
  }

  return (
    <div className="rounded-xl border border-border bg-bg-section p-6">
      <div className="flex items-baseline justify-between mb-2">
        <h2 className="text-xl font-semibold text-text">
          Close the loop: prevent future un-tagging
        </h2>
        <span className="text-[11px] uppercase tracking-wider font-mono text-text-muted">
          generated in your browser
        </span>
      </div>
      {unavailable ? (
        <p className="text-sm text-text-soft leading-relaxed">
          No attributed teams in this analysis, so there&apos;s nothing to build a
          policy from — the generator refuses to emit an empty-but-plausible
          policy. Attribute some resources first (tags or recognizable names).
        </p>
      ) : (
        <>
          <p className="text-sm text-text-soft leading-relaxed mb-4">
            From the teams found above ({teams.join(", ")}), generate the AWS
            Organizations artifacts that stop the untagged pile from growing:
            a <b className="text-text">tag policy</b> pinning the allowed{" "}
            <code className="font-mono text-xs bg-bg-soft px-1 py-0.5 rounded">team</code>{" "}
            values, and an <b className="text-text">SCP</b> denying resource
            creation without the tag (EC2/RDS/Lambda — S3 can&apos;t be gated at
            create-time). Same output as{" "}
            <code className="font-mono text-xs bg-bg-soft px-1 py-0.5 rounded">costdna policy</code>.
          </p>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => downloadJson(buildTagPolicy(teams), "tag-policy.json")}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-bg-deep text-text-on-deep font-medium text-sm hover:brightness-110 transition"
            >
              ↓ tag-policy.json
            </button>
            <button
              type="button"
              onClick={() => downloadJson(buildRequireTagScp(), "scp-require-tag.json")}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-md border border-border bg-bg text-text font-medium text-sm hover:border-text transition"
            >
              ↓ scp-require-tag.json
            </button>
          </div>
          <p className="mt-3 text-xs text-text-muted leading-relaxed">
            Attach via Organizations → Policies. Heads-up: this in-browser path
            derives teams from tags + name patterns; the CLI version
            additionally gates on model confidence before anything becomes
            policy.
          </p>
        </>
      )}
    </div>
  );
}


function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="bg-bg-section p-5">
      <div className="text-3xl font-bold tracking-tight text-text">{value}</div>
      <div className="text-xs text-text-soft mt-2 leading-snug">{label}</div>
    </div>
  );
}
