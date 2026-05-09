import { describe, it, expect } from "vitest";

import { analyzeCsv } from "./cur-analyze";


describe("analyzeCsv", () => {
  it("aggregates per-resource cost and infers team from name pattern", () => {
    const csv = [
      "lineItem/UsageAccountId,lineItem/UsageStartDate,lineItem/ProductCode,lineItem/ResourceId,lineItem/UnblendedCost",
      // backend EC2 (matches 'backend')
      "111,2026-04-01,AmazonEC2,i-backend-api-1,5.00",
      "111,2026-04-02,AmazonEC2,i-backend-api-1,2.50",
      // ml RDS (matches 'training' — most-specific ml token)
      "111,2026-04-01,AmazonRDS,arn:aws:rds:us-east-1:111:db:ml-training-cluster,12.30",
      // data S3 (matches 'pipeline')
      "111,2026-04-01,AmazonS3,arn:aws:s3:::data-pipeline-bucket,0.85",
      // line item without resource_id — should be dropped
      "111,2026-04-01,AWSDataTransfer,,1.20",
    ].join("\n");

    const out = analyzeCsv(csv);

    expect(out.resource_count).toBe(3);
    expect(out.total_cost).toBeCloseTo(5.00 + 2.50 + 12.30 + 0.85);

    const backend = out.by_team.find((t) => t.team === "backend");
    expect(backend?.total_cost).toBeCloseTo(7.50);

    const ml = out.by_team.find((t) => t.team === "ml");
    expect(ml?.total_cost).toBeCloseTo(12.30);

    const data = out.by_team.find((t) => t.team === "data");
    expect(data?.total_cost).toBeCloseTo(0.85);

    expect(out.unattributed_count).toBe(0);
  });

  it("uses word boundaries so 'ml' doesn't false-match in 'html' etc", () => {
    const csv = [
      "lineItem/UsageAccountId,lineItem/ResourceId,lineItem/UnblendedCost",
      "111,html-static-cache,1.00",        // should NOT match ml just because of 'ml'
      "111,xml-export-pipeline,2.00",       // should match data via 'pipeline'
    ].join("\n");
    const out = analyzeCsv(csv);
    const ml = out.by_team.find((t) => t.team === "ml");
    expect(ml).toBeUndefined();   // 'html' / 'xml' not classified as ml
    const data = out.by_team.find((t) => t.team === "data");
    expect(data?.n_resources).toBe(1);
  });

  it("uses the user_team tag when present and counts it as tagged", () => {
    const csv = [
      "lineItem/UsageAccountId,lineItem/ResourceId,lineItem/UnblendedCost,resourceTags/user_team",
      "111,arn:aws:ec2:us-east-1:111:instance/i-mystery-1,4.20,marketing",
      "111,arn:aws:ec2:us-east-1:111:instance/i-mystery-2,1.10,",
    ].join("\n");

    const out = analyzeCsv(csv);
    expect(out.tagged_count).toBe(1);

    const marketing = out.by_team.find((t) => t.team === "marketing");
    expect(marketing?.total_cost).toBeCloseTo(4.20);
    expect(marketing?.n_resources).toBe(1);
  });

  it("flags resources with no tag and no name match as unattributed", () => {
    const csv = [
      "lineItem/UsageAccountId,lineItem/ResourceId,lineItem/UnblendedCost,lineItem/ProductCode",
      "111,xyz-mystery-thing,9.99,AmazonEC2",
    ].join("\n");
    const out = analyzeCsv(csv);
    expect(out.unattributed_count).toBe(1);
    expect(out.unattributed_top[0].resource_id).toBe("xyz-mystery-thing");
    expect(out.unattributed_top[0].total_cost).toBeCloseTo(9.99);
  });

  it("warns helpfully if the CSV is the wrong shape", () => {
    const csv = "month,cost\n2026-04,123.45";
    const out = analyzeCsv(csv);
    expect(out.warnings.some((w) => w.includes("Cost & Usage Report"))).toBe(true);
    expect(out.resource_count).toBe(0);
  });

  it("surfaces top unattributed resources sorted by cost", () => {
    const rows = [
      "lineItem/UsageAccountId,lineItem/ResourceId,lineItem/UnblendedCost",
      "111,unknown-a,10.00",
      "111,unknown-b,50.00",
      "111,unknown-c,5.00",
      "111,backend-svc-fn,99.00",     // attributed → not in unattributed list
    ];
    const out = analyzeCsv(rows.join("\n"));
    const ids = out.unattributed_top.map((r) => r.resource_id);
    expect(ids).toEqual(["unknown-b", "unknown-a", "unknown-c"]);
    expect(ids).not.toContain("backend-svc-fn");
  });
});
