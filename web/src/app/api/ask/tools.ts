/**
 * TypeScript port of the 9 CostDNA agent tools (src/costdna/agent.py).
 *
 * Each tool runs against a pre-baked scan loaded from public/data/scan.json
 * — pure data lookups, no compute. The Anthropic agent loop in route.ts
 * decides which to call based on the visitor's question.
 */

export type Prediction = {
  resource_id: string;
  team_pred: string;
  confidence: number;
  resource_type?: string;
  team_truth?: string;
  kind?: string;
  explanation?: string;
};

export type Metadata = {
  resource_id: string;
  resource_type?: string;
  team?: string;
  kind?: string;
  iam_role?: string;
  vpc_cidr?: string;
};

export type Signal = {
  resource_id: string;
  signal_type: string;
  value: number;
  timestamp: string;
  user_identity?: string;
  iam_role?: string;
  event_name?: string;
};

export type Deploy = {
  team: string;
  signal_type?: string;
  repo: string;
  commit: string;
  timestamp: string;
};

export type Scan = {
  predictions: Prediction[];
  metadata: Metadata[];
  signals: Signal[];
  deploys: Deploy[];
  teams: string[];
  summary: {
    total_resources: number;
    total_signal_rows: number;
    n_teams: number;
    model_test_acc: number;
  };
};

// ─────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────

function costByResource(signals: Signal[]): Map<string, number> {
  const m = new Map<string, number>();
  for (const s of signals) {
    if (s.signal_type !== "cost") continue;
    m.set(s.resource_id, (m.get(s.resource_id) ?? 0) + s.value);
  }
  return m;
}

// ─────────────────────────────────────────────────────────────────────
// Tools
// ─────────────────────────────────────────────────────────────────────

export function summarize_account(scan: Scan) {
  const cost = costByResource(scan.signals);
  const byTeam = new Map<
    string,
    { n: number; conf_sum: number; spend: number }
  >();
  for (const p of scan.predictions) {
    const e = byTeam.get(p.team_pred) ?? { n: 0, conf_sum: 0, spend: 0 };
    e.n += 1;
    e.conf_sum += p.confidence;
    e.spend += cost.get(p.resource_id) ?? 0;
    byTeam.set(p.team_pred, e);
  }
  const teams = [...byTeam.entries()]
    .map(([team, e]) => ({
      team,
      resources: e.n,
      avg_confidence: +(e.conf_sum / e.n).toFixed(3),
      total_spend: +e.spend.toFixed(2),
    }))
    .sort((a, b) => b.resources - a.resources);
  return {
    total_resources: scan.predictions.length,
    teams_found: scan.teams,
    by_team: teams,
  };
}

export function attribute_resource(scan: Scan, resource_id: string) {
  const exact = scan.predictions.find((p) => p.resource_id === resource_id);
  if (exact) {
    return {
      resource_id: exact.resource_id,
      predicted_team: exact.team_pred,
      confidence: exact.confidence,
      explanation: exact.explanation ?? "",
      resource_type: exact.resource_type,
      ground_truth_team: exact.team_truth ?? null,
    };
  }
  const lc = resource_id.toLowerCase();
  const candidates = scan.predictions
    .filter((p) => p.resource_id.toLowerCase().includes(lc))
    .slice(0, 5);
  if (candidates.length === 0) {
    return { error: `Resource ${JSON.stringify(resource_id)} not found in this scan.` };
  }
  return {
    exact_match: false,
    candidates,
    error: `No exact match for "${resource_id}"; showing candidates with that substring.`,
  };
}

export function top_spenders(
  scan: Scan,
  args: { team?: string; limit?: number },
) {
  const limit = args.limit ?? 10;
  const cost = costByResource(scan.signals);
  let rows = scan.predictions.map((p) => ({
    resource_id: p.resource_id,
    team_pred: p.team_pred,
    confidence: p.confidence,
    total_cost: +(cost.get(p.resource_id) ?? 0).toFixed(2),
  }));
  if (args.team) rows = rows.filter((r) => r.team_pred === args.team);
  rows.sort((a, b) => b.total_cost - a.total_cost);
  return { filter_team: args.team ?? null, top_spenders: rows.slice(0, limit) };
}

export function find_cost_spikes(scan: Scan, args: { top_n?: number }) {
  const n = args.top_n ?? 5;
  // Group cost signals into hourly buckets per resource.
  const hourly = new Map<string, Map<string, number>>(); // rid -> hour -> $
  for (const s of scan.signals) {
    if (s.signal_type !== "cost") continue;
    const hour = s.timestamp.slice(0, 13); // YYYY-MM-DD HH
    const inner = hourly.get(s.resource_id) ?? new Map();
    inner.set(hour, (inner.get(hour) ?? 0) + s.value);
    hourly.set(s.resource_id, inner);
  }
  // For each resource, find the largest hourly bucket.
  const spikes: { resource_id: string; spike_amount_usd: number; spike_time: string; team: string }[] = [];
  const teamByRid = new Map(scan.predictions.map((p) => [p.resource_id, p.team_pred]));
  for (const [rid, hourMap] of hourly.entries()) {
    let maxHour = "";
    let maxAmt = 0;
    for (const [h, amt] of hourMap.entries()) {
      if (amt > maxAmt) {
        maxAmt = amt;
        maxHour = h;
      }
    }
    if (maxAmt > 0) {
      spikes.push({
        resource_id: rid,
        spike_amount_usd: +maxAmt.toFixed(2),
        spike_time: maxHour,
        team: teamByRid.get(rid) ?? "unknown",
      });
    }
  }
  spikes.sort((a, b) => b.spike_amount_usd - a.spike_amount_usd);
  // Try to attribute to a deploy in the team's deploys ±3 hours before.
  const enriched = spikes.slice(0, n).map((s) => {
    const teamDeploys = scan.deploys
      .filter((d) => d.team === s.team)
      .filter((d) => {
        const dh = d.timestamp.slice(0, 13);
        return dh < s.spike_time && dh >= prevHours(s.spike_time, 6);
      })
      .sort((a, b) => b.timestamp.localeCompare(a.timestamp));
    return { ...s, nearby_deploy: teamDeploys[0] ?? null };
  });
  return { spikes: enriched };
}

function prevHours(hourStr: string, n: number): string {
  // hourStr like "2026-05-05 13" -> subtract n hours.
  const dt = new Date(hourStr.replace(" ", "T") + ":00:00Z");
  dt.setUTCHours(dt.getUTCHours() - n);
  return dt.toISOString().slice(0, 13).replace("T", " ");
}

export function find_anomalies(scan: Scan, args: { limit?: number }) {
  const limit = args.limit ?? 10;
  const sorted = [...scan.predictions]
    .sort((a, b) => a.confidence - b.confidence)
    .slice(0, limit);
  return {
    anomalies: sorted.map((p) => ({
      resource_id: p.resource_id,
      predicted_team: p.team_pred,
      confidence: p.confidence,
      explanation: p.explanation ?? "",
      anomaly_score: +(1 - p.confidence).toFixed(3),
    })),
  };
}

export function search_resources(
  scan: Scan,
  args: { substring: string; limit?: number },
) {
  const limit = args.limit ?? 20;
  const lc = args.substring.toLowerCase();
  const matches = scan.predictions.filter((p) =>
    p.resource_id.toLowerCase().includes(lc),
  );
  return {
    substring: args.substring,
    n_matches: matches.length,
    matches: matches.slice(0, limit),
  };
}

export function signal_history(
  scan: Scan,
  args: { resource_id: string; hours?: number },
) {
  const events = scan.signals.filter((s) => s.resource_id === args.resource_id);
  if (events.length === 0) {
    return { resource_id: args.resource_id, events: 0, note: "no signals for this resource" };
  }
  const byType = new Map<string, number>();
  let cost = 0;
  for (const e of events) {
    byType.set(e.signal_type, (byType.get(e.signal_type) ?? 0) + 1);
    if (e.signal_type === "cost") cost += e.value;
  }
  events.sort((a, b) => a.timestamp.localeCompare(b.timestamp));
  return {
    resource_id: args.resource_id,
    n_events: events.length,
    events_by_type: Object.fromEntries(byType),
    total_cost: +cost.toFixed(2),
    first_10_events: events.slice(0, 10),
  };
}

export function find_idle(scan: Scan, args: { max_events?: number }) {
  const maxEvents = args.max_events ?? 5;
  const counts = new Map<string, number>();
  for (const s of scan.signals) {
    counts.set(s.resource_id, (counts.get(s.resource_id) ?? 0) + 1);
  }
  const cost = costByResource(scan.signals);
  const idle = scan.predictions
    .filter((p) => (counts.get(p.resource_id) ?? 0) <= maxEvents)
    .map((p) => ({
      resource_id: p.resource_id,
      n_events: counts.get(p.resource_id) ?? 0,
      team_pred: p.team_pred,
      resource_type: p.resource_type,
      total_cost: +(cost.get(p.resource_id) ?? 0).toFixed(2),
    }))
    .sort((a, b) => b.total_cost - a.total_cost);
  return { max_events_threshold: maxEvents, n_idle: idle.length, resources: idle.slice(0, 20) };
}

export function compare_teams(scan: Scan, args: { team_a: string; team_b: string }) {
  const cost = costByResource(scan.signals);
  const stat = (team: string) => {
    const rows = scan.predictions.filter((p) => p.team_pred === team);
    const totalSpend = rows.reduce((s, r) => s + (cost.get(r.resource_id) ?? 0), 0);
    const byType: Record<string, number> = {};
    for (const r of rows) {
      const t = r.resource_type ?? "unknown";
      byType[t] = (byType[t] ?? 0) + 1;
    }
    const top3 = [...rows]
      .map((r) => ({ resource_id: r.resource_id, cost: +(cost.get(r.resource_id) ?? 0).toFixed(2) }))
      .sort((a, b) => b.cost - a.cost)
      .slice(0, 3);
    return {
      team,
      n_resources: rows.length,
      total_spend: +totalSpend.toFixed(2),
      avg_confidence: rows.length
        ? +(rows.reduce((s, r) => s + r.confidence, 0) / rows.length).toFixed(3)
        : 0,
      by_type: byType,
      top_3_resources: top3,
    };
  };
  return { team_a: stat(args.team_a), team_b: stat(args.team_b) };
}

// ─────────────────────────────────────────────────────────────────────
// Tool registry — Anthropic-format schemas
// ─────────────────────────────────────────────────────────────────────

export const TOOL_DEFINITIONS = [
  {
    name: "summarize_account",
    description:
      "High-level summary of the account: total resources, teams found, per-team resource counts and spend.",
    input_schema: { type: "object", properties: {} },
  },
  {
    name: "attribute_resource",
    description:
      "Look up which team owns a specific AWS resource and why. Returns predicted team, confidence, and the naming-signal explanation.",
    input_schema: {
      type: "object",
      properties: { resource_id: { type: "string" } },
      required: ["resource_id"],
    },
  },
  {
    name: "top_spenders",
    description:
      "Top resources by total cost in the scan window. Optionally filter by team.",
    input_schema: {
      type: "object",
      properties: {
        team: { type: "string" },
        limit: { type: "integer", default: 10 },
      },
    },
  },
  {
    name: "find_cost_spikes",
    description:
      "Find the largest hourly cost spikes and try to attribute each to a recent deploy on the resource's team.",
    input_schema: {
      type: "object",
      properties: { top_n: { type: "integer", default: 5 } },
    },
  },
  {
    name: "find_anomalies",
    description:
      "Resources with the lowest prediction confidence — likely don't fit any team well. Investigate manually.",
    input_schema: {
      type: "object",
      properties: { limit: { type: "integer", default: 10 } },
    },
  },
  {
    name: "search_resources",
    description: "Find resources whose ID contains a substring.",
    input_schema: {
      type: "object",
      properties: {
        substring: { type: "string" },
        limit: { type: "integer", default: 20 },
      },
      required: ["substring"],
    },
  },
  {
    name: "signal_history",
    description:
      "Recent CloudTrail-style events and cost samples for a specific resource.",
    input_schema: {
      type: "object",
      properties: {
        resource_id: { type: "string" },
        hours: { type: "integer", default: 24 },
      },
      required: ["resource_id"],
    },
  },
  {
    name: "find_idle",
    description:
      "Resources with very few events — candidates for cleanup, deprecation, or cost reduction.",
    input_schema: {
      type: "object",
      properties: { max_events: { type: "integer", default: 5 } },
    },
  },
  {
    name: "compare_teams",
    description:
      "Side-by-side comparison of two teams: counts, spend, by resource type, top 3 resources each.",
    input_schema: {
      type: "object",
      properties: {
        team_a: { type: "string" },
        team_b: { type: "string" },
      },
      required: ["team_a", "team_b"],
    },
  },
];

export function runTool(scan: Scan, name: string, args: any): unknown {
  switch (name) {
    case "summarize_account":
      return summarize_account(scan);
    case "attribute_resource":
      return attribute_resource(scan, args.resource_id);
    case "top_spenders":
      return top_spenders(scan, args);
    case "find_cost_spikes":
      return find_cost_spikes(scan, args);
    case "find_anomalies":
      return find_anomalies(scan, args);
    case "search_resources":
      return search_resources(scan, args);
    case "signal_history":
      return signal_history(scan, args);
    case "find_idle":
      return find_idle(scan, args);
    case "compare_teams":
      return compare_teams(scan, args);
    default:
      return { error: `unknown tool: ${name}` };
  }
}
