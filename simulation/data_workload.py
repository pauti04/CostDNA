"""Data team workload - overnight batch ETL pipeline.

Distinctive shape:
  - Heavy S3 read+write on the data bucket (ETL pulling and writing parquet).
  - Modest RDS describes (status-poll the warehouse).
  - No Lambda invokes (data team doesn't run web APIs).
"""

from __future__ import annotations

import random

from simulation.common import assumed_session, load_labels


def main() -> None:
    rng = random.Random()
    sess = assumed_session("data")
    resources = load_labels("data")

    rds = sess.client("rds")
    s3 = sess.client("s3")
    ec2 = sess.client("ec2")

    # ETL workers periodically check their compute fleet's status. Each call
    # leaves a CloudTrail event attributed to the data team's role *for the
    # data team's EC2 instances* — distinctive vs other teams.
    for inst_id in resources["ec2"]:
        for _ in range(rng.randint(2, 4)):
            try:
                ec2.describe_instances(InstanceIds=[inst_id])
            except Exception as e:
                print(f"  describe {inst_id} failed: {e}")
                break

    # Status-poll the warehouse RDS (modest volume, not a tight loop).
    for db_id in resources["rds"]:
        for _ in range(rng.randint(3, 6)):
            try:
                rds.describe_db_instances(DBInstanceIdentifier=db_id)
            except Exception as e:
                print(f"  describe {db_id} failed: {e}")
                break

    # Heavy S3 ETL: write parquet shards, read them back. Object-level
    # operations are reliably logged as data events.
    for bucket in resources["s3"]:
        # Write phase: ~15 parquet shards per cycle.
        keys = []
        for _ in range(rng.randint(12, 20)):
            key = f"warehouse/dt={rng.randint(0, 100)}/shard-{rng.randint(0, 1_000_000)}.parquet"
            keys.append(key)
            try:
                s3.put_object(Bucket=bucket, Key=key, Body=b"\x00" * 4096)
            except Exception as e:
                print(f"  put {bucket} failed: {e}")
                break

        # Read phase: head + get a few back.
        for key in keys[:rng.randint(5, 10)]:
            try:
                s3.head_object(Bucket=bucket, Key=key)
            except Exception as e:
                print(f"  head {bucket} failed: {e}")


if __name__ == "__main__":
    main()
