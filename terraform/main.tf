terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region = var.region
}

# CloudTrail bucket — receives the audit log. One trail covers everything.
resource "aws_s3_bucket" "cloudtrail" {
  bucket        = "${var.project}-cloudtrail-${random_id.suffix.hex}"
  force_destroy = true
}

resource "random_id" "suffix" { byte_length = 4 }

data "aws_iam_policy_document" "cloudtrail_bucket" {
  statement {
    actions   = ["s3:GetBucketAcl"]
    resources = [aws_s3_bucket.cloudtrail.arn]
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }
  }
  statement {
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.cloudtrail.arn}/AWSLogs/*"]
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "s3:x-amz-acl"
      values   = ["bucket-owner-full-control"]
    }
  }
}

resource "aws_s3_bucket_policy" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id
  policy = data.aws_iam_policy_document.cloudtrail_bucket.json
}

resource "aws_cloudtrail" "main" {
  name                          = "${var.project}-trail"
  s3_bucket_name                = aws_s3_bucket.cloudtrail.id
  include_global_service_events = true
  is_multi_region_trail         = true
  enable_log_file_validation    = true
  depends_on                    = [aws_s3_bucket_policy.cloudtrail]

  # Data events — without these, S3 GetObject and Lambda Invoke are NOT
  # logged. Most behavioral signal lives in data events. Cost is ~$0.10
  # per 100K events (~$1-3 over a 1-week demo). Each selector can specify
  # exactly one resources.type, so we have one selector per type.
  advanced_event_selector {
    name = "S3 data events"
    field_selector {
      field  = "eventCategory"
      equals = ["Data"]
    }
    field_selector {
      field  = "resources.type"
      equals = ["AWS::S3::Object"]
    }
  }

  advanced_event_selector {
    name = "Lambda data events"
    field_selector {
      field  = "eventCategory"
      equals = ["Data"]
    }
    field_selector {
      field  = "resources.type"
      equals = ["AWS::Lambda::Function"]
    }
  }

  advanced_event_selector {
    name = "Management events"
    field_selector {
      field  = "eventCategory"
      equals = ["Management"]
    }
  }
}

# Shared VPC Flow Logs go to one CloudWatch log group; the AWS collector
# expects this exact name.
resource "aws_cloudwatch_log_group" "flow_logs" {
  name              = "/aws/vpc/flowlogs"
  retention_in_days = 14
}

resource "aws_iam_role" "flow_logs" {
  name = "${var.project}-vpc-flow-logs"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "vpc-flow-logs.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "flow_logs" {
  role = aws_iam_role.flow_logs.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["logs:CreateLogStream", "logs:PutLogEvents",
               "logs:DescribeLogGroups", "logs:DescribeLogStreams"]
      Resource = "*"
    }]
  })
}

# Per-team modules — see teams.tf.
output "cloudtrail_bucket"  { value = aws_s3_bucket.cloudtrail.bucket }
output "flow_log_group"     { value = aws_cloudwatch_log_group.flow_logs.name }
