"""Live GCP project collector.

Talks to a live GCP project: enumerates resources via Cloud Asset Inventory,
queries Cloud Audit Logs (via Cloud Logging), pulls Cloud Billing data.

Status: implementation follows the documented Google Cloud Python SDK
patterns. **Untested against a live GCP project** as of the current commit
— needs validation by anyone with access. Once validated, update the README
"Cloud support" matrix and remove this notice.

Authentication uses Application Default Credentials (ADC) which tries:
  1. GOOGLE_APPLICATION_CREDENTIALS env var (service account JSON)
  2. gcloud CLI (`gcloud auth application-default login`)
  3. Workload Identity (in GKE)
  4. Compute Engine metadata server

For a developer laptop the easiest is `gcloud auth application-default login`.

Required IAM roles on the target project:
  - roles/cloudasset.viewer        (Cloud Asset Inventory)
  - roles/logging.viewer            (Cloud Audit Logs)
  - roles/billing.viewer            (Cloud Billing)
  - roles/compute.viewer            (VPC flow logs metadata)

Install: `pip install 'costdna[gcp]'` adds the required SDK extras.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pandas as pd

from costdna.collectors._base import (CloudProvider, CollectionResult,
                                       register)

log = logging.getLogger(__name__)


def _import_gcp_sdk():
    """Lazy import. Friendly error if [gcp] extras aren't installed."""
    try:
        from google.cloud import asset_v1
        from google.cloud import logging as gcp_logging
        from google.cloud import billing_v1
        from google.auth import default as google_auth_default
    except ImportError as e:
        raise ImportError(
            "GCP live collector requires the [gcp] extras. "
            "Install: pip install 'costdna[gcp]'\n"
            f"Underlying error: {e}"
        ) from e
    return {
        "asset_v1": asset_v1,
        "logging": gcp_logging,
        "billing_v1": billing_v1,
        "auth_default": google_auth_default,
    }


# Map GCP asset types to CostDNA's resource_type taxonomy.
GCP_TYPE_MAP = {
    "compute.googleapis.com/Instance": "ec2",
    "sqladmin.googleapis.com/Instance": "rds",
    "cloudfunctions.googleapis.com/CloudFunction": "lambda",
    "run.googleapis.com/Service": "lambda",     # Cloud Run = Functions++
    "storage.googleapis.com/Bucket": "s3",
}


def _list_assets(sdk, project_id: str) -> list[dict]:
    """Cloud Asset Inventory: enumerate every resource type CostDNA cares
    about in a single API call. Much cleaner than AWS's per-service describe."""
    client = sdk["asset_v1"].AssetServiceClient()
    parent = f"projects/{project_id}"

    out = []
    try:
        for asset in client.list_assets(
            request={"parent": parent,
                     "asset_types": list(GCP_TYPE_MAP.keys()),
                     "content_type": sdk["asset_v1"].ContentType.RESOURCE},
        ):
            rtype = GCP_TYPE_MAP.get(asset.asset_type)
            if rtype is None:
                continue
            # asset.name = "//compute.googleapis.com/projects/X/zones/Y/instances/Z"
            # short name is the last segment
            name = asset.name.split("/")[-1]
            sa = ""
            if asset.resource and asset.resource.data:
                sa = (asset.resource.data.get("serviceAccount", "")
                      or asset.resource.data.get("service_account", "")
                      or "")
            location = (asset.resource.location
                        if asset.resource and asset.resource.location else "")
            out.append({
                "resource_id": name,
                "resource_type": rtype,
                "iam_role": sa,           # service account ≈ AWS IAM role
                "vpc_cidr": location,      # GCP region for graph grouping
                "created_at": (asset.update_time.isoformat()
                                if asset.update_time else ""),
            })
    except Exception as e:
        log.warning("[gcp] list_assets failed: %s", e)

    return out


def _audit_logs(sdk, project_id: str, resource_ids: list[str],
                days: int) -> list[dict]:
    """Cloud Audit Logs ≈ AWS CloudTrail.

    We query logName=cloudaudit.googleapis.com%2Factivity for the last N
    days, then post-filter to entries whose resource name matches ours.
    """
    client = sdk["logging"].Client(project=project_id)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    flt = (
        f'logName="projects/{project_id}/logs/cloudaudit.googleapis.com%2Factivity" '
        f'AND timestamp>="{start.isoformat()}"'
    )

    rid_set = {r.lower() for r in resource_ids}
    rows = []
    try:
        for entry in client.list_entries(filter_=flt):
            payload = entry.payload or {}
            method_name = payload.get("methodName", "") or ""
            principal = (
                payload.get("authenticationInfo", {})
                       .get("principalEmail", "")
                or ""
            )
            # The resource name appears in payload.resourceName as
            # "projects/.../instances/{name}" or similar.
            resource_name = (payload.get("resourceName", "") or "").lower()
            match = next((r for r in rid_set if r and r in resource_name), None)
            if not match:
                continue
            rows.append({
                "resource_id": match,
                "signal_type": "cloudtrail_event",
                "user_identity": principal,
                "iam_role": principal,        # GCP collapses this distinction
                "event_name": method_name,
                "source_account": project_id,
                "value": 1.0,
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else "",
            })
    except Exception as e:
        log.warning("[gcp] audit log query failed: %s", e)
    return rows


def _cost_series(sdk, project_id: str, resource_ids: list[str],
                  days: int) -> list[dict]:
    """Cloud Billing API returns monthly aggregates; for per-resource daily
    cost you typically need the BigQuery billing export. We do best-effort
    with the API and document the limitation.

    Returns empty if billing is not exported / not accessible.
    """
    # TODO: query the BigQuery billing-export table if configured.
    # gcloud beta billing accounts list  →  ACCOUNT_ID
    # SELECT service.description, sku.description, usage_start_time, cost
    # FROM `project.dataset.gcp_billing_export_*`
    # WHERE _PARTITIONTIME between …
    # For now return empty so the rest of the pipeline still runs.
    return []


@register("gcp")
class GCPProvider(CloudProvider):
    """Live GCP project scanner.

    UNTESTED against a live project as of this commit. Validate before
    relying on output.

    `region` argument is interpreted as the GCP project_id (GCP's billing
    + audit boundary is the project, not a region; resources have their
    own region attribute carried in `vpc_cidr`).
    """

    def doctor(self, *, profile, region):
        sdk = _import_gcp_sdk()
        out = {}
        try:
            creds, project = sdk["auth_default"]()
            out["ADC credentials"] = ("ok", f"loaded for project={project}")
        except Exception as e:
            out["ADC credentials"] = ("fail", f"{e}")
        try:
            client = sdk["asset_v1"].AssetServiceClient()
            list(client.list_assets(
                request={"parent": f"projects/{region}",
                         "page_size": 1},
            ))
            out["Cloud Asset Inventory"] = ("ok", "reachable")
        except Exception as e:
            out["Cloud Asset Inventory"] = ("fail", f"{e}")
        try:
            sdk["logging"].Client(project=region)
            out["Cloud Logging"] = ("ok", "client constructed")
        except Exception as e:
            out["Cloud Logging"] = ("fail", f"{e}")
        return out

    def collect(self, *, profile, region, days):
        sdk = _import_gcp_sdk()
        project_id = region   # see docstring

        log.info("[gcp] listing assets in project=%s", project_id)
        resources = _list_assets(sdk, project_id)
        log.info("[gcp] found %d resources", len(resources))

        if not resources:
            empty = pd.DataFrame()
            return CollectionResult(
                metadata=empty, signals=empty,
                flows=pd.DataFrame(columns=["src", "dst", "bytes"]),
                deploys=pd.DataFrame(),
            )

        rids = [r["resource_id"] for r in resources]
        rows = _audit_logs(sdk, project_id, rids, days)
        rows.extend(_cost_series(sdk, project_id, rids, days))

        signals = pd.DataFrame(rows)
        if not signals.empty:
            signals["timestamp"] = pd.to_datetime(
                signals["timestamp"], format="ISO8601", utc=True,
            )
        metadata = pd.DataFrame(resources)
        flows = pd.DataFrame(columns=["src", "dst", "bytes"])
        deploys = pd.DataFrame(columns=["team", "signal_type", "repo",
                                         "commit", "timestamp"])

        return CollectionResult(
            metadata=metadata, signals=signals, flows=flows, deploys=deploys,
        )
