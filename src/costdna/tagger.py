"""Tag write-back.

Translates predictions into AWS resource tagging operations. Output is
either:
  - a list of `aws` CLI commands (default; safe to inspect)
  - actual boto3 calls to put-tags on the live account (`--apply` flag)

We never write tags for low-confidence predictions — that's the whole
point of the confidence column. Threshold defaults to 0.7 (matching the
exec summary).
"""

from __future__ import annotations

import logging
import shlex
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class TagOp:
    resource_id: str
    resource_type: str
    team: str
    confidence: float
    cli_command: str


def _cli_command(rid: str, rtype: str, team: str) -> str:
    """Build the appropriate AWS CLI command for the resource type."""
    tag_arg = f"Key=team,Value={shlex.quote(team)} Key=costdna:inferred,Value=true"
    if rtype == "ec2":
        return f"aws ec2 create-tags --resources {rid} --tags {tag_arg}"
    if rtype == "rds":
        return (f"aws rds add-tags-to-resource "
                f"--resource-name arn:aws:rds:REGION:ACCOUNT:db:{rid} "
                f"--tags {tag_arg.replace('=', '=').replace(' ', ' ')}")
    if rtype == "lambda":
        return (f"aws lambda tag-resource "
                f"--resource arn:aws:lambda:REGION:ACCOUNT:function:{rid} "
                f"--tags team={shlex.quote(team)},costdna:inferred=true")
    if rtype == "s3":
        return (f"aws s3api put-bucket-tagging --bucket {rid} "
                f"--tagging 'TagSet=[{{Key=team,Value={team}}},"
                f"{{Key=costdna:inferred,Value=true}}]'")
    return f"# unknown resource_type={rtype} for {rid}"


def build_tag_ops(
    predictions_df,
    *,
    min_confidence: float = 0.7,
) -> list[TagOp]:
    """Returns one TagOp per predictable resource above the confidence threshold."""
    ops: list[TagOp] = []
    for _, row in predictions_df.iterrows():
        if float(row["confidence"]) < min_confidence:
            continue
        rid = str(row["resource_id"])
        rtype = str(row.get("resource_type", "ec2"))
        team = str(row["team_pred"])
        ops.append(TagOp(
            resource_id=rid,
            resource_type=rtype,
            team=team,
            confidence=float(row["confidence"]),
            cli_command=_cli_command(rid, rtype, team),
        ))
    return ops


def apply_tags_live(
    ops: list[TagOp],
    profile: str | None = None,
    region: str = "us-east-1",
) -> tuple[int, int]:
    """Actually write tags via boto3. Returns (succeeded, failed).

    Caller should confirm with the user first — this mutates the live account.
    """
    import boto3
    sess = boto3.Session(profile_name=profile, region_name=region)
    ec2 = sess.client("ec2")
    rds = sess.client("rds")
    lam = sess.client("lambda")
    s3 = sess.client("s3")

    succeeded = 0
    failed = 0
    for op in ops:
        tags = [
            {"Key": "team", "Value": op.team},
            {"Key": "costdna:inferred", "Value": "true"},
        ]
        try:
            if op.resource_type == "ec2":
                ec2.create_tags(Resources=[op.resource_id], Tags=tags)
            elif op.resource_type == "rds":
                # RDS needs the ARN, which we can't reconstruct without the account.
                arn = f"arn:aws:rds:{region}:" + sess.client("sts").get_caller_identity()["Account"] + f":db:{op.resource_id}"
                rds.add_tags_to_resource(ResourceName=arn,
                                          Tags=tags)
            elif op.resource_type == "lambda":
                arn = f"arn:aws:lambda:{region}:" + sess.client("sts").get_caller_identity()["Account"] + f":function:{op.resource_id}"
                lam.tag_resource(Resource=arn, Tags={t["Key"]: t["Value"] for t in tags})
            elif op.resource_type == "s3":
                s3.put_bucket_tagging(
                    Bucket=op.resource_id,
                    Tagging={"TagSet": tags},
                )
            else:
                log.warning("unknown type %s for %s", op.resource_type, op.resource_id)
                failed += 1
                continue
            succeeded += 1
        except Exception as e:
            log.warning("tag failed for %s: %s", op.resource_id, e)
            failed += 1
    return succeeded, failed
