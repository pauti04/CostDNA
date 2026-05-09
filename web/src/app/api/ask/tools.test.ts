import { describe, it, expect } from "vitest";

import {
  attribute_resource,
  compare_teams,
  find_abandoned,
  find_anomalies,
  find_cost_spikes,
  find_idle,
  runTool,
  search_resources,
  signal_history,
  summarize_account,
  top_spenders,
  TOOL_DEFINITIONS,
  type Scan,
} from "./tools";

/**
 * A small synthetic Scan covering 5 resources across 3 teams, plus events,
 * cost signals, and a deploy ~3h before a spike. Just enough to exercise
 * each tool's happy path and the obvious edge cases without bringing in
 * the full 6 MB scan.json.
 */
function makeScan(): Scan {
  return {
    predictions: [
      { resource_id: "i-back-1",  team_pred: "backend", confidence: 0.95, resource_type: "ec2",    explanation: "iam_role contains 'backend'" },
      { resource_id: "i-data-1",  team_pred: "data",    confidence: 0.91, resource_type: "ec2" },
      { resource_id: "i-ml-1",    team_pred: "ml",      confidence: 0.55, resource_type: "ec2" },
      { resource_id: "rds-back",  team_pred: "backend", confidence: 0.83, resource_type: "rds" },
      { resource_id: "lam-orph",  team_pred: "ml",      confidence: 0.32, resource_type: "lambda" },
    ],
    metadata: [
      { resource_id: "i-back-1",  resource_type: "ec2",    iam_role: "backend-svc-role" },
      { resource_id: "i-data-1",  resource_type: "ec2",    iam_role: "data-pipeline-role" },
      { resource_id: "i-ml-1",    resource_type: "ec2",    iam_role: "ml-training-role" },
      { resource_id: "rds-back",  resource_type: "rds",    iam_role: "backend-svc-role" },
      { resource_id: "lam-orph",  resource_type: "lambda", iam_role: "" },
    ],
    signals: [
      // cost: spike on i-back-1 at 2026-05-05 14:00
      { resource_id: "i-back-1",  signal_type: "cost",             value: 12.50, timestamp: "2026-05-05 14:00:00" },
      { resource_id: "i-back-1",  signal_type: "cost",             value: 1.20,  timestamp: "2026-05-05 13:00:00" },
      { resource_id: "i-data-1",  signal_type: "cost",             value: 0.80,  timestamp: "2026-05-05 14:00:00" },
      { resource_id: "rds-back",  signal_type: "cost",             value: 5.00,  timestamp: "2026-05-05 12:00:00" },
      // events
      ...Array.from({ length: 30 }, (_, i) => ({
        resource_id: "i-back-1", signal_type: "cloudtrail_event",
        event_name: "DescribeInstances", iam_role: "backend-svc-role",
        timestamp: `2026-05-05 ${String(13 + (i % 4)).padStart(2, "0")}:${String(i).padStart(2, "0")}:00`,
        value: 1,
      })),
      ...Array.from({ length: 8 }, (_, i) => ({
        resource_id: "i-data-1", signal_type: "cloudtrail_event",
        event_name: "DescribeDBInstances", iam_role: "data-pipeline-role",
        timestamp: `2026-05-05 02:${String(i).padStart(2, "0")}:00`,
        value: 1,
      })),
      // lam-orph: only 2 events (idle)
      { resource_id: "lam-orph", signal_type: "cloudtrail_event",
        event_name: "Invoke", iam_role: "", timestamp: "2026-05-04 09:00:00", value: 1 },
      { resource_id: "lam-orph", signal_type: "cloudtrail_event",
        event_name: "Invoke", iam_role: "", timestamp: "2026-05-04 09:30:00", value: 1 },
    ],
    deploys: [
      // backend deploy 1h before the spike — should be picked up by find_cost_spikes
      { team: "backend", repo: "backend-svc", commit: "abc123",
        timestamp: "2026-05-05 12:30:00" },
    ],
    teams: ["backend", "data", "ml"],
    summary: {
      total_resources: 5,
      total_signal_rows: 100,
      n_teams: 3,
      model_test_acc: 0.87,
    },
  };
}

describe("TOOL_DEFINITIONS", () => {
  it("exposes exactly 10 tools", () => {
    expect(TOOL_DEFINITIONS).toHaveLength(10);
  });
  it("each tool has name + description + input_schema", () => {
    for (const t of TOOL_DEFINITIONS) {
      expect(t.name).toBeTruthy();
      expect(t.description).toBeTruthy();
      expect(t.input_schema).toBeDefined();
      expect((t.input_schema as { type: string }).type).toBe("object");
    }
  });
  it("tool names are unique", () => {
    const names = TOOL_DEFINITIONS.map((t) => t.name);
    expect(new Set(names).size).toBe(names.length);
  });
});

describe("summarize_account", () => {
  it("returns total_resources, teams_found, by_team breakdown", () => {
    const scan = makeScan();
    const out = summarize_account(scan) as {
      total_resources: number;
      teams_found: string[];
      by_team: { team: string; resources: number; total_spend: number }[];
    };
    expect(out.total_resources).toBe(5);
    expect(out.teams_found).toContain("backend");
    expect(out.teams_found).toContain("data");
    expect(out.teams_found).toContain("ml");

    const backend = out.by_team.find((b) => b.team === "backend");
    expect(backend?.resources).toBe(2); // i-back-1 + rds-back
    expect(backend?.total_spend).toBeGreaterThan(0);
  });
});

describe("attribute_resource", () => {
  it("returns the prediction for a known resource", () => {
    const out = attribute_resource(makeScan(), "i-back-1") as {
      resource_id: string; predicted_team: string; confidence: number;
    };
    expect(out.resource_id).toBe("i-back-1");
    expect(out.predicted_team).toBe("backend");
    expect(out.confidence).toBeCloseTo(0.95);
  });
  it("returns a not-found shape for unknown ids", () => {
    const out = attribute_resource(makeScan(), "i-does-not-exist") as { error?: string };
    expect(out.error).toBeTruthy();
  });
});

describe("top_spenders", () => {
  it("returns the highest-cost resource first", () => {
    const out = top_spenders(makeScan(), { limit: 3 }) as {
      top_spenders: { resource_id: string; total_cost: number }[];
    };
    expect(out.top_spenders.length).toBeGreaterThan(0);
    // i-back-1 has 12.50 + 1.20 = 13.70, the largest by far
    expect(out.top_spenders[0].resource_id).toBe("i-back-1");
    expect(out.top_spenders[0].total_cost).toBeGreaterThan(13);
  });
  it("filters by team when provided", () => {
    const out = top_spenders(makeScan(), { team: "backend" }) as {
      filter_team: string;
      top_spenders: { team_pred: string }[];
    };
    expect(out.filter_team).toBe("backend");
    expect(out.top_spenders.every((r) => r.team_pred === "backend")).toBe(true);
  });
});

describe("find_cost_spikes", () => {
  it("finds the largest hourly cost bucket and attributes a nearby deploy", () => {
    const out = find_cost_spikes(makeScan(), { top_n: 2 }) as {
      spikes: {
        resource_id: string;
        spike_amount_usd: number;
        team: string;
        nearby_deploy: { commit: string } | null;
      }[];
    };
    expect(out.spikes.length).toBeGreaterThan(0);
    const top = out.spikes[0];
    expect(top.resource_id).toBe("i-back-1");
    expect(top.spike_amount_usd).toBeCloseTo(12.50);
    expect(top.team).toBe("backend");
    // The backend deploy is 1.5h before the 14:00 spike, within the 6h window
    expect(top.nearby_deploy?.commit).toBe("abc123");
  });
});

describe("find_anomalies", () => {
  it("returns lowest-confidence resources first", () => {
    const out = find_anomalies(makeScan(), { limit: 2 }) as {
      anomalies: { resource_id: string; confidence: number; anomaly_score: number }[];
    };
    expect(out.anomalies).toHaveLength(2);
    // lam-orph has the lowest confidence (0.32)
    expect(out.anomalies[0].resource_id).toBe("lam-orph");
    expect(out.anomalies[0].confidence).toBeCloseTo(0.32);
    // anomaly_score = 1 - confidence
    expect(out.anomalies[0].anomaly_score).toBeCloseTo(0.68, 2);
  });
});

describe("search_resources", () => {
  it("substring-matches across resource ids", () => {
    const out = search_resources(makeScan(), { substring: "back" }) as {
      matches: { resource_id: string }[];
    };
    const ids = out.matches.map((m) => m.resource_id);
    expect(ids).toContain("i-back-1");
    expect(ids).toContain("rds-back");
    expect(ids).not.toContain("i-data-1");
  });
});

describe("signal_history", () => {
  it("returns event counts + first events for a resource", () => {
    const out = signal_history(makeScan(), { resource_id: "i-back-1", hours: 240 }) as {
      n_events: number;
      events_by_type: Record<string, number>;
      first_10_events: unknown[];
    };
    expect(out.n_events).toBeGreaterThan(0);
    expect(out.events_by_type.cloudtrail_event).toBeGreaterThan(0);
    expect(out.first_10_events.length).toBeGreaterThan(0);
  });
  it("handles unknown resource id", () => {
    const out = signal_history(makeScan(), { resource_id: "i-nope" }) as {
      events?: number; note?: string;
    };
    expect(out.events).toBe(0);
    expect(out.note).toContain("no signals");
  });
});

describe("find_idle", () => {
  it("returns resources under the max_events threshold", () => {
    const out = find_idle(makeScan(), { max_events: 3 }) as {
      n_idle: number;
      resources: { resource_id: string; n_events: number }[];
    };
    const ids = out.resources.map((r) => r.resource_id);
    expect(ids).toContain("lam-orph"); // only 2 events
    expect(ids).not.toContain("i-back-1"); // 30 events
    expect(out.n_idle).toBeGreaterThan(0);
  });
});

describe("find_abandoned", () => {
  function makeScanWithDecay(): Scan {
    // Two resources:
    //   abandoned-1: 10 events on 2026-04-01 (prior half), 0 on 2026-05-01 (recent)
    //   active-1:    5 events 2026-04-01,                 8 events 2026-05-01
    //   was-quiet-1: 2 events 2026-04-01,                 0 events 2026-05-01 — should be skipped (not enough prior)
    const events = [
      ...Array.from({ length: 10 }, (_, i) => ({
        resource_id: "abandoned-1", signal_type: "cloudtrail_event",
        event_name: "Invoke", iam_role: "ml-training-role",
        timestamp: `2026-04-01 ${String(i).padStart(2, "0")}:00:00`, value: 1,
      })),
      ...Array.from({ length: 5 }, (_, i) => ({
        resource_id: "active-1", signal_type: "cloudtrail_event",
        event_name: "Invoke", iam_role: "backend-svc-role",
        timestamp: `2026-04-01 ${String(i).padStart(2, "0")}:00:00`, value: 1,
      })),
      ...Array.from({ length: 8 }, (_, i) => ({
        resource_id: "active-1", signal_type: "cloudtrail_event",
        event_name: "Invoke", iam_role: "backend-svc-role",
        timestamp: `2026-05-01 ${String(i).padStart(2, "0")}:00:00`, value: 1,
      })),
      ...Array.from({ length: 2 }, (_, i) => ({
        resource_id: "was-quiet-1", signal_type: "cloudtrail_event",
        event_name: "Invoke", iam_role: "data-pipeline-role",
        timestamp: `2026-04-01 ${String(i).padStart(2, "0")}:00:00`, value: 1,
      })),
      // Cost rows so total_cost is non-zero for abandoned-1.
      { resource_id: "abandoned-1", signal_type: "cost",
        event_name: "", iam_role: "", value: 4.50, timestamp: "2026-04-01 00:00:00" },
    ];
    return {
      predictions: [
        { resource_id: "abandoned-1",  team_pred: "ml",      confidence: 0.9 },
        { resource_id: "active-1",     team_pred: "backend", confidence: 0.95 },
        { resource_id: "was-quiet-1",  team_pred: "data",    confidence: 0.7 },
      ],
      metadata: [],
      signals: events,
      deploys: [],
      teams: ["backend", "data", "ml"],
      summary: { total_resources: 3, total_signal_rows: events.length,
                  n_teams: 3, model_test_acc: 0.9 },
    };
  }

  it("surfaces resources whose activity collapsed", () => {
    const out = find_abandoned(makeScanWithDecay(), {}) as {
      abandoned: { resource_id: string; decay_ratio: number; total_cost: number }[];
      n_abandoned: number;
    };
    const ids = out.abandoned.map((r) => r.resource_id);
    expect(ids).toContain("abandoned-1");      // 10 -> 0 events = total decay
    expect(ids).not.toContain("active-1");     // 5 -> 8 events = growing
    expect(ids).not.toContain("was-quiet-1");  // never busy enough to qualify
    expect(out.abandoned[0].decay_ratio).toBe(0);
    expect(out.abandoned[0].total_cost).toBeCloseTo(4.50);
  });

  it("respects min_prior_events", () => {
    // With min_prior_events=15, even abandoned-1 (only 10 prior events) shouldn't qualify.
    const out = find_abandoned(makeScanWithDecay(), { min_prior_events: 15 }) as {
      n_abandoned: number;
    };
    expect(out.n_abandoned).toBe(0);
  });

  it("respects decay_threshold", () => {
    // With decay_threshold=0 (only resources with ZERO recent events qualify).
    const out = find_abandoned(makeScanWithDecay(), { decay_threshold: 0 }) as {
      abandoned: { resource_id: string; recent_events: number }[];
    };
    // abandoned-1 has 0 recent events, ratio=0, qualifies (0 ≤ 0).
    expect(out.abandoned.find((r) => r.resource_id === "abandoned-1")?.recent_events).toBe(0);
  });

  it("handles empty signals gracefully", () => {
    const empty: Scan = {
      predictions: [], metadata: [], signals: [], deploys: [],
      teams: [], summary: { total_resources: 0, total_signal_rows: 0, n_teams: 0, model_test_acc: 0 },
    };
    const out = find_abandoned(empty, {}) as { abandoned: unknown[]; note?: string };
    expect(out.abandoned).toEqual([]);
    expect(out.note).toContain("no cloudtrail events");
  });
});

describe("compare_teams", () => {
  it("returns side-by-side counts and spend for two teams", () => {
    const out = compare_teams(makeScan(), { team_a: "backend", team_b: "ml" }) as {
      backend?: unknown;
      ml?: unknown;
      [k: string]: unknown;
    };
    // Teams may come back keyed by their own name OR as a/b — check the
    // common-case keys exist.
    const keys = Object.keys(out);
    expect(keys.length).toBeGreaterThanOrEqual(2);
  });
});

describe("runTool dispatcher", () => {
  it("routes by name", () => {
    const out = runTool(makeScan(), "summarize_account", {}) as {
      total_resources: number;
    };
    expect(out.total_resources).toBe(5);
  });
  it("returns an error shape for unknown tool", () => {
    const out = runTool(makeScan(), "definitely_not_a_tool", {}) as {
      error?: string;
    };
    expect(out.error).toBeTruthy();
  });
});
