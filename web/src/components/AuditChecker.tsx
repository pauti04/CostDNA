"use client";

/**
 * Interactive in-browser audit checker.
 *
 * Pastes the methodology section's central claim — "run this two-line
 * check on your own dataset before reporting accuracy" — and lets the
 * visitor actually run it on a CSV. Pure client-side. No upload.
 *
 * Two paths:
 *   1. Try with sample → loads a 60-row CSV with a deliberate leak
 *      (deployment_id ≡ subscription_id) so visitors see the check
 *      firing within 3 seconds of clicking.
 *   2. Drop your own CSV → audit runs on the visitor's actual data.
 *      Useful when they want to verify the claim against a real
 *      published-cloud or proprietary dataset.
 */

import { useCallback, useState } from "react";

import {
  AuditResult,
  findDeterministicEdges,
  parseCsv,
} from "@/lib/audit-check";


/**
 * 60-row sample that reproduces the Azure-trace pattern in miniature.
 * Each deployment_id maps 1:1 to a single subscription_id, exactly
 * like the original audit finding. cpu_avg is a genuine non-leaking
 * behavioural feature for contrast.
 */
function generateSampleCsv(): string {
  const header = "deployment_id,subscription_id,cpu_bucket,resource_type,team";
  const rows: string[] = [header];
  const teams = ["backend", "data", "ml", "platform"];
  const types = ["vm", "rds", "lambda", "s3"];
  // cpu_bucket has only 4 distinct values across the 60 rows. By design each
  // bucket appears in multiple subscriptions, so cpu_bucket does NOT
  // deterministically encode subscription_id — that makes deployment_id the
  // only column flagged by the default 0.85 threshold. (A previous version
  // used cpu_avg as floats; the audit caught that too, but only because
  // 60 rows was too small to repeat values — a noisy result that confused
  // visitors. Bucketing keeps the demo's "look, only the leak fires" punch
  // and is closer to how real cloud features actually look.)
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


export default function AuditChecker() {
  const [rows, setRows] = useState<Array<Record<string, string>> | null>(null);
  const [columns, setColumns] = useState<string[]>([]);
  const [targetCol, setTargetCol] = useState<string>("");
  const [filename, setFilename] = useState<string>("");
  const [results, setResults] = useState<AuditResult[] | null>(null);
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
      // Default target = the column whose name looks like a label / id
      // / subscription / team / class. Falls back to the last column.
      const targetGuess = columns.find((c) => /target|label|class|team|subscription|vc/i.test(c))
        ?? columns[columns.length - 1];
      setTargetCol(targetGuess);
      setResults(null);
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

  const trySample = useCallback(() => {
    ingest(generateSampleCsv(), "sample-with-leak.csv");
  }, [ingest]);

  const runAudit = useCallback(() => {
    if (!rows || !targetCol) return;
    setError(null);
    try {
      const candidates = columns.filter((c) => c !== targetCol);
      const out = findDeterministicEdges(rows, targetCol, candidates, threshold);
      setResults(out);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Audit failed");
    }
  }, [rows, columns, targetCol, threshold]);

  const reset = useCallback(() => {
    setRows(null); setColumns([]); setTargetCol(""); setFilename("");
    setResults(null); setError(null);
  }, []);

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
                onClick={trySample}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-md bg-bg-deep text-text-on-deep font-medium text-sm hover:brightness-110 transition"
              >
                Try with sample (Azure-style leak) →
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
            <p className="mt-4 text-xs text-text-muted">
              Sample: 60 rows, deployment_id deterministically maps to
              subscription_id (the original Azure-trace pattern).
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
                  onChange={(e) => { setTargetCol(e.target.value); setResults(null); }}
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

            {results !== null && (
              <div className="mt-4 border-t border-border pt-5">
                {results.length === 0 ? (
                  <div className="p-4 rounded-lg bg-bg-section border-l-4 border-text">
                    <div className="font-semibold text-text mb-1">No leaks detected</div>
                    <p className="text-xs text-text-soft leading-relaxed">
                      Every non-target column you provided has determinism &lt;{" "}
                      {threshold.toFixed(2)}. Either the columns you passed in
                      genuinely span multiple target values, or your candidate
                      list missed the leaking one. The audit only checks what
                      you ask it to check.
                    </p>
                  </div>
                ) : (
                  <>
                    <div className="text-xs uppercase tracking-wider text-text-muted mb-3">
                      Leaking columns (determinism ≥ {threshold.toFixed(2)})
                    </div>
                    <div className="rounded-lg border border-border overflow-hidden">
                      <table className="w-full text-sm">
                        <thead className="bg-bg-soft">
                          <tr>
                            <th className="px-4 py-2 text-left text-xs uppercase tracking-wider text-text-soft font-semibold">Column</th>
                            <th className="px-4 py-2 text-right text-xs uppercase tracking-wider text-text-soft font-semibold">Determinism</th>
                            <th className="px-4 py-2 text-right text-xs uppercase tracking-wider text-text-soft font-semibold">Distinct values</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border bg-bg-section">
                          {results.map((r) => {
                            // High-cardinality flag: if a column has nearly
                            // as many distinct values as rows, the 1:1
                            // mapping may be coincidence (few values repeat
                            // at all), not a structural leak. Surface this
                            // so visitors don't misread the result.
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
                                <td className="px-4 py-2.5 text-right font-mono text-text font-semibold">
                                  {(r.determinism * 100).toFixed(1)}%
                                </td>
                                <td className="px-4 py-2.5 text-right font-mono text-text-soft">
                                  {r.nDistinctValues.toLocaleString()}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                    <p className="mt-3 text-xs text-text-muted leading-relaxed">
                      ⚠ Each row above is a column that deterministically
                      encodes <code className="font-mono text-text bg-bg-soft px-1 py-0.5 rounded">{targetCol}</code>.
                      Using any of these as a graph edge or feature reproduces
                      the failure mode the methodology audit documents. Drop
                      them, then re-run your model on the honest signal.
                    </p>
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
