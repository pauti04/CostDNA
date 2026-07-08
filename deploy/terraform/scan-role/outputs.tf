output "role_arn" {
  description = "ARN of the CostDNA scan role. Add an ~/.aws/config profile with role_arn=<this> + source_profile, then `costdna scan --aws-profile costdna`."
  value       = aws_iam_role.scan.arn
}

output "role_name" {
  description = "Name of the created role."
  value       = aws_iam_role.scan.name
}

output "mode" {
  description = "Whether tag write-back was enabled."
  value       = var.enable_tag_writeback ? "read + tag-writeback" : "read-only"
}
