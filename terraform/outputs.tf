output "ec2_instances" {
  value = { for k, v in aws_instance.team : k => v.id }
}

output "rds_instances" {
  value = { for k, v in aws_db_instance.team : k => v.identifier }
}

output "lambda_functions" {
  value = { for k, v in aws_lambda_function.team : k => v.function_name }
}

output "s3_buckets" {
  value = { for k, v in aws_s3_bucket.team : k => v.bucket }
}

output "iam_roles" {
  value = { for k, v in aws_iam_role.team : k => v.arn }
}

# Used by the simulation scripts to know who owns what.
# This file is your ground truth — never include it in model training inputs.
resource "local_file" "labels" {
  filename = "${path.module}/../labels.csv"
  content  = join("\n", concat(
    ["resource_id,team"],
    [for k, v in aws_instance.team       : "${v.id},${split("-", k)[0]}"],
    [for k, v in aws_db_instance.team    : "${v.identifier},${k}"],
    [for k, v in aws_lambda_function.team: "${v.function_name},${k}"],
    [for k, v in aws_s3_bucket.team      : "${v.bucket},${k}"],
  ))
}
