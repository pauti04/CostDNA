"""ML team workload — bursty training runs that hit S3 hard, mostly off-hours.

Run aggressively in evenings:
  while true; do python -m simulation.ml_workload; sleep 120; done
"""

from __future__ import annotations

import random

from simulation.common import assumed_session, load_labels


def main() -> None:
    rng = random.Random()
    sess = assumed_session("ml")
    resources = load_labels("ml")

    s3 = sess.client("s3")
    lam = sess.client("lambda")

    # Each "training run" hammers S3 for many object reads.
    n_runs = rng.randint(1, 3)
    for _ in range(n_runs):
        for bucket in resources["s3"]:
            for _ in range(rng.randint(100, 400)):
                try:
                    s3.list_objects_v2(Bucket=bucket, MaxKeys=500)
                except Exception as e:
                    print(f"  list failed: {e}")
                    break

    # Trigger inference Lambdas after training.
    for fn in resources["lambda"]:
        try:
            lam.invoke(FunctionName=fn, InvocationType="Event",
                       Payload=b'{"task": "eval"}')
        except Exception as e:
            print(f"  invoke failed: {e}")


if __name__ == "__main__":
    main()
