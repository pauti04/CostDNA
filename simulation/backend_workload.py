"""Backend team workload - steady weekday daytime web-API traffic.

Each call goes through an AssumeRole'd session so CloudTrail attributes the
event to the backend team's IAM role.

Design goals:
  - ~30-40 events per cycle (balanced with data and ml)
  - All API calls use operations CloudTrail reliably logs
  - Distinctive mix vs other teams: heavy on Lambda invokes (web-style),
    moderate EC2 describes, light S3
"""

from __future__ import annotations

import random

from simulation.common import assumed_session, load_labels


def main() -> None:
    rng = random.Random()
    sess = assumed_session("backend")
    resources = load_labels("backend")

    lam = sess.client("lambda")
    ec2 = sess.client("ec2")
    s3 = sess.client("s3")

    # Web-style: hammer Lambda functions (each invoke = 1 data event).
    # Backend's distinctive shape: many short Lambda invokes per cycle.
    for fn in resources["lambda"]:
        for _ in range(rng.randint(15, 25)):
            try:
                lam.invoke(FunctionName=fn, InvocationType="RequestResponse",
                           Payload=b'{"path": "/health"}')
            except Exception as e:
                print(f"  invoke {fn} failed: {e}")
                break

    # Operational: describe EC2 instances (auto-scaling, status checks).
    for inst_id in resources["ec2"]:
        for _ in range(rng.randint(2, 4)):
            try:
                ec2.describe_instances(InstanceIds=[inst_id])
            except Exception as e:
                print(f"  describe {inst_id} failed: {e}")
                break

    # Light S3: write a few application logs (object-level data events).
    for bucket in resources["s3"]:
        for _ in range(rng.randint(2, 5)):
            key = f"logs/api/{rng.randint(0, 1_000_000)}.json"
            try:
                s3.put_object(Bucket=bucket, Key=key,
                              Body=b'{"event":"req","ms":42}')
            except Exception as e:
                print(f"  put {bucket} failed: {e}")
                break


if __name__ == "__main__":
    main()
