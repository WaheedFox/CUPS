"""Entitlement value types used throughout CUPS.

Three Entitlement types (from DOMAIN.md):
  Boolean        — feature on/off          e.g. atlas_access: true/false
  Numeric        — quantitative limit      e.g. max_projects_total: 10
  CapabilityTier — multi-level access      e.g. inspector_level: none|basic|advanced

ResolvedEntitlements is what Runtime consumes — never the raw Subscription.
"""

from __future__ import annotations

from typing import Union

# The possible value types for any Entitlement
EntitlementValue = Union[bool, int, str]

# What the Entitlement Engine produces and Runtime consumes
ResolvedEntitlements = dict[str, EntitlementValue]
