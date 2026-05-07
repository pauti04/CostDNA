"""Provider abstraction for live cloud collectors.

CostDNA's pipeline (features → graph → GNN → agent) is cloud-agnostic.
Only the collector layer is cloud-specific. This module defines the
interface every cloud provider must satisfy so the rest of the project
doesn't care whether signals come from CloudTrail, Azure Activity Log,
or Cloud Audit Logs.

Adding a new cloud means:
  1. Implement `CloudProvider` for that cloud
  2. Register it in `PROVIDERS`
  3. Pass `--cloud <name>` to `costdna scan`

Returned shapes:
  metadata  pd.DataFrame[resource_id, resource_type, iam_role, vpc_cidr,
                          created_at, team?]
  signals   pd.DataFrame[resource_id, signal_type, user_identity, iam_role,
                          event_name, source_account, value, timestamp]
  flows     pd.DataFrame[src, dst, bytes]   (may be empty)
  deploys   pd.DataFrame[team, repo, commit, timestamp]   (may be empty;
            populated by separate sync from git/CI, not the cloud API)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd


@dataclass
class CollectionResult:
    """Everything a single cloud-account scan returns."""
    metadata: pd.DataFrame
    signals: pd.DataFrame
    flows: pd.DataFrame
    deploys: pd.DataFrame


class CloudProvider(ABC):
    """Live cloud collector interface.

    Each cloud (AWS, Azure, GCP) implements this. The shape of returned
    DataFrames is identical across providers so the downstream pipeline
    (features.py, graph.py, model.py) doesn't need to know which cloud
    the data came from.
    """

    name: str  # canonical short name: "aws", "azure", "gcp"

    @abstractmethod
    def doctor(self, *, profile: str | None, region: str) -> dict:
        """Preflight: returns {check_name: (status, detail)} dict.

        Verifies credentials, required permissions, audit-log availability,
        cost-API availability, etc. before a real scan.
        """

    @abstractmethod
    def collect(
        self,
        *,
        profile: str | None,
        region: str,
        days: int,
    ) -> CollectionResult:
        """Pull metadata + signals + flows for the requested time window."""


# Registry — populated by each provider module on import.
PROVIDERS: dict[str, CloudProvider] = {}


def register(name: str):
    """Decorator: registers a provider class under the given name."""
    def _wrap(cls):
        PROVIDERS[name] = cls()
        cls.name = name
        return cls
    return _wrap


def get_provider(name: str) -> CloudProvider:
    """Look up a provider by name. Raises with a helpful message if missing."""
    if name not in PROVIDERS:
        # Lazy-load known providers — they self-register on import.
        if name == "aws":
            from costdna.collectors import aws  # noqa: F401
        elif name == "azure":
            from costdna.collectors import azure_live  # noqa: F401
        elif name == "gcp":
            from costdna.collectors import gcp  # noqa: F401
    if name not in PROVIDERS:
        available = ", ".join(sorted(PROVIDERS)) or "(none loaded)"
        raise ValueError(
            f"unknown cloud provider {name!r}. Available: {available}. "
            f"For Azure: pip install 'costdna[azure]'. "
            f"For GCP:   pip install 'costdna[gcp]'."
        )
    return PROVIDERS[name]
