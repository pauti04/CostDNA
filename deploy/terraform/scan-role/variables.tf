variable "role_name" {
  type        = string
  default     = "CostDNAScanRole"
  description = "Name for the created IAM role."
}

variable "trusted_principal_arn" {
  type        = string
  default     = ""
  description = <<-EOT
    ARN of the principal permitted to assume this role (your IAM user, a CI
    role, or the CostDNA managed-scan account). Empty = trust the account root
    (any principal in this account with sts:AssumeRole).
  EOT
}

variable "external_id" {
  type        = string
  default     = ""
  sensitive   = true
  description = <<-EOT
    Optional shared secret required on AssumeRole. Recommended for the managed
    (cross-account) case to prevent the confused-deputy problem. Empty for the
    self-hosted CLI.
  EOT
}

variable "enable_tag_writeback" {
  type        = bool
  default     = false
  description = <<-EOT
    When true, also grant write access to tag EC2/RDS/Lambda/S3 resources,
    gated so it can only modify resources already marked managed_by=costdna.
    Default false = strictly read-only.
  EOT
}
