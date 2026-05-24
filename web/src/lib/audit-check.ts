/**
 * Client-side port of costdna.audit.find_deterministic_edges.
 *
 * Same math as the Python implementation in src/costdna/audit.py; same
 * docstring intent. Runs entirely in the visitor's browser — no
 * uploads, no server round-trip — so they can paste their own
 * sensitive ML training data and audit it without leaving the page.
 *
 * The function is the single thing this project most wants other people
 * to copy-paste into their own pipelines. Keeping the TypeScript and
 * Python versions in sync is intentional: anyone who sees the demo here
 * can either use the JS version or grab the Python one from the repo.
 *
 * Reference implementation in costdna.audit.find_deterministic_edges.
 */

export type AuditResult = {
  column: string;
  determinism: number;     // 0.0 to 1.0
  nDistinctValues: number;
};

/**
 * For each candidate column, compute the fraction of distinct values
 * that map to exactly one value of the target column. A value of 1.0
 * means the column is a perfect lookup of the target — using it as a
 * graph edge or feature reproduces the failure mode documented in
 * the audit blog post.
 *
 * Columns above `threshold` (default 0.85) are returned, sorted by
 * determinism descending. An empty result means the candidates you
 * passed in are clean — but absence of evidence is not evidence of
 * absence; only the columns you list are checked.
 */
export function findDeterministicEdges(
  rows: Array<Record<string, string>>,
  targetCol: string,
  candidateCols: string[],
  threshold: number = 0.85,
): AuditResult[] {
  if (rows.length === 0) return [];
  if (!(targetCol in rows[0])) {
    throw new Error(`target_col '${targetCol}' not in dataset columns`);
  }

  const results: AuditResult[] = [];
  for (const col of candidateCols) {
    if (col === targetCol) continue;
    if (!(col in rows[0])) {
      throw new Error(`candidate column '${col}' not in dataset`);
    }
    // Group target values by the candidate column's value. If a
    // candidate value maps to more than one distinct target value,
    // it's not deterministic of the target.
    const groups = new Map<string, Set<string>>();
    for (const row of rows) {
      const key = row[col];
      const tgt = row[targetCol];
      if (key === undefined || tgt === undefined) continue;
      let set = groups.get(key);
      if (!set) { set = new Set(); groups.set(key, set); }
      set.add(tgt);
    }
    const nDistinct = groups.size;
    if (nDistinct === 0) continue;
    let deterministic = 0;
    for (const set of groups.values()) {
      if (set.size === 1) deterministic += 1;
    }
    const determinism = deterministic / nDistinct;
    results.push({
      column: col,
      determinism,
      nDistinctValues: nDistinct,
    });
  }

  return results
    .filter((r) => r.determinism >= threshold)
    .sort((a, b) => b.determinism - a.determinism);
}


/**
 * Parse a CSV string into row-objects. Pure-JS — no Papa Parse dependency
 * here because we use this only on small audit inputs (a few hundred rows
 * typical). For the multi-MB CUR path, the /your-account page uses Papa
 * Parse directly. Simple parser handles: quoted strings, escaped quotes,
 * trailing newlines.
 */
export function parseCsv(text: string): {
  rows: Array<Record<string, string>>;
  columns: string[];
} {
  const lines = text.replace(/\r\n/g, "\n").split("\n").filter((l) => l.length > 0);
  if (lines.length === 0) return { rows: [], columns: [] };

  const splitRow = (row: string): string[] => {
    const out: string[] = [];
    let cur = "";
    let inQuotes = false;
    for (let i = 0; i < row.length; i++) {
      const c = row[i];
      if (inQuotes) {
        if (c === '"') {
          if (row[i + 1] === '"') { cur += '"'; i++; }
          else inQuotes = false;
        } else {
          cur += c;
        }
      } else {
        if (c === '"') inQuotes = true;
        else if (c === ",") { out.push(cur); cur = ""; }
        else cur += c;
      }
    }
    out.push(cur);
    return out;
  };

  const columns = splitRow(lines[0]).map((c) => c.trim());
  const rows: Array<Record<string, string>> = [];
  for (let i = 1; i < lines.length; i++) {
    const values = splitRow(lines[i]);
    const row: Record<string, string> = {};
    for (let j = 0; j < columns.length; j++) {
      row[columns[j]] = (values[j] ?? "").trim();
    }
    rows.push(row);
  }
  return { rows, columns };
}
