"""Tests for the multi-cloud collectors.

These tests don't talk to live cloud accounts. They mock the SDK layer with
objects that have the exact shapes documented in the cloud SDKs (verified by
introspection of azure-mgmt-resource v25, azure-mgmt-monitor v7,
azure-mgmt-costmanagement v4, google-cloud-logging v3, google-cloud-asset v4)
so the test catches breakage if the collectors deviate from the contract.

These don't replace live-account validation but they catch the obvious shape
errors that would surface on first contact with a real account.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from costdna.collectors._base import PROVIDERS, get_provider


# ------------------------------------------------------------------
# Provider registry
# ------------------------------------------------------------------

def test_all_providers_registered():
    aws = get_provider("aws")
    azure = get_provider("azure")
    gcp = get_provider("gcp")
    assert aws.name == "aws"
    assert azure.name == "azure"
    assert gcp.name == "gcp"


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="unknown cloud provider"):
        get_provider("digitalocean")


# ------------------------------------------------------------------
# Azure
# ------------------------------------------------------------------

def _fake_azure_resource(name, type_, location="eastus", principal_id=None):
    """Mimics the shape of GenericResourceExpanded from azure-mgmt-resource."""
    r = MagicMock()
    r.name = name
    r.type = type_
    r.location = location
    r.created_time = datetime(2025, 1, 15, tzinfo=timezone.utc)
    if principal_id:
        r.identity = MagicMock()
        r.identity.principal_id = principal_id
    else:
        r.identity = None
    return r


def _fake_azure_event(resource_id, caller, op_value, when):
    """Mimics EventData from azure-mgmt-monitor."""
    e = MagicMock()
    e.resource_id = resource_id
    e.caller = caller   # plain string per actual Azure SDK
    e.operation_name = MagicMock()
    e.operation_name.value = op_value
    e.event_timestamp = when
    return e


def test_azure_list_resources_extracts_correct_fields():
    """Confirm _list_resources reads the right attributes off GenericResourceExpanded."""
    from costdna.collectors.azure_live import AZURE_TYPE_MAP, _list_resources

    fake_rm_client = MagicMock()
    fake_rm_client.resources.list.return_value = [
        _fake_azure_resource("vm-1", "Microsoft.Compute/virtualMachines",
                             principal_id="abc123"),
        _fake_azure_resource("db-1", "Microsoft.Sql/servers/databases"),
        _fake_azure_resource("orphan", "Microsoft.SomeUnknown/thing"),  # filtered out
        _fake_azure_resource("bucket", "Microsoft.Storage/storageAccounts"),
    ]
    fake_sdk = {"ResourceManagementClient": MagicMock(return_value=fake_rm_client)}

    out = _list_resources(fake_sdk, MagicMock(), "sub-id-123")

    # 3 supported types, "orphan" dropped
    assert len(out) == 3
    # Type mapping
    assert {r["resource_type"] for r in out} == {"ec2", "rds", "s3"}
    # Field extraction
    vm = next(r for r in out if r["resource_id"] == "vm-1")
    assert vm["resource_type"] == "ec2"   # virtualMachines -> ec2
    assert vm["iam_role"] == "abc123"
    assert vm["vpc_cidr"] == "eastus"
    assert vm["created_at"].startswith("2025-01-15")
    # The expand kwarg was passed (if dropped, created_time is None)
    fake_rm_client.resources.list.assert_called_with(expand="createdTime,changedTime")


def test_azure_activity_log_handles_real_event_shape():
    """ev.caller is a plain string; ev.operation_name has a .value attr."""
    from costdna.collectors.azure_live import _activity_log

    fake_monitor = MagicMock()
    fake_monitor.activity_logs.list.return_value = [
        _fake_azure_event(
            resource_id=("/subscriptions/sub/resourceGroups/rg/providers/"
                         "Microsoft.Compute/virtualMachines/vm-1"),
            caller="alice@example.com",
            op_value="Microsoft.Compute/virtualMachines/start/action",
            when=datetime(2025, 5, 1, 10, 30, tzinfo=timezone.utc),
        ),
        _fake_azure_event(
            resource_id="/some/other/path/that/we/dont/own",
            caller="bot",
            op_value="X.Y/op",
            when=datetime(2025, 5, 1, tzinfo=timezone.utc),
        ),
    ]
    fake_sdk = {"MonitorManagementClient": MagicMock(return_value=fake_monitor)}

    rows = _activity_log(fake_sdk, MagicMock(), "sub-id", ["vm-1", "vm-2"], days=7)

    # Only the event scoped to vm-1 matches
    assert len(rows) == 1
    r = rows[0]
    assert r["resource_id"] == "vm-1"
    assert r["user_identity"] == "alice@example.com"
    assert r["iam_role"] == "alice@example.com"
    assert r["event_name"] == "Microsoft.Compute/virtualMachines/start/action"
    assert r["source_account"] == "sub-id"
    assert r["signal_type"] == "cloudtrail_event"


def test_azure_activity_log_handles_none_op_name_and_caller():
    """Defensive: real Azure events sometimes have empty fields."""
    from costdna.collectors.azure_live import _activity_log

    e = MagicMock()
    e.resource_id = "/subscriptions/x/resourceGroups/y/providers/Z/foo/vm-1"
    e.caller = None
    e.operation_name = None
    e.event_timestamp = datetime(2025, 5, 1, tzinfo=timezone.utc)

    fake_monitor = MagicMock()
    fake_monitor.activity_logs.list.return_value = [e]
    fake_sdk = {"MonitorManagementClient": MagicMock(return_value=fake_monitor)}

    rows = _activity_log(fake_sdk, MagicMock(), "sub-id", ["vm-1"], days=7)
    assert len(rows) == 1
    assert rows[0]["user_identity"] == ""   # None -> ""
    assert rows[0]["event_name"] == ""        # None operation_name -> ""


def test_azure_cost_query_uses_typed_models():
    """The SDK rejects raw dicts on v4; ensure we build typed QueryDefinition."""
    from azure.mgmt.costmanagement.models import QueryDefinition

    from costdna.collectors.azure_live import _cost_series

    captured = {}

    def fake_query_usage(scope, parameters):
        captured["scope"] = scope
        captured["parameters"] = parameters
        result = MagicMock()
        result.rows = [[1.23, 20250501, "USD", "/subs/x/res/r/vm-1"]]
        return result

    fake_cm = MagicMock()
    fake_cm.query.usage.side_effect = fake_query_usage
    fake_sdk = {"CostManagementClient": MagicMock(return_value=fake_cm)}

    rows = _cost_series(fake_sdk, MagicMock(), "sub-id", ["vm-1"], days=30)

    # Verify we passed a QueryDefinition (not a dict)
    assert isinstance(captured["parameters"], QueryDefinition)
    assert captured["scope"] == "/subscriptions/sub-id"
    assert len(rows) == 1
    assert rows[0]["resource_id"] == "vm-1"
    assert rows[0]["signal_type"] == "cost"
    assert rows[0]["value"] == 1.23


# ------------------------------------------------------------------
# GCP
# ------------------------------------------------------------------

def _fake_protobuf_audit_payload(method_name, principal_email, resource_name):
    """Mimics google.cloud.audit.AuditLog proto. Has snake_case attrs."""
    p = MagicMock()
    p.method_name = method_name
    p.authentication_info = MagicMock()
    p.authentication_info.principal_email = principal_email
    p.resource_name = resource_name
    return p


def _fake_log_entry(payload, when):
    e = MagicMock()
    e.payload = payload
    e.timestamp = when
    return e


def test_gcp_audit_logs_extracts_protobuf_payload():
    """ProtobufEntry.payload is a proto with snake_case attrs (NOT a dict)."""
    from costdna.collectors.gcp import _audit_logs

    proto = _fake_protobuf_audit_payload(
        method_name="compute.instances.start",
        principal_email="bob@example.com",
        resource_name="projects/p/zones/us-central1-a/instances/inst-1",
    )

    fake_logging_client = MagicMock()
    fake_logging_client.list_entries.return_value = [
        _fake_log_entry(proto, datetime(2025, 5, 1, tzinfo=timezone.utc)),
    ]
    fake_sdk = {"logging": MagicMock(Client=MagicMock(
        return_value=fake_logging_client))}

    rows = _audit_logs(fake_sdk, "proj-id", ["inst-1"], days=7)
    assert len(rows) == 1
    assert rows[0]["event_name"] == "compute.instances.start"
    assert rows[0]["user_identity"] == "bob@example.com"
    assert rows[0]["resource_id"] == "inst-1"


def test_gcp_audit_logs_extracts_struct_payload():
    """StructEntry.payload is a dict with camelCase keys."""
    from costdna.collectors.gcp import _audit_logs

    payload_dict = {
        "methodName": "storage.buckets.create",
        "authenticationInfo": {"principalEmail": "carol@example.com"},
        "resourceName": "projects/p/buckets/bucket-1",
    }

    fake_logging_client = MagicMock()
    fake_logging_client.list_entries.return_value = [
        _fake_log_entry(payload_dict, datetime(2025, 5, 1, tzinfo=timezone.utc)),
    ]
    fake_sdk = {"logging": MagicMock(Client=MagicMock(
        return_value=fake_logging_client))}

    rows = _audit_logs(fake_sdk, "proj-id", ["bucket-1"], days=7)
    assert len(rows) == 1
    assert rows[0]["event_name"] == "storage.buckets.create"
    assert rows[0]["user_identity"] == "carol@example.com"


def test_gcp_audit_logs_skips_unknown_resources():
    from costdna.collectors.gcp import _audit_logs

    proto = _fake_protobuf_audit_payload(
        method_name="x.y", principal_email="z",
        resource_name="projects/p/buckets/different-bucket",
    )
    fake_logging_client = MagicMock()
    fake_logging_client.list_entries.return_value = [
        _fake_log_entry(proto, datetime(2025, 5, 1, tzinfo=timezone.utc)),
    ]
    fake_sdk = {"logging": MagicMock(Client=MagicMock(
        return_value=fake_logging_client))}

    rows = _audit_logs(fake_sdk, "proj-id", ["bucket-1"], days=7)
    assert len(rows) == 0   # different-bucket doesn't match bucket-1


def test_gcp_list_assets_filters_by_known_types():
    """ContentType.RESOURCE is enum value 1; asset_types filter excludes
    types not in GCP_TYPE_MAP."""
    from costdna.collectors.gcp import GCP_TYPE_MAP, _list_assets

    fake_asset = MagicMock()
    fake_asset.asset_type = "compute.googleapis.com/Instance"
    fake_asset.name = ("//compute.googleapis.com/projects/p/zones/"
                        "us-central1-a/instances/inst-1")
    fake_asset.resource = MagicMock()
    fake_asset.resource.location = "us-central1-a"
    fake_asset.resource.data = {"serviceAccount": "sa@p.iam.gserviceaccount.com"}
    fake_asset.update_time = datetime(2025, 1, 15, tzinfo=timezone.utc)

    fake_client = MagicMock()
    fake_client.list_assets.return_value = [fake_asset]

    captured = {}

    def asset_service_client_ctor():
        return fake_client
    fake_asset_service = MagicMock()
    fake_asset_service.AssetServiceClient.side_effect = lambda: fake_client

    class _ContentType:
        RESOURCE = 1
    fake_asset_service.ContentType = _ContentType

    fake_sdk = {"asset_v1": fake_asset_service}

    out = _list_assets(fake_sdk, "proj-id")
    assert len(out) == 1
    r = out[0]
    assert r["resource_type"] == "ec2"   # Instance -> ec2
    assert r["resource_id"] == "inst-1"
    assert r["iam_role"] == "sa@p.iam.gserviceaccount.com"
    assert r["vpc_cidr"] == "us-central1-a"
    assert r["created_at"].startswith("2025-01-15")
