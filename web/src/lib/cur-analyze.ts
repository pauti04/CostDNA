/**
 * Client-side AWS Cost & Usage Report (CUR) analysis.
 *
 * The full CUR has ~150 columns. We only care about a handful:
 *   lineItem/UsageAccountId          — account scope
 *   lineItem/UsageStartDate          — when
 *   lineItem/ProductCode             — service (AWSDataTransfer, AmazonEC2, …)
 *   lineItem/ResourceId              — the resource (often empty for non-resource line items)
 *   lineItem/UnblendedCost           — $$ for the line item
 *   resourceTags/user_team           — IF the resource has a team tag, use it
 *   lineItem/UsageType               — falls back to a coarser bucket
 *
 * On a typical CUR with hundreds of thousands of rows, we group by
 * resource_id, sum cost, and run name-pattern heuristics over the
 * resource ID to infer team when the tag is missing. This is the same
 * heuristic the costdna doctor uses for the "discover" step.
 */

import Papa from "papaparse";

export type CurRow = {
  resource_id: string;
  product_code: string;
  cost: number;
  account_id: string;
  user_team_tag: string;   // empty if no team tag
};

export type ResourceSummary = {
  resource_id: string;
  product_code: string;
  total_cost: number;
  inferred_team: string;
  source: "tag" | "name-pattern" | "unattributed";
  evidence: string;
};

export type Analysis = {
  total_cost: number;
  resource_count: number;
  tagged_count: number;
  attributed_count: number;
  unattributed_count: number;
  by_team: { team: string; n_resources: number; total_cost: number; share: number }[];
  by_service: { service: string; total_cost: number; share: number }[];
  resources: ResourceSummary[];
  unattributed_top: ResourceSummary[];
  warnings: string[];
};


// Common team-name patterns in IAM roles / instance names. Same idea as
// costdna's discover.py auto-discovery.
//
// Order matters — first match wins. Most-specific patterns come first.
// All tokens use \b word boundaries so short tokens (ml, ui, sre) don't
// false-match inside unrelated strings (e.g. /\bml\b/ doesn't match 'html').
const TEAM_PATTERNS: Array<[string, RegExp]> = [
  // ML-specific (high-specificity tokens).
  ["ml",        /(\bml\b|training|sagemaker|tensorflow|pytorch|inference|\bmodel\b|predictor)/i],
  // Security-specific.
  ["security",  /(\bsecurity\b|guardduty|\biam\b|audit|compliance)/i],
  // Frontend-specific.
  ["frontend",  /(frontend|\bcdn\b|nextjs|reactjs|\bui\b|static-assets)/i],
  // Analytics-specific.
  ["analytics", /(analytics|telemetry|tracking|\bmetric\b)/i],
  // Data-engineering-specific.
  ["data",      /(\bdata\b|\betl\b|pipeline|warehouse|\bdwh\b|airflow|\bdbt\b|snowflake)/i],
  // Platform/infra.
  ["platform",  /(platform|\binfra\b|devops|\bsre\b|\bops\b|terraform)/i],
  // Backend / web service (broader, deliberately last).
  ["backend",   /(backend|api-|\bsvc\b|service|webapp|prod-web)/i],
];


function inferTeam(rid: string): { team: string; evidence: string } | null {
  if (!rid) return null;
  for (const [team, pat] of TEAM_PATTERNS) {
    const m = rid.match(pat);
    if (m) return { team, evidence: `name contains '${m[0].toLowerCase()}'` };
  }
  return null;
}


function detectColumns(headers: string[]): {
  resourceId?: string; productCode?: string; cost?: string;
  accountId?: string; teamTag?: string;
} {
  // CUR columns can use slashes (raw) or underscores (post-import). Match
  // both styles, case-insensitively.
  const find = (...candidates: string[]) =>
    headers.find((h) =>
      candidates.some((c) => h.toLowerCase().replace(/[/_]/g, "") ===
                              c.toLowerCase().replace(/[/_]/g, "")));
  const teamTag = headers.find((h) => /resource_?tags?[/_]?(user[/_]?)?team/i.test(h));
  return {
    resourceId:  find("lineItem/ResourceId", "lineitem_resourceid"),
    productCode: find("lineItem/ProductCode", "lineitem_productcode"),
    cost:        find("lineItem/UnblendedCost", "lineitem_unblendedcost"),
    accountId:   find("lineItem/UsageAccountId", "lineitem_usageaccountid"),
    teamTag,
  };
}


export function analyzeCsv(text: string): Analysis {
  const warnings: string[] = [];
  const parsed = Papa.parse<Record<string, string>>(text, {
    header: true,
    skipEmptyLines: true,
    transformHeader: (h) => h.trim(),
  });
  if (parsed.errors.length) {
    warnings.push(`CSV parser encountered ${parsed.errors.length} non-fatal errors.`);
  }
  const rows = parsed.data;
  if (rows.length === 0) {
    return {
      total_cost: 0, resource_count: 0, tagged_count: 0,
      attributed_count: 0, unattributed_count: 0,
      by_team: [], by_service: [], resources: [], unattributed_top: [],
      warnings: ["No data rows found in CSV."],
    };
  }

  const headers = parsed.meta.fields ?? Object.keys(rows[0]);
  const cols = detectColumns(headers);
  if (!cols.resourceId || !cols.cost) {
    warnings.push(
      "Could not find lineItem/ResourceId or lineItem/UnblendedCost columns. " +
      "This doesn't look like a Cost & Usage Report — make sure you exported " +
      "the right format (CUR, not just a Cost Explorer cost-per-month CSV).",
    );
    return {
      total_cost: 0, resource_count: 0, tagged_count: 0,
      attributed_count: 0, unattributed_count: 0,
      by_team: [], by_service: [], resources: [], unattributed_top: [],
      warnings,
    };
  }

  // Aggregate by resource_id.
  const byResource = new Map<string, CurRow>();
  for (const row of rows) {
    const rid = (row[cols.resourceId] ?? "").trim();
    if (!rid) continue;   // Many CUR rows are non-resource line items (e.g. taxes)
    const cost = parseFloat(row[cols.cost] ?? "0") || 0;
    const existing = byResource.get(rid);
    if (existing) {
      existing.cost += cost;
      // Prefer non-empty team tag if any row has one.
      if (!existing.user_team_tag && cols.teamTag && row[cols.teamTag]?.trim()) {
        existing.user_team_tag = row[cols.teamTag]!.trim();
      }
    } else {
      byResource.set(rid, {
        resource_id: rid,
        product_code: row[cols.productCode ?? ""] ?? "",
        cost,
        account_id: row[cols.accountId ?? ""] ?? "",
        user_team_tag: cols.teamTag ? (row[cols.teamTag] ?? "").trim() : "",
      });
    }
  }

  // Classify each resource.
  let tagged = 0;
  let attributed = 0;
  const summaries: ResourceSummary[] = [];
  for (const r of byResource.values()) {
    let team = "";
    let source: "tag" | "name-pattern" | "unattributed" = "unattributed";
    let evidence = "no team tag, no name match";

    if (r.user_team_tag) {
      team = r.user_team_tag.toLowerCase();
      source = "tag";
      evidence = `tag user_team=${r.user_team_tag}`;
      tagged += 1;
      attributed += 1;
    } else {
      const inferred = inferTeam(r.resource_id);
      if (inferred) {
        team = inferred.team;
        source = "name-pattern";
        evidence = inferred.evidence;
        attributed += 1;
      }
    }

    summaries.push({
      resource_id: r.resource_id,
      product_code: r.product_code,
      total_cost: +r.cost.toFixed(2),
      inferred_team: team || "unattributed",
      source,
      evidence,
    });
  }

  // Aggregate by team and by service.
  const teamTotals = new Map<string, { n: number; total: number }>();
  const serviceTotals = new Map<string, number>();
  let totalCost = 0;
  for (const s of summaries) {
    totalCost += s.total_cost;
    const t = teamTotals.get(s.inferred_team) ?? { n: 0, total: 0 };
    t.n += 1;
    t.total += s.total_cost;
    teamTotals.set(s.inferred_team, t);
    serviceTotals.set(s.product_code,
      (serviceTotals.get(s.product_code) ?? 0) + s.total_cost);
  }

  const byTeam = [...teamTotals.entries()]
    .map(([team, t]) => ({
      team,
      n_resources: t.n,
      total_cost: +t.total.toFixed(2),
      share: totalCost > 0 ? +(t.total / totalCost).toFixed(3) : 0,
    }))
    .sort((a, b) => b.total_cost - a.total_cost);

  const byService = [...serviceTotals.entries()]
    .map(([service, total]) => ({
      service: service || "(unknown)",
      total_cost: +total.toFixed(2),
      share: totalCost > 0 ? +(total / totalCost).toFixed(3) : 0,
    }))
    .sort((a, b) => b.total_cost - a.total_cost);

  // Surface the highest-spend unattributed resources for review.
  const unattributedTop = summaries
    .filter((s) => s.source === "unattributed")
    .sort((a, b) => b.total_cost - a.total_cost)
    .slice(0, 20);

  return {
    total_cost: +totalCost.toFixed(2),
    resource_count: summaries.length,
    tagged_count: tagged,
    attributed_count: attributed,
    unattributed_count: summaries.length - attributed,
    by_team: byTeam,
    by_service: byService.slice(0, 15),
    resources: summaries.sort((a, b) => b.total_cost - a.total_cost).slice(0, 100),
    unattributed_top: unattributedTop,
    warnings,
  };
}
