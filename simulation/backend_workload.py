"""Backend team workload — steady weekday daytime traffic.

Each call goes through an AssumeRole'd session so CloudTrail attributes the
event to the backend team's IAM role, not your user.

Run in a tight loop for the 1-day demo:
  while true; do python -m simulation.backend_workload; sleep 60; done
"""

from __future__ import annotations

import random

from simulation.common import assumed_session, load_labels, maybe


def main() -> None:
    rng = random.Random()
    sess = assumed_session("backend")
    resources = load_labels("backend")

    lam = sess.client("lambda")
    ec2 = sess.client("ec2")
    s3 = sess.client("s3")

    for fn in resources["lambda"]:
        try:
            lam.invoke(FunctionName=fn, InvocationType="RequestResponse",
                       Payload=b'{"path": "/health"}')
        except Exception as e:
            print(f"  invoke {fn} failed: {e}")

    for inst_id in resources["ec2"]:
        try:
            ec2.describe_instances(InstanceIds=[inst_id])
        except Exception as e:
            print(f"  describe {inst_id} failed: {e}")

    for bucket in resources["s3"]:
        if maybe(0.4, rng):
            try:
                s3.list_objects_v2(Bucket=bucket, MaxKeys=10)
            except Exception as e:
                print(f"  list {bucket} failed: {e}")


if __name__ == "__main__":
    main()
