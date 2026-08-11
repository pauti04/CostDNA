"use client";

/**
 * Interactive in-browser audit checker.
 *
 * Pastes the methodology section's central claim — "run this two-line
 * check on your own dataset before reporting accuracy" — and lets the
 * visitor actually run it on a CSV. Pure client-side. No upload.
 *
 * Three paths:
 *   1. Azure-style sample → a 60-row CSV with a 100% leak
 *      (deployment_id ≡ subscription_id).
 *   2. Philly-style sample → a partial leak: user_id is ~95%
 *      deterministic of vc, machine_id is ~15%. Teaches the point the
 *      re-verification surfaced — leakage is a *gradient*, not a binary.
 *   3. Drop your own CSV → audit runs on the visitor's actual data.
 *
 * Results show the FULL determinism spectrum (every candidate column
 * ranked), with the threshold as the leak/clean divider — so a partial
 * leak is visible sitting above the honest signals, not hidden behind a
 * binary "leak / no-leak".
 */

import { useCallback, useState } from "react";

import {
  AuditResult,
  findDeterministicEdges,
  parseCsv,
} from "@/lib/audit-check";


/**
 * 60-row sample reproducing the Azure-trace pattern: each deployment_id
 * maps 1:1 to a single subscription_id (100% leak). cpu_bucket / type
 * span multiple subscriptions, so only deployment_id fires.
 */
function generateAzureSampleCsv(): string {
  const header = "deployment_id,subscription_id,cpu_bucket,resource_type,team";
  const rows: string[] = [header];
  const teams = ["backend", "data", "ml", "platform"];
  const types = ["vm", "rds", "lambda", "s3"];
  const cpuBuckets = ["low", "medium", "high", "spike"];
  for (let d = 1; d <= 12; d++) {
    const sub = `sub-${["alpha", "beta", "gamma", "delta"][d % 4]}`;
    for (let r = 0; r < 5; r++) {
      rows.push([
        `dep-${d.toString().padStart(3, "0")}`,
        sub,
        cpuBuckets[(d + r * 3) % cpuBuckets.length],
        types[r % types.length],
        teams[(d + r) % teams.length],
      ].join(","));
    }
  }
  return rows.join("\n") + "\n";
}


/**
 * Philly-style PARTIAL leak, mirroring the real re-verified finding
 * (scripts/bench-philly.py): user_id is ~95% deterministic of the virtual
 * cluster (38 of 40 users live in one vc; 2 span two), while machine_id is
 * a shared pool across clusters → low determinism. gpu_bucket is noise.
 * This is the honest, more interesting case — a leak that isn't 100%.
 */
function generatePhillySampleCsv(): string {
  const header = "job_id,user_id,machine_id,gpu_bucket,vc";
  const rows: string[] = [header];
  const vcs = ["vc-research", "vc-vision", "vc-nlp", "vc-speech", "vc-rl"];
  const machines = Array.from({ length: 10 }, (_, i) => `m${(i + 1).toString().padStart(3, "0")}`);
  const gpuBuckets = ["1gpu", "2gpu", "4gpu", "8gpu"];
  const N_USERS = 40;
  let job = 0;
  for (let u = 1; u <= N_USERS; u++) {
    const homeVc = vcs[u % vcs.length];
    const spansTwo = u === 7 || u === 23;          // 2/40 → determinism 0.95
    for (let j = 0; j < 2; j++) {
      const vc = spansTwo && j === 1 ? vcs[(u + 1) % vcs.length] : homeVc;
      // Most machines are a shared pool (span many vcs → low determinism);
      // two users run on cluster-dedicated boxes so machine_id lands at
      // ~15%, mirroring the real Philly machine→vc figure (0.144) rather
      // than a sterile 0%.
      const machine = u <= 2
        ? `m-${homeVc}-dedicated`
        : machines[(u * 3 + j * 7) % machines.length];
      rows.push([
        `job-${(++job).toString().padStart(4, "0")}`,
        `user-${u.toString().padStart(2, "0")}`,
        machine,
        gpuBuckets[(u + j) % gpuBuckets.length],
        vc,
      ].join(","));
    }
  }
  return rows.join("\n") + "\n";
}


export default function AuditChecker() {
  const [rows, setRows] = useState<Array<Record<string, string>> | null>(null);
  const [columns, setColumns] = useState<string[]>([]);
  const [targetCol, setTargetCol] = useState<string>("");
  const [filename, setFilename] = useState<string>("");
  // Full spectrum: every candidate ranked (computed with threshold 0). The
  // leak/clean split is applied in the UI at `threshold` so moving the
  // threshold reclassifies rows without re-scanning.
  const [spectrum, setSpectrum] = useState<AuditResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [threshold, setThreshold] = useState(0.85);

  const ingest = useCallback((text: string, name: string) => {
    setError(null);
    try {
      const { rows, columns } = parseCsv(text);
      if (rows.length === 0) throw new Error("CSV is empty");
      setRows(rows);
      setColumns(columns);
      setFilename(name);
      const targetGuess = columns.find((c) => /target|label|class|team|subscription|vc/i.test(c))
        ?? columns[columns.length - 1];
      setTargetCol(targetGuess);
      setSpectrum(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to parse CSV");
    }
  }, []);

  const onFile = useCallback(async (file: File) => {
    if (file.size > 5 * 1024 * 1024) {
      setError("Files over 5 MB will lock the browser thread. Try a smaller sample.");
      return;
    }
    ingest(await file.text(), file.name);
  }, [ingest]);

  const runAudit = useCallback(() => {
    if (!rows || !targetCol) return;
    setError(null);
    try {
      const candidates = columns.filter((c) => c !== targetCol);
      // threshold 0 → return EVERY candidate with its determinism, ranked.
      const all = findDeterministicEdges(rows, targetCol, candidates, 0);
      setSpectrum(all);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Audit failed");
    }
  }, [rows, columns, targetCol]);

  const reset = useCallback(() => {
    setRows(null); setColumns([]); setTargetCol(""); setFilename("");
    setSpectrum(null); setError(null);
  }, []);

  const leaks = spectrum?.filter((r) => r.determinism >= threshold) ?? [];

  return (
    <div className="rounded-xl border border-border bg-bg overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-bg-soft">
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-text/40" />
          <div className="w-2.5 h-2.5 rounded-full bg-text/30" />
          <div className="w-2.5 h-2.5 rounded-full bg-text/20" />
        </div>
        <span className="text-xs text-text-soft font-mono ml-2">
          audit.py — interactive · runs in your browser
        </span>
      </div>

      <div className="p-5 sm:p-6">
        {!rows && (
          <>
            <p className="text-sm text-text-soft leading-relaxed mb-4">
              Run the two-line audit on your own data. Drop any CSV with a
              target column (team / label / subscription / vc / class) and
              one or more candidate columns. The check is entirely client-
              side — your data never leaves the browser.
            </p>
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => ingest(generateAzureSampleCsv(), "azure-sample-100pct-leak.csv")}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-md bg-bg-deep text-text-on-deep font-medium text-sm hover:brightness-110 transition"
              >
                Azure-style leak (100%) →
              </button>
              <button
                type="button"
                onClick={() => ingest(generatePhillySampleCsv(), "philly-sample-partial-leak.csv")}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-md bg-bg-deep text-text-on-deep font-medium text-sm hover:brightness-110 transition"
              >
                Philly-style partial leak (~95%) →
              </button>
              <label className="inline-flex items-center gap-2 px-4 py-2.5 rounded-md border border-border bg-bg-section text-text font-medium text-sm hover:border-text transition cursor-pointer">
                Drop your CSV
                <input
                  type="file"
                  accept=".csv,text/csv"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) void onFile(f);
                  }}
                />
              </label>
            </div>
            <p className="mt-4 text-xs text-text-muted leading-relaxed">
              The two samples show the range: Azure&apos;s <code className="font-mono text-text bg-bg-soft px-1 py-0.5 rounded">deployment_id</code> is
              a <b className="text-text">100%</b> lookup of the label; Philly&apos;s <code className="font-mono text-text bg-bg-soft px-1 py-0.5 rounded">user_id</code> is
              a <b className="text-text">~95%</b> partial leak sitting just above the honest <code className="font-mono text-text bg-bg-soft px-1 py-0.5 rounded">machine_id</code> signal.
              Leakage is a gradient — that&apos;s why the threshold matters.
            </p>
          </>
        )}

        {rows && (
          <>
            <div className="flex items-baseline justify-between mb-4">
              <div className="text-xs font-mono text-text-soft">
                <span className="text-text">{filename}</span>{" · "}
                {rows.length.toLocaleString()} rows{" · "}
                {columns.length} columns
              </div>
              <button
                type="button"
                onClick={reset}
                className="text-xs text-text-soft hover:text-text"
              >
                ← reset
              </button>
            </div>

            <div className="grid sm:grid-cols-[1fr_auto_auto] gap-3 items-end mb-5">
              <label className="block text-xs">
                <span className="block text-text-soft mb-1.5 uppercase tracking-wider text-[10px]">
                  Target column (the prediction label)
                </span>
                <select
                  value={targetCol}
                  onChange={(e) => { setTargetCol(e.target.value); setSpectrum(null); }}
                  className="w-full font-mono text-xs px-3 py-2 rounded-md border border-border bg-bg-section text-text"
                >
                  {columns.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </label>
              <label className="block text-xs">
                <span className="block text-text-soft mb-1.5 uppercase tracking-wider text-[10px]">
                  Threshold
                </span>
                <input
                  type="number"
                  min={0.5}
                  max={1.0}
                  step={0.05}
                  value={threshold}
                  onChange={(e) => setThreshold(parseFloat(e.target.value))}
                  className="w-24 font-mono text-xs px-3 py-2 rounded-md border border-border bg-bg-section text-text"
                />
              </label>
              <button
                type="button"
                onClick={runAudit}
                className="px-4 py-2 rounded-md bg-accent text-white font-medium text-sm hover:brightness-110 transition"
              >
                Run audit
              </button>
            </div>

            {spectrum !== null && (
              <div className="mt-4 border-t border-border pt-5">
                {spectrum.length === 0 ? (
                  <div className="p-4 rounded-lg bg-bg-section border-l-4 border-text">
                    <div className="font-semibold text-text mb-1">No candidate columns</div>
                    <p className="text-xs text-text-soft leading-relaxed">
                      There were no non-target columns to check. Add candidate
                      columns to the CSV, or pick a different target.
                    </p>
                  </div>
                ) : (
                  <>
                    <div className="flex items-baseline justify-between mb-3">
                      <div className="text-xs uppercase tracking-wider text-text-muted">
                        Determinism of <code className="font-mono text-text">{targetCol}</code> — every candidate, ranked
                      </div>
                      <div className="text-xs text-text-soft">
                        {leaks.length === 0
                          ? "no leaks ≥ threshold"
                          : `${leaks.length} leaking ≥ ${threshold.toFixed(2)}`}
                      </div>
                    </div>
                    <div className="rounded-lg border border-border overflow-hidden">
                      <table className="w-full text-sm">
                        <thead className="bg-bg-soft">
                          <tr>
                            <th className="px-4 py-2 text-left text-xs uppercase tracking-wider text-text-soft font-semibold">Column</th>
                            <th className="px-4 py-2 text-left text-xs uppercase tracking-wider text-text-soft font-semibold">Determinism</th>
                            <th className="px-4 py-2 text-right text-xs uppercase tracking-wider text-text-soft font-semibold">Verdict</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border bg-bg-section">
                          {spectrum.map((r) => {
                            const isLeak = r.determinism >= threshold;
                            const highCardinality = rows!
                              && r.nDistinctValues > 0.8 * rows!.length;
                            return (
                              <tr key={r.column}>
                                <td className="px-4 py-2.5 font-mono text-text">
                                  {r.column}
                                  {highCardinality && (
                                    <span
                                      className="ml-2 text-[10px] uppercase tracking-wider text-text-muted"
                                      title="High cardinality — the determinism may be coincidental on this dataset's small sample size, not a real structural leak."
                                    >
                                      ⓘ high-card
                                    </span>
                                  )}
                                </td>
                                <td className="px-4 py-2.5">
                                  {/* mini determinism bar */}
                                  <div className="flex items-center gap-2">
                                    <div className="h-1.5 w-24 rounded-full bg-bg-soft overflow-hidden">
                                      <div
                                        className={`h-full rounded-full ${isLeak ? "bg-bad" : "bg-text/40"}`}
                                        style={{ width: `${Math.round(r.determinism * 100)}%` }}
                                      />
                                    </div>
                                    <span className={`font-mono text-xs ${isLeak ? "text-text font-semibold" : "text-text-soft"}`}>
                                      {(r.determinism * 100).toFixed(1)}%
                                    </span>
                                  </div>
                                </td>
                                <td className="px-4 py-2.5 text-right">
                                  {isLeak ? (
                                    <span className="text-[10px] uppercase tracking-wider font-semibold text-bad">⚠ leak — drop it</span>
                                  ) : (
                                    <span className="text-[10px] uppercase tracking-wider text-text-muted">honest signal</span>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                    <p className="mt-3 text-xs text-text-muted leading-relaxed">
                      {leaks.length > 0 ? (
                        <>⚠ Columns above the {threshold.toFixed(2)} line deterministically
                        encode <code className="font-mono text-text bg-bg-soft px-1 py-0.5 rounded">{targetCol}</code> —
                        using them as a graph edge or feature reproduces the leakage the
                        methodology audit documents. Drop them and re-run on the honest signal below the line.</>
                      ) : (
                        <>No column clears {threshold.toFixed(2)}. These candidates span multiple
                        target values — but absence of evidence isn&apos;t evidence of absence; the audit
                        only checks the columns you pass it.</>
                      )}
                    </p>
                    <div className="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-text-soft">
                      <span>Want this in CI?</span>
                      <code className="font-mono text-text bg-bg-soft px-1.5 py-0.5 rounded">pip install leakaudit</code>
                      <span className="text-text-muted">— the same check as a one-liner or a{" "}
                        <code className="font-mono text-text bg-bg-soft px-1 py-0.5 rounded">--fail-on-leak</code> gate.
                      </span>
                    </div>
                  </>
                )}
              </div>
            )}
          </>
        )}

        {error && (
          <div className="mt-3 p-3 rounded-lg bg-bg-soft border-l-4 border-bad text-sm text-text">
            <b>Error:</b> {error}
          </div>
        )}
      </div>
    </div>
  );
}
