# CostDNA scan role — Terraform equivalent of the CloudFormation template.
# Least-privilege, read-only by default; opt-in tag write-back scoped to
# resources CostDNA has marked (managed_by=costdna). Cross-account trust with
# an optional ExternalId (confused-deputy-safe) for the managed-scan case.

terraform {
  required_version = ">= 1.3"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  # Default trust: the account root (any principal in this account that can
  # sts:AssumeRole). Override with var.trusted_principal_arn for cross-account.
  trusted_principal = (
    var.trusted_principal_arn != ""
    ? var.trusted_principal_arn
    : "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
  )
}

data "aws_iam_policy_document" "assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = [local.trusted_principal]
    }

    # ExternalId gate — only added when var.external_id is set. This is the
    # confused-deputy mitigation the SAA exam calls out for third-party roles.
    dynamic "condition" {
      for_each = var.external_id != "" ? [1] : []
      content {
        test     = "StringEquals"
        variable = "sts:ExternalId"
        values   = [var.external_id]
      }
    }
  }
}

data "aws_iam_policy_document" "readonly" {
  statement {
    sid    = "DiscoverAndAttribute"
    effect = "Allow"
    actions = [
      "cloudtrail:LookupEvents",
      "ec2:DescribeInstances",
      "ec2:DescribeVolumes",
      "ec2:DescribeVpcs",
      "ec2:DescribeSubnets",
      "ec2:DescribeFlowLogs",
      "rds:DescribeDBInstances",
      "lambda:ListFunctions",
      "s3:ListAllMyBuckets",
      "s3:GetBucketTagging",
      "iam:ListRoles",
      "iam:ListUsers",
      "iam:GetRole",
      "iam:GetUser",
      "iam:ListAttachedRolePolicies",
      "ce:GetCostAndUsage",
      "ce:GetCostAndUsageWithResources",
      "ce:GetCostCategories",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role" "scan" {
  name                 = var.role_name
  description          = "Read-only role for CostDNA cost-attribution scans."
  assume_role_policy   = data.aws_iam_policy_document.assume.json
  max_session_duration = 3600

  tags = {
    app        = "costdna"
    managed_by = "costdna"
  }
}

resource "aws_iam_role_policy" "readonly" {
  name   = "CostDNAReadOnly"
  role   = aws_iam_role.scan.id
  policy = data.aws_iam_policy_document.readonly.json
}

# Opt-in tag write-back — created only when enable_tag_writeback = true.
# Scoped so it can never touch a resource CostDNA didn't already mark.
data "aws_iam_policy_document" "writeback" {
  count = var.enable_tag_writeback ? 1 : 0
  statement {
    sid    = "TagWriteback"
    effect = "Allow"
    actions = [
      "ec2:CreateTags",
      "rds:AddTagsToResource",
      "lambda:TagResource",
      "s3:PutBucketTagging",
    ]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/managed_by"
      values   = ["costdna"]
    }
  }
}

resource "aws_iam_role_policy" "writeback" {
  count  = var.enable_tag_writeback ? 1 : 0
  name   = "CostDNATagWriteback"
  role   = aws_iam_role.scan.id
  policy = data.aws_iam_policy_document.writeback[0].json
}
