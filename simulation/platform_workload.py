"""Platform team workload — shared infra accessed by everyone.

Steady but moderate. Hits its own resources, plus light cross-team checks
(simulating cross-team observability scrapes).

  while true; do python -m simulation.platform_workload; sleep 180; done
"""

from __future__ import annotations

import random

from simulation.common import assumed_session, load_labels


def main() -> None:
    rng = random.Random()
    sess = assumed_session("platform")
    resources = load_labels("platform")

    ec2 = sess.client("ec2")
    s3 = sess.client("s3")
    lam = sess.client("lambda")

    # Platform team frequently lists / describes everything for monitoring.
    try:
        ec2.describe_instances()
    except Exception as e:
        print(f"  describe_instances failed: {e}")

    for inst in resources["ec2"]:
        try:
            ec2.describe_instances(InstanceIds=[inst])
        except Exception as e:
            print(f"  describe {inst} failed: {e}")

    # Log archival pattern — list and occasionally write to logs buckets.
    for bucket in resources["s3"]:
        try:
            s3.list_objects_v2(Bucket=bucket, MaxKeys=50)
            if rng.random() < 0.3:
                s3.put_object(Bucket=bucket,
                              Key=f"logs/{rng.randint(0, 10**6)}.gz",
                              Body=b"log entry")
        except Exception as e:
            print(f"  s3 op failed: {e}")

    # Shared utility lambdas get invoked frequently.
    for fn in resources["lambda"]:
        try:
            lam.invoke(FunctionName=fn, InvocationType="RequestResponse",
                       Payload=b'{"action": "health-check"}')
        except Exception as e:
            print(f"  invoke {fn} failed: {e}")


if __name__ == "__main__":
    main()
