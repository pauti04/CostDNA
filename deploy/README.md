# Deploying the CostDNA scan role

CostDNA needs read-only access to discover and attribute resources in your
account. This directory gives you two ways to grant it — CloudFormation or
Terraform — both least-privilege, read-only by default, with an opt-in
tag-write-back grant.

**Safe by default.** The role can read CloudTrail / IAM / EC2 / RDS / Lambda /
S3 / Cost Explorer, and nothing else. Tag write-back is a *separate* opt-in
grant, scoped so it can only ever touch resources CostDNA has already marked
`managed_by=costdna`. Full threat model: [`../docs/security.md`](../docs/security.md).

---

## Azure

The Azure equivalent (least-privilege custom RBAC role, Bicep + Terraform)
lives in [`azure/`](azure/). Same posture: read-only by default, opt-in tag
write-back.

## Option A — CloudFormation

**One command (recommended — always works):**

```bash
aws cloudformation deploy \
  --template-file cloudformation/costdna-scan-role.yaml \
  --stack-name costdna-scan-role \
  --capabilities CAPABILITY_NAMED_IAM
```

Read + write-back, cross-account with an external ID:

```bash
aws cloudformation deploy \
  --template-file cloudformation/costdna-scan-role.yaml \
  --stack-name costdna-scan-role \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
      EnableTagWriteback=true \
      TrustedPrincipalArn=arn:aws:iam::111122223333:role/costdna-scanner \
      ExternalId=$(openssl rand -hex 16)
```

**Console (click-through):** CloudFormation → Create stack → Upload a template
file → pick `cloudformation/costdna-scan-role.yaml` → Next. (A quick-create
deep-link requires the template to be S3-hosted; upload is the reliable path.)

Grab the role ARN:

```bash
aws cloudformation describe-stacks --stack-name costdna-scan-role \
  --query "Stacks[0].Outputs" --output table
```

## Option B — Terraform

```bash
cd terraform/scan-role
terraform init
terraform apply                                  # read-only, same-account
# or:
terraform apply -var enable_tag_writeback=true \
                -var 'trusted_principal_arn=arn:aws:iam::111122223333:role/costdna-scanner' \
                -var "external_id=$(openssl rand -hex 16)"
terraform output role_arn
```

## Using the role

The CLI assumes the role through a named AWS profile (the standard boto3
pattern — no special flag). Add to `~/.aws/config`:

```ini
[profile costdna]
role_arn       = arn:aws:iam::<ACCOUNT_ID>:role/CostDNAScanRole
source_profile = default            # a profile with sts:AssumeRole rights
region         = us-east-1
```

Then:

```bash
costdna doctor --aws-profile costdna     # preflight the permissions
costdna scan   --aws-profile costdna     # boto3 assumes the role automatically
```

## Parameters (both templates)

| Parameter | Default | Purpose |
|---|---|---|
| `TrustedPrincipalArn` / `trusted_principal_arn` | account root | Who may assume the role. Set to a specific principal for cross-account. |
| `ExternalId` / `external_id` | (empty) | Confused-deputy mitigation for cross-account/managed-scan. Recommended when the trusted principal is in another account. |
| `EnableTagWriteback` / `enable_tag_writeback` | `false` | Add the scoped write-back grant. Off = strictly read-only. |
| `RoleName` / `role_name` | `CostDNAScanRole` | Role name. |

## Tear down

```bash
aws cloudformation delete-stack --stack-name costdna-scan-role   # Option A
terraform destroy                                                # Option B
```
