# CostDNA scan role — Terraform equivalent of ../main.bicep.
# Least-privilege Azure custom role: read-only by default, opt-in tag
# write-back. Permissions derived from the API calls documented in
# src/costdna/collectors/azure_live.py.

terraform {
  required_version = ">= 1.3"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

data "azurerm_subscription" "current" {}

locals {
  read_actions = [
    "Microsoft.Resources/subscriptions/read",
    "Microsoft.Resources/subscriptions/resources/read",
    "Microsoft.Insights/eventtypes/values/read",
    # Both forms included — the SDK's cost query path hasn't been validated
    # against a live subscription yet (see the project's multi-cloud caveat).
    "Microsoft.CostManagement/query/action",
    "Microsoft.CostManagement/query/read",
    "Microsoft.Network/networkSecurityGroups/read",
  ]
  writeback_actions = ["Microsoft.Resources/tags/*"]
}

resource "azurerm_role_definition" "scan" {
  name        = var.role_name
  scope       = data.azurerm_subscription.current.id
  description = "Least-privilege role for CostDNA cost-attribution scans. Read-only unless tag write-back was explicitly enabled."

  permissions {
    actions = var.enable_tag_writeback ? concat(
      local.read_actions, local.writeback_actions
    ) : local.read_actions
    not_actions = []
  }

  assignable_scopes = [data.azurerm_subscription.current.id]
}

resource "azurerm_role_assignment" "scan" {
  count              = var.principal_id != "" ? 1 : 0
  scope              = data.azurerm_subscription.current.id
  role_definition_id = azurerm_role_definition.scan.role_definition_resource_id
  principal_id       = var.principal_id
}
