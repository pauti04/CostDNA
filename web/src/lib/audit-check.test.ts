/**
 * Mirrors tests/test_audit.py so the TS port is verified against the
 * same patterns the Python implementation catches:
 *   - Microsoft Azure: deployment_id ≡ subscription_id (100% deterministic)
 *   - Microsoft Philly: user_id → vc (~95% deterministic; fixture below uses a
 *     90% example to exercise partial-determinism detection at the threshold)
 *   - Threshold respected
 *   - Clean data returns empty
 */
import { describe, expect, it } from "vitest";
import { findDeterministicEdges, parseCsv } from "./audit-check";


describe("findDeterministicEdges", () => {
  it("flags Azure-style 100% determinism", () => {
    const rows = [
      { deployment_id: "d1", subscription_id: "A", cpu_avg: "0.3" },
      { deployment_id: "d1", subscription_id: "A", cpu_avg: "0.4" },
      { deployment_id: "d2", subscription_id: "B", cpu_avg: "0.5" },
      { deployment_id: "d2", subscription_id: "B", cpu_avg: "0.6" },
      { deployment_id: "d3", subscription_id: "C", cpu_avg: "0.7" },
      { deployment_id: "d3", subscription_id: "C", cpu_avg: "0.8" },
    ];
    const out = findDeterministicEdges(rows, "subscription_id",
      ["deployment_id", "cpu_avg"]);
    const dep = out.find((r) => r.column === "deployment_id");
    expect(dep).toBeDefined();
    expect(dep!.determinism).toBeCloseTo(1.0, 5);
  });

  it("flags Philly-style partial determinism", () => {
    // 9 of 10 users (90%) map to a single vc → flagged at default 0.85
    const rows: Array<Record<string, string>> = [];
    for (let u = 1; u <= 9; u++) {
      const vc = ["x", "y", "z"][u % 3];
      rows.push({ user_id: `u${u}`, vc });
      rows.push({ user_id: `u${u}`, vc });
    }
    rows.push({ user_id: "u10", vc: "x" });
    rows.push({ user_id: "u10", vc: "y" });
    const out = findDeterministicEdges(rows, "vc", ["user_id"]);
    expect(out).toHaveLength(1);
    expect(out[0].column).toBe("user_id");
    expect(out[0].determinism).toBeCloseTo(0.9, 5);
  });

  it("returns empty when no candidate is deterministic", () => {
    const rows = [
      { target: "A", feat: "x" },
      { target: "B", feat: "x" },
      { target: "A", feat: "y" },
      { target: "B", feat: "y" },
      { target: "A", feat: "x" },
      { target: "B", feat: "y" },
    ];
    expect(findDeterministicEdges(rows, "target", ["feat"])).toEqual([]);
  });

  it("respects the threshold parameter", () => {
    // 4 of 5 distinct edge values → 0.8 determinism. Below default 0.85
    // (not flagged); above 0.5 (flagged).
    const rows = [
      { edge: "x", target: "A" },
      { edge: "y", target: "A" },
      { edge: "z", target: "B" },
      { edge: "z", target: "B" },
      { edge: "w", target: "A" },
      { edge: "w", target: "B" },
      { edge: "v", target: "A" },
    ];
    expect(findDeterministicEdges(rows, "target", ["edge"])).toEqual([]);
    const lowered = findDeterministicEdges(rows, "target", ["edge"], 0.5);
    expect(lowered).toHaveLength(1);
    expect(lowered[0].column).toBe("edge");
  });

  it("silently skips target column included as a candidate", () => {
    const rows = [
      { target: "A", other: "x" },
      { target: "A", other: "x" },
      { target: "B", other: "y" },
    ];
    const out = findDeterministicEdges(rows, "target", ["target", "other"]);
    expect(out.find((r) => r.column === "target")).toBeUndefined();
  });

  it("throws on missing target column", () => {
    const rows = [{ a: "1" }];
    expect(() => findDeterministicEdges(rows, "missing", ["a"])).toThrow();
  });

  it("throws on missing candidate column", () => {
    const rows = [{ target: "A" }];
    expect(() => findDeterministicEdges(rows, "target", ["nonexistent"])).toThrow();
  });
});


describe("parseCsv", () => {
  it("parses a simple comma-separated table", () => {
    const text = "a,b,c\n1,2,3\n4,5,6\n";
    const { rows, columns } = parseCsv(text);
    expect(columns).toEqual(["a", "b", "c"]);
    expect(rows).toEqual([
      { a: "1", b: "2", c: "3" },
      { a: "4", b: "5", c: "6" },
    ]);
  });

  it("handles quoted strings containing commas", () => {
    const text = `a,b\n"hello, world",1\n"with ""escaped"" quotes",2`;
    const { rows } = parseCsv(text);
    expect(rows[0].a).toBe("hello, world");
    expect(rows[1].a).toBe('with "escaped" quotes');
  });

  it("handles CRLF line endings", () => {
    const text = "a,b\r\n1,2\r\n3,4\r\n";
    const { rows } = parseCsv(text);
    expect(rows).toEqual([{ a: "1", b: "2" }, { a: "3", b: "4" }]);
  });
});
