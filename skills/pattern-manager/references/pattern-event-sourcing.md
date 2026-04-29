# Event Sourcing

**Layer:** 4 — Architectural

**What it is:** Entity state is derived from an immutable sequence of events. Never overwrites — only appends events. Current state = replay of all events.

**When to use:**
- Complete history of changes is a requirement (audit, compliance, LGPD — right of access)
- Undo/redo is required
- Debugging complex state
- Combined with CQRS in event-driven systems

**When NOT to use:**
- High-frequency events without history requirement (telemetry metrics)
- Team without experience — high learning curve
- Read performance is critical without projection infrastructure

**Flow:**
```
// Write
events = [
  UserRegistered { id, email, timestamp },
  EmailVerified { id, timestamp },
  SubscriptionStarted { id, plan, timestamp }
]
eventStore.append(userId, events)

// Read (replay)
user = eventStore.replay(userId)
  .reduce(initialState, applyEvent)
// user.status = 'subscribed'
```

**Cost:** Infrastructure complexity. Snapshots required for performance with long histories. Eventual consistency with read models.

**Related:** CQRS (reading via projections), State Machine (to validate event transitions)
