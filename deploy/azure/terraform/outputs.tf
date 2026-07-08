output "role_definition_id" {
  description = "ID of the CostDNA scan role definition."
  value       = azurerm_role_definition.scan.role_definition_resource_id
}

output "mode" {
  description = "Whether tag write-back was enabled."
  value       = var.enable_tag_writeback ? "read + tag-writeback" : "read-only"
}
