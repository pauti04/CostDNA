variable "role_name" {
  type        = string
  default     = "CostDNA Scan Role"
  description = "Name for the custom role definition."
}

variable "principal_id" {
  type        = string
  default     = ""
  description = "Object ID of the user / service principal / managed identity to assign the role to. Empty = create the role definition only."
}

variable "enable_tag_writeback" {
  type        = bool
  default     = false
  description = "When true, additionally grant Microsoft.Resources/tags/* so `costdna apply --apply` can write inferred tags back. Default false = strictly read-only."
}
