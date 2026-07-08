// CostDNA scan role — least-privilege Azure custom role (AZ-104-style RBAC).
//
// Mirrors deploy/cloudformation for AWS: read-only by default, opt-in tag
// write-back. Permissions are derived from the actual API calls documented
// in src/costdna/collectors/azure_live.py (resources.list, activity_logs.list,
// cost-management query, NSG read).
//
// Deploy at subscription scope:
//   az deployment sub create --location eastus --template-file main.bicep \
//     [--parameters principalId=<objectId> enableTagWriteback=true]
//
// Honest caveat (matching the project's multi-cloud table): the Azure
// collector is implemented per SDK patterns but has not been validated
// against a live subscription. This role is the access-granting half of
// that story; a live run is what flips the △ to ✓.

targetScope = 'subscription'

@description('Object ID of the user / service principal / managed identity to assign the role to. Leave empty to only create the role definition.')
param principalId string = ''

@description('When true, additionally grant tag write access (Microsoft.Resources/tags/*) so `costdna apply --apply` can write inferred tags back. Default false = strictly read-only.')
param enableTagWriteback bool = false

@description('Name for the custom role.')
param roleName string = 'CostDNA Scan Role'

var readActions = [
  // Enumerate resources with createdTime/changedTime (resources.list expand)
  'Microsoft.Resources/subscriptions/read'
  'Microsoft.Resources/subscriptions/resources/read'
  // Activity Log — Azure's CloudTrail equivalent (activity_logs.list)
  'Microsoft.Insights/eventtypes/values/read'
  // Cost Management query. The SDK's query API is exposed as an action in
  // Azure RBAC; the read form is included as well since the collector path
  // has not yet been validated against a live subscription.
  'Microsoft.CostManagement/query/action'
  'Microsoft.CostManagement/query/read'
  // NSG read (flow-log adjacency signal)
  'Microsoft.Network/networkSecurityGroups/read'
]

var writebackActions = [
  // Tag write-back only — the essence of the built-in Tag Contributor role,
  // without any other write permission.
  'Microsoft.Resources/tags/*'
]

resource scanRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: guid(subscription().id, roleName)
  properties: {
    roleName: roleName
    description: 'Least-privilege role for CostDNA cost-attribution scans. Read-only unless tag write-back was explicitly enabled at deploy time.'
    type: 'CustomRole'
    permissions: [
      {
        actions: enableTagWriteback ? concat(readActions, writebackActions) : readActions
        notActions: []
        dataActions: []
        notDataActions: []
      }
    ]
    assignableScopes: [
      subscription().id
    ]
  }
}

resource scanAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (principalId != '') {
  name: guid(subscription().id, principalId, roleName)
  properties: {
    roleDefinitionId: scanRole.id
    principalId: principalId
  }
}

output roleDefinitionId string = scanRole.id
output mode string = enableTagWriteback ? 'read + tag-writeback' : 'read-only'
