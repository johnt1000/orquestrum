# Idempotent Consumer

**Layer:** 3 — Integration / Distributed Systems

**What it is:** Guarantees that processing the same event/message multiple times has the same effect as processing it once. Required for systems with retry and at-least-once delivery.

**When to use:**
- Any worker that consumes events or webhooks (may receive duplicates)
- After implementing Outbox or Retry
- Payment operations, resource creation

**Typical implementation:**
```
// Before processing, check if already processed
processEvent(event):
  if processedEvents.contains(event.id):
    return  // silent skip — already processed
  
  // process...
  
  processedEvents.add(event.id)
```

**Cost:** Storage of processed IDs (Redis, DB table). TTL required for cleanup.

**Related:** Outbox (produces events with unique IDs), Retry (reprocesses events)
