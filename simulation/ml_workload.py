"""ML team workload - bursty late-night training runs.

Distinctive shape:
  - Heavy S3 reads (training data + model checkpoints) — object-level GETs
    that CloudTrail reliably logs as data events.
  - Moderate S3 writes (checkpoint artifacts).
  - One Lambda invoke per cycle (kick off async eval).
  - No RDS, no EC2 describes (ml team doesn't poll infra status).
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

    for bucket in resources["s3"]:
        # First seed a few checkpoint files so we have something to GET.
        # (We won't have them on the very first cycle but that's fine.)
        seed_keys = []
        for _ in range(rng.randint(3, 6)):
            key = f"checkpoints/run-{rng.randint(0, 1_000_000)}/model-step{rng.randint(0, 100000)}.bin"
            seed_keys.append(key)
            try:
                s3.put_object(Bucket=bucket, Key=key,
                              Body=b"\xff" * 8192)  # 8KB "model"
            except Exception as e:
                print(f"  put {bucket} failed: {e}")
                break

        # Heavy read phase: training-style fetch of many "training-data" objects.
        # head_object is an object-level data event = reliably logged.
        for _ in range(rng.randint(20, 30)):
            key = f"training-data/batch-{rng.randint(0, 1000)}/sample-{rng.randint(0, 100000)}.parquet"
            # First write so the GET will find something (then head it).
            try:
                s3.put_object(Bucket=bucket, Key=key, Body=b"\x00" * 1024)
                s3.head_object(Bucket=bucket, Key=key)
            except Exception as e:
                print(f"  s3 op failed: {e}")
                break

    # End each "training run" with one inference Lambda invoke.
    for fn in resources["lambda"]:
        try:
            lam.invoke(FunctionName=fn, InvocationType="Event",
                       Payload=b'{"task": "eval", "checkpoint": "latest"}')
        except Exception as e:
            print(f"  invoke {fn} failed: {e}")


if __name__ == "__main__":
    main()
