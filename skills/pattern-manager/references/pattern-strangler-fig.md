# Strangler Fig

**Layer:** 4 — Architectural

**What it is:** Incremental migration of a legacy system. New features are built in the new system; the legacy is gradually "strangled" until it can be shut down.

**When to use:**
- Onboarding an existing project (phase -1 of the pipeline)
- Rewriting a production system without downtime
- Gradual modernization of a monolith

**Flow:**
```
Phase 1: Proxy in front of EVERYTHING → routes to Legacy
Phase 2: New feature X → built in New → Proxy routes X to New, rest to Legacy
Phase 3: Feature Y migrated → Proxy routes Y to New
...
Phase N: All traffic in New → Legacy shut down
```

**Cost:** Period of coexistence of both systems. Data synchronization between them.

**Related:** Adapter (for compatibility between legacy and new interfaces), Anti-Corruption Layer (protection against legacy model leakage)
