# Realistic mess. These resources don't belong to any team —
# they simulate what a lived-in AWS account looks like after a few years.
#
# Categories:
#   vendor  — looks like a vendor's forwarder / scanner / log archive
#   legacy  — old naming, old IAM, old VPC; sparse occasional access
#   orphan  — IAM principal no longer exists; near-zero recent activity
#   shadow  — console-deployed, no IaC, weird default-style names
#
# These are NOT included in labels.csv (intentional) — the model has to
# discover them via the anomaly detector instead.

# ---------- Vendor (Datadog-like forwarder) ----------
# Trust BOTH lambda.amazonaws.com (so the function can run) and Datadog's
# published account (so the integration could be assumed in a real setup).
resource "aws_iam_role" "vendor_datadog" {
  name = "DatadogIntegrationRole-${random_id.suffix.hex}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
        Action    = "sts:AssumeRole"
      },
      {
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::464622532012:root" }
        Action    = "sts:AssumeRole"
      },
    ]
  })
}

resource "aws_lambda_function" "vendor_datadog_forwarder" {
  function_name = "DatadogForwarder-${random_id.suffix.hex}"
  role          = aws_iam_role.vendor_datadog.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  filename      = data.archive_file.lambda_zip.output_path
}

resource "aws_s3_bucket" "vendor_cloudflare_logs" {
  bucket        = "cloudflare-access-logs-${random_id.suffix.hex}"
  force_destroy = true
}

# ---------- Legacy (old naming convention, old VPC) ----------
resource "aws_iam_role" "legacy" {
  name = "legacy-2019-billing-export-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_s3_bucket" "legacy_billing" {
  bucket        = "old-billing-bucket-2019-${random_id.suffix.hex}"
  force_destroy = true
  # Notably absent: any team tag.
}

resource "aws_lambda_function" "legacy_cron" {
  function_name = "billing-export-2018"
  role          = aws_iam_role.legacy.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  filename      = data.archive_file.lambda_zip.output_path
}

# ---------- Orphan (former-employee resources) ----------
# We can't actually delete the IAM principal here while still owning the
# resource — that requires manual cleanup post-apply. The role name hints
# at the situation.
resource "aws_iam_role" "orphan" {
  name = "deleted-user-alice.smith-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_s3_bucket" "orphan_personal" {
  bucket        = "alice-smith-personal-bucket-${random_id.suffix.hex}"
  force_destroy = true
}

resource "aws_lambda_function" "orphan_test" {
  function_name = "alice-smith-test-fn"  # AWS Lambda names can't contain dots
  role          = aws_iam_role.orphan.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  filename      = data.archive_file.lambda_zip.output_path
}

# ---------- Shadow (console-deployed, no IaC pattern) ----------
# Real shadow infra is deployed via console and isn't managed by Terraform.
# We simulate the artifacts (weird names, no team association) but Terraform
# still owns them — in a real account they'd be unmanaged.
resource "aws_iam_role" "shadow_basic" {
  name = "lambda_basic_execution_console"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_lambda_function" "shadow_my_function" {
  function_name = "myFunction-2"
  role          = aws_iam_role.shadow_basic.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  filename      = data.archive_file.lambda_zip.output_path
}

resource "aws_lambda_function" "shadow_untitled" {
  function_name = "test-deploy-v3"
  role          = aws_iam_role.shadow_basic.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  filename      = data.archive_file.lambda_zip.output_path
}
