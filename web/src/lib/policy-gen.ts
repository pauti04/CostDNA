/**
 * In-browser port of costdna.policy — generate AWS Organizations governance
 * from an in-browser CUR analysis. Same output shapes as the Python
 * generator (src/costdna/policy.py), kept in sync the same way
 * audit-check.ts mirrors audit.py.
 *
 * Differences from the CLI version, stated honestly:
 * - The CLI gates on model confidence (>= 0.7). The in-browser path is the
 *   heuristic tag/name-pattern analyzer, which has no confidence score —
 *   so we gate on attribution *source* instead: only teams attributed via
 *   an explicit tag or a name-pattern match contribute allowed values;
 *   the "unattributed" bucket never becomes policy.
 * - Same S3 caveat as the CLI: CreateBucket doesn't honor aws:RequestTag,
 *   so S3 is excluded from the SCP (bucket tags apply post-create).
 */

import type { Analysis } from "./cur-analyze";

export const DEFAULT_ENFORCED_FOR = [
  "ec2:instance",
  "ec2:volume",
  "rds:db",
  "lambda:function",
  "s3:bucket",
] as const;

const SCP_CREATE_ACTIONS: Record<string, string[]> = {
  "ec2:RunInstances": ["arn:aws:ec2:*:*:instance/*"],
  "rds:CreateDBInstance": ["arn:aws:rds:*:*:db:*"],
  "lambda:CreateFunction": ["arn:aws:lambda:*:*:function:*"],
};

/** Teams eligible for policy: real attributions only, never the
 *  "unattributed" bucket. Throws if nothing qualifies — a policy derived
 *  from zero attributed teams would be empty-but-plausible, which is the
 *  failure mode the Python version also refuses. */
export function teamsFromAnalysis(analysis: Analysis): string[] {
  const teams = analysis.by_team
    .map((t) => t.team)
    .filter((t) => t && t !== "unattributed");
  if (teams.length === 0) {
    throw new Error(
      "No attributed teams found — refusing to generate a policy from an " +
      "empty team set.",
    );
  }
  return [...new Set(teams)].sort();
}

export function buildTagPolicy(
  teams: string[],
  tagKey = "team",
): Record<string, unknown> {
  if (teams.length === 0) throw new Error("teams must be non-empty");
  return {
    tags: {
      [tagKey]: {
        tag_key: { "@@assign": tagKey },
        tag_value: { "@@assign": [...teams].sort() },
        enforced_for: { "@@assign": [...DEFAULT_ENFORCED_FOR].sort() },
      },
    },
  };
}

export function buildRequireTagScp(tagKey = "team"): Record<string, unknown> {
  const statements = Object.entries(SCP_CREATE_ACTIONS)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([action, resources]) => {
      const service = action.split(":")[0];
      const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
      return {
        Sid: `Deny${cap(service)}CreateWithout${cap(tagKey)}Tag`,
        Effect: "Deny",
        Action: [action],
        Resource: resources,
        Condition: { Null: { [`aws:RequestTag/${tagKey}`]: "true" } },
      };
    });
  return { Version: "2012-10-17", Statement: statements };
}

/** Trigger a client-side download of a JSON object as a file. */
export function downloadJson(obj: unknown, filename: string): void {
  const blob = new Blob([JSON.stringify(obj, null, 2) + "\n"], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
