/**
 * Mirrors tests/test_policy.py so the TS port stays in sync with the Python
 * generator — same @@assign shapes, same S3 exclusion, same refusal to
 * build policy from an empty/unattributed team set.
 */
import { describe, expect, it } from "vitest";

import type { Analysis } from "./cur-analyze";
import {
  buildRequireTagScp,
  buildTagPolicy,
  teamsFromAnalysis,
} from "./policy-gen";

function analysisWith(teams: { team: string; n: number; cost: number }[]): Analysis {
  return {
    total_cost: teams.reduce((s, t) => s + t.cost, 0),
    resource_count: teams.reduce((s, t) => s + t.n, 0),
    tagged_count: 0,
    attributed_count: 0,
    unattributed_count: 0,
    by_team: teams.map((t) => ({
      team: t.team, n_resources: t.n, total_cost: t.cost, share: 0,
    })),
    by_service: [],
    resources: [],
    unattributed_top: [],
    warnings: [],
  };
}

describe("teamsFromAnalysis", () => {
  it("returns sorted unique attributed teams, excluding 'unattributed'", () => {
    const a = analysisWith([
      { team: "ml", n: 3, cost: 100 },
      { team: "data", n: 2, cost: 50 },
      { team: "unattributed", n: 9, cost: 900 },
    ]);
    expect(teamsFromAnalysis(a)).toEqual(["data", "ml"]);
  });

  it("throws when only 'unattributed' exists — never an empty policy", () => {
    const a = analysisWith([{ team: "unattributed", n: 5, cost: 100 }]);
    expect(() => teamsFromAnalysis(a)).toThrow(/refusing/i);
  });
});

describe("buildTagPolicy", () => {
  it("matches the Python @@assign schema", () => {
    const pol = buildTagPolicy(["ml", "data"]) as {
      tags: Record<string, Record<string, unknown>>;
    };
    const entry = pol.tags["team"];
    expect(entry["tag_key"]).toEqual({ "@@assign": "team" });
    expect(entry["tag_value"]).toEqual({ "@@assign": ["data", "ml"] });
    const enforced = (entry["enforced_for"] as { "@@assign": string[] })["@@assign"];
    expect(enforced).toContain("ec2:instance");
    expect(enforced).toContain("s3:bucket"); // reporting covers S3...
  });

  it("supports a custom tag key", () => {
    const pol = buildTagPolicy(["a"], "cost_center") as {
      tags: Record<string, unknown>;
    };
    expect(Object.keys(pol.tags)).toEqual(["cost_center"]);
  });
});

describe("buildRequireTagScp", () => {
  it("denies creation without the tag, and excludes S3 (no RequestTag on CreateBucket)", () => {
    const scp = buildRequireTagScp() as {
      Version: string;
      Statement: { Action: string[]; Effect: string; Condition: unknown }[];
    };
    expect(scp.Version).toBe("2012-10-17");
    const actions = scp.Statement.flatMap((s) => s.Action);
    expect(new Set(actions)).toEqual(
      new Set(["ec2:RunInstances", "rds:CreateDBInstance", "lambda:CreateFunction"]),
    );
    for (const s of scp.Statement) {
      expect(s.Effect).toBe("Deny");
      expect(s.Condition).toEqual({ Null: { "aws:RequestTag/team": "true" } });
    }
  });
});
