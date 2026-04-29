# State Machine

**Layer:** 2 — Behavioral

**What it is:** An object with well-defined states and explicit transitions between them. Makes invalid transitions impossible.

**When to use:**
- Entity with a complex lifecycle (Order: draft → confirmed → paid → shipped → delivered)
- Approval workflow with multiple steps
- Protocol connections (disconnected → connecting → connected → error)

**When NOT to use:**
- Entity with only 2 states (active/inactive — use boolean)
- States are just independent flags without transitions between them

**Minimal interface:**
```
States: DRAFT | CONFIRMED | PAID | SHIPPED | DELIVERED | CANCELLED

Transitions:
  DRAFT      → CONFIRMED  (on: confirm)
  DRAFT      → CANCELLED  (on: cancel)
  CONFIRMED  → PAID       (on: paymentReceived)
  PAID       → SHIPPED    (on: ship)
  SHIPPED    → DELIVERED  (on: deliver)

Order:
  currentState: State
  transition(event):
    if transition not allowed: throw InvalidTransitionError
    currentState = newState
```

**Cost:** More initial code. Worth it when the number of states > 3 with transitions.

**Related:** Event Sourcing (when transitions must be persisted as history)
