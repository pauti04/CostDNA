# Deploying the CostDNA scan role — Azure

Azure counterpart of the AWS role in [`../cloudformation/`](../cloudformation/):
a **least-privilege custom RBAC role** granting exactly what the Azure
collector calls — nothing else. Read-only by default; tag write-back is a
separate opt-in.

**Permissions granted** (derived from `src/costdna/collectors/azure_live.py`):

| Action | Why |
|---|---|
| `Microsoft.Resources/subscriptions/read` + `.../resources/read` | Enumerate resources with created/changed timestamps |
| `Microsoft.Insights/eventtypes/values/read` | Activity Log — Azure's CloudTrail equivalent |
| `Microsoft.CostManagement/query/action` + `query/read` | Cost query (both forms — see caveat) |
| `Microsoft.Network/networkSecurityGroups/read` | NSG adjacency signal |
| `Microsoft.Resources/tags/*` | **Only when** `enableTagWriteback=true` |

## Option A — Bicep

```bash
az deployment sub create --location eastus --template-file main.bicep
# with assignment + write-back:
az deployment sub create --location eastus --template-file main.bicep \
  --parameters principalId=$(az ad signed-in-user show --query id -o tsv) \
               enableTagWriteback=true
```

## Option B — Terraform

```bash
cd terraform
terraform init && terraform apply
# terraform apply -var principal_id=<objectId> -var enable_tag_writeback=true
```

## Using it

```bash
az login                                   # DefaultAzureCredential picks this up
costdna scan --cloud azure --region <subscription_id>
```

## Honest status

- The **Terraform module passes `terraform validate`**. The **Bicep template
  has not been compiled** (no `az`/`bicep` CLI on the authoring machine) —
  run `az bicep build --file main.bicep` before first use.
- The Azure collector itself is implemented per SDK patterns but **has not
  been validated against a live subscription** (the △ in the README's
  multi-cloud table). Both `Microsoft.CostManagement/query/action` and
  `query/read` are granted because the live-validated minimal set isn't yet
  known. Running this role + `costdna scan --cloud azure` on a real
  subscription is exactly the afternoon of work that flips △ → ✓ — field
  notes welcome.
