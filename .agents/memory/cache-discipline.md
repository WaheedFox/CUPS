---
name: Cache discipline
description: Durable architectural decision for CUPS cache usage.
---

Cache is an optimization, never a source of truth or a reason to widen the first vertical slice. Add it only when a measured performance or multi-process distribution need exists, with explicit invalidation and stale-result rules.

**Why:** The initial CUPS slice can prove resolution and quota behavior directly; inventing cache states before a real need would add failure modes without improving the contract.

**How to apply:** Keep source-of-truth reads in the core path. When cache becomes necessary, define its consistency and invalidation contract before implementing it.