"""Data team workload — overnight batch jobs against RDS + S3.

Run aggressively during off-hours, light during day.

Run in a loop for the 1-day demo:
  while true; do python -m simulation.data_workload; sleep 90; done
"""

from __future__ import annotations

import random

from simulation.common import assumed_session, load_labels, maybe


def main() -> None:
    rng = random.Random()
    sess = assumed_session("data")
    resources = load_labels("data")

    rds = sess.client("rds")
    s3 = sess.client("s3")

    # Long-running batch query simulator: many describe + get_metric calls.
    for db_id in resources["rds"]:
        for _ in range(rng.randint(20, 80)):
            try:
                rds.describe_db_instances(DBInstanceIdentifier=db_id)
            except Exception as e:
                print(f"  describe {db_id} failed: {e}")
                break

    # Heavy S3 traffic: write-then-read, simulate ETL.
    for bucket in resources["s3"]:
        for _ in range(rng.randint(10, 30)):
            key = f"batch/{rng.randint(0, 1_000_000)}.parquet"
            try:
                if maybe(0.5, rng):
                    s3.put_object(Bucket=bucket, Key=key, Body=b"\x00" * 1024)
                else:
                    s3.list_objects_v2(Bucket=bucket, MaxKeys=200)
            except Exception as e:
                print(f"  s3 op failed: {e}")


if __name__ == "__main__":
    main()
