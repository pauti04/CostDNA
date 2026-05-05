"""CostDNA — behavioral fingerprinting for AWS cost attribution."""

__version__ = "0.2.0"

# Four teams in the synthetic environment. The "platform" team owns shared
# infra (logging, secrets, CI runners) — its resources see traffic from every
# other team, which makes them the hardest cases for behavioral attribution.
TEAMS = ("backend", "data", "ml", "platform")
