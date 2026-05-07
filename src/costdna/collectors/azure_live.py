"""Live Azure subscription collector.

DIFFERENT from `azure.py` (which is the Microsoft Public Dataset benchmark
loader). This module talks to a live Azure subscription via the management
plane: enumerates resources, queries the Activity Log, pulls Cost Management
data.

Status: implementation follows the Azure SDK for Python v1.x patterns
documented at https://learn.microsoft.com/en-us/python/api/overview/azure/.
**Untested against a live Azure subscription** as of the current commit —
needs validation by anyone with access. Once validated, update the README
"Cloud support" matrix and remove this notice.

Authentication uses `DefaultAzureCredential` which tries (in order):
  1. Environment variables (AZURE_CLIENT_ID/SECRET/TENANT_ID)
  2. Workload Identity (in AKS)
  3. Managed Identity (in an Azure VM)
  4. Azure CLI (`az login`)
  5. Azure PowerShell

For a developer laptop the easiest is `az login`.

Required Azure RBAC role on the target subscription: **Reader** is enough
for collection. To write tags back (via `costdna apply`), you'd need
**Tag Contributor** in addition.

Permissions checklist:
  - Microsoft.Resources/subscriptions/resources/read
  - Microsoft.Insights/eventtypes/values/read       (Activity Log)
  - Microsoft.CostManagement/query/read
  - Microsoft.Network/networkSecurityGroups/read    (NSG flow logs)

Install: `pip install 'costdna[azure]'` adds the required SDK extras.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pandas as pd

from costdna.collectors._base import (CloudProvider, CollectionResult,
                                       register)

log = logging.getLogger(__name__)


def _import_azure_sdk():
    """Lazy import. Raises a friendly error if the [azure] extras aren't
    installed. Avoids forcing every CostDNA install to pull the Azure SDK."""
    try:
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.costmanagement import CostManagementClient
        from azure.mgmt.monitor import MonitorManagementClient
        from azure.mgmt.resource import ResourceManagementClient
        from azure.mgmt.network import NetworkManagementClient
    except ImportError as e:
        raise ImportError(
            "Azure live collector requires the [azure] extras. "
            "Install: pip install 'costdna[azure]'\n"
            f"Underlying error: {e}"
        ) from e
    return {
        "DefaultAzureCredential": DefaultAzureCredential,
        "CostManagementClient": CostManagementClient,
        "MonitorManagementClient": MonitorManagementClient,
        "ResourceManagementClient": ResourceManagementClient,
        "NetworkManagementClient": NetworkManagementClient,
    }


# Map Azure resource types to CostDNA's resource_type taxonomy. Keep this
# narrow — only the types we actually have features for.
AZURE_TYPE_MAP = {
    "Microsoft.Compute/virtualMachines": "ec2",
    "Microsoft.Compute/virtualMachineScaleSets": "ec2",
    "Microsoft.Sql/servers/databases": "rds",
    "Microsoft.DBforPostgreSQL/flexibleServers": "rds",
    "Microsoft.DBforMySQL/flexibleServers": "rds",
    "Microsoft.Web/sites": "lambda",       # Azure Functions
    "Microsoft.Storage/storageAccounts": "s3",
}


def _list_resources(sdk, credential, subscription_id: str) -> list[dict]:
    """Enumerate every Azure resource that maps to a CostDNA resource type.

    Uses `expand=createdTime,changedTime` to pull `GenericResourceExpanded`
    instead of the bare `GenericResource` (the latter doesn't have a
    `created_time` attribute). Verified against azure-mgmt-resource v25.
    """
    rm = sdk["ResourceManagementClient"](credential, subscription_id)
    out = []
    for r in rm.resources.list(expand="createdTime,changedTime"):
        # r.type looks like "Microsoft.Compute/virtualMachines"
        rtype = AZURE_TYPE_MAP.get(r.type)
        if rtype is None:
            continue
        # Identity binding ≈ AWS IAM role. r.identity is a ResourceIdentity
        # object on resources with managed identity, None otherwise.
        identity = getattr(r, "identity", None)
        principal_id = (getattr(identity, "principal_id", "") or "") if identity else ""
        # created_time only exists on GenericResourceExpanded (when expand
        # arg includes 'createdTime' — see resources.list call above).
        created_at = ""
        ct = getattr(r, "created_time", None)
        if ct is not None:
            try:
                created_at = ct.isoformat()
            except AttributeError:
                created_at = str(ct)
        out.append({
            "resource_id": r.name,             # bucket/instance/db name
            "resource_type": rtype,
            "iam_role": principal_id,           # managed identity principal
            "vpc_cidr": getattr(r, "location", "") or "",
            "created_at": created_at,
        })
    return out


def _activity_log(sdk, credential, subscription_id: str,
                  resource_ids: list[str], days: int) -> list[dict]:
    """Pull Activity Log events scoped to the provided resources.

    Azure Monitor's eventtypes/management API is the equivalent of
    CloudTrail Lookup Events. We query with `eventTimestamp ge <window>`
    and post-filter to events whose `resourceId` matches ours.
    """
    monitor = sdk["MonitorManagementClient"](credential, subscription_id)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    filter_str = (
        f"eventTimestamp ge '{start.isoformat()}' and "
        f"eventTimestamp le '{end.isoformat()}'"
    )

    rid_set = {r.lower() for r in resource_ids}
    rows = []
    for ev in monitor.activity_logs.list(filter=filter_str):
        # ev.resource_id is the full ARM ID; ev.caller is a plain string;
        # ev.operation_name is a LocalizableString with a .value attr.
        # Verified against azure-mgmt-monitor v7 EventData model.
        full = (ev.resource_id or "").lower()
        match = next((r for r in rid_set if r and r in full), None)
        if not match:
            continue
        caller = ev.caller or ""   # always a string
        op = ev.operation_name
        op_name = getattr(op, "value", "") if op else ""
        rows.append({
            "resource_id": match,
            "signal_type": "cloudtrail_event",
            "user_identity": caller,
            "iam_role": caller,
            "event_name": op_name,
            "source_account": subscription_id,
            "value": 1.0,
            "timestamp": (ev.event_timestamp.isoformat()
                          if ev.event_timestamp else ""),
        })
    return rows


def _cost_series(sdk, credential, subscription_id: str,
                  resource_ids: list[str], days: int) -> list[dict]:
    """Cost Management `query` API, grouped by ResourceId.

    Returns one cost row per (resource, day). Daily granularity (Azure CM
    doesn't expose hourly without a separate enrollment-export pipeline).
    Uses the typed `QueryDefinition`/`QueryDataset`/etc. models — the SDK
    rejects raw dicts on v4+.
    """
    from azure.mgmt.costmanagement.models import (
        QueryAggregation, QueryDataset, QueryDefinition, QueryGrouping,
        QueryTimePeriod,
    )

    cm = sdk["CostManagementClient"](credential)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    scope = f"/subscriptions/{subscription_id}"

    query = QueryDefinition(
        type="Usage",
        timeframe="Custom",
        time_period=QueryTimePeriod(from_property=start, to=end),
        dataset=QueryDataset(
            granularity="Daily",
            aggregation={
                "totalCost": QueryAggregation(name="PreTaxCost", function="Sum"),
            },
            grouping=[QueryGrouping(type="Dimension", name="ResourceId")],
        ),
    )
    try:
        result = cm.query.usage(scope=scope, parameters=query)
    except Exception as e:
        log.warning("Azure cost query failed: %s", e)
        return []

    rid_set = {r.lower() for r in resource_ids}
    rows = []
    for row in (getattr(result, "rows", None) or []):
        # Row layout depends on the columns returned by the query. With the
        # grouping above, expect: [cost, day_int, currency, resource_id_full]
        if len(row) < 4:
            continue
        cost, day_int, _currency, rid_full = row[0], row[1], row[2], row[3]
        rid_short = str(rid_full).split("/")[-1].lower()
        if rid_short not in rid_set:
            continue
        day_str = str(day_int)
        ts = f"{day_str[:4]}-{day_str[4:6]}-{day_str[6:8]}T00:00:00+00:00"
        rows.append({
            "resource_id": rid_short,
            "signal_type": "cost",
            "user_identity": "",
            "iam_role": "",
            "event_name": "",
            "source_account": subscription_id,
            "value": float(cost),
            "timestamp": ts,
        })
    return rows


def _nsg_flow_logs(sdk, credential, subscription_id: str) -> pd.DataFrame:
    """NSG flow logs ≈ AWS VPC Flow Logs. Schema: src, dst, bytes.

    Azure's flow logs are written to a storage account (NetworkWatcher);
    pulling them parsed is non-trivial without the storage SAS token. For
    now this collector returns empty — the GNN handles missing flow data
    gracefully (graph still has IAM and resource-type edges).
    """
    return pd.DataFrame(columns=["src", "dst", "bytes"])


@register("azure")
class AzureProvider(CloudProvider):
    """Live Azure subscription scanner.

    UNTESTED against a live subscription as of this commit. SDK calls follow
    documented patterns from `azure-mgmt-resource`, `azure-mgmt-monitor`,
    and `azure-mgmt-costmanagement`. Validate against your subscription
    before relying on output.

    `region` argument is interpreted as the Azure subscription_id (Azure
    has no concept of "region" at the management-plane level — its
    "subscription" is the closest equivalent to AWS's "account-region"
    pair for billing scope).
    """

    def doctor(self, *, profile, region):
        """region == subscription_id for Azure."""
        sdk = _import_azure_sdk()
        cred = sdk["DefaultAzureCredential"]()
        out = {}
        try:
            rm = sdk["ResourceManagementClient"](cred, region)
            list(rm.resources.list(top=1))
            out["Auth + resource list"] = ("ok", "reachable as default credential")
        except Exception as e:
            out["Auth + resource list"] = ("fail", f"{e}")
        try:
            sdk["MonitorManagementClient"](cred, region)
            out["Activity Log client"] = ("ok", "constructed")
        except Exception as e:
            out["Activity Log client"] = ("fail", f"{e}")
        try:
            sdk["CostManagementClient"](cred)
            out["Cost Management client"] = ("ok", "constructed")
        except Exception as e:
            out["Cost Management client"] = ("fail", f"{e}")
        return out

    def collect(self, *, profile, region, days):
        sdk = _import_azure_sdk()
        cred = sdk["DefaultAzureCredential"]()
        sub_id = region   # see docstring

        log.info("[azure] enumerating resources in subscription=%s", sub_id)
        resources = _list_resources(sdk, cred, sub_id)
        log.info("[azure] found %d resources", len(resources))

        if not resources:
            empty = pd.DataFrame()
            return CollectionResult(
                metadata=empty, signals=empty,
                flows=pd.DataFrame(columns=["src", "dst", "bytes"]),
                deploys=pd.DataFrame(),
            )

        rids = [r["resource_id"] for r in resources]
        log.info("[azure] querying activity log (last %d days)", days)
        rows = _activity_log(sdk, cred, sub_id, rids, days)
        log.info("[azure] activity log: %d events matched our resources", len(rows))

        try:
            rows.extend(_cost_series(sdk, cred, sub_id, rids, days))
        except Exception as e:
            log.warning("[azure] cost series failed: %s", e)

        signals = pd.DataFrame(rows)
        if not signals.empty:
            signals["timestamp"] = pd.to_datetime(
                signals["timestamp"], format="ISO8601", utc=True,
            )
        metadata = pd.DataFrame(resources)
        flows = _nsg_flow_logs(sdk, cred, sub_id)
        deploys = pd.DataFrame(columns=["team", "signal_type", "repo",
                                         "commit", "timestamp"])

        return CollectionResult(
            metadata=metadata, signals=signals, flows=flows, deploys=deploys,
        )
