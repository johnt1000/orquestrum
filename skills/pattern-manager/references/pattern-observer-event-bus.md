# Observer / Event Bus

**Layer:** 2 — Behavioral

**What it is:** Producer emits events without knowing who consumes them. Consumers register interest in specific events.

**When to use:**
- Business side effects (e.g.: user created → send email + create audit log + notify slack)
- Decouple modules that should not know each other
- n8n workflows triggered by business events
- Real-time notifications

**When NOT to use:**
- Simple linear flow where order matters and the producer needs to know the result
- When implicit coupling creates more confusion than explicit coupling

**Minimal interface:**
```
EventBus:
  publish(event: Event): void
  subscribe(eventType, handler: (event) => void): void

// Producer does not know consumers
UserService:
  createUser(data):
    user = repo.save(data)
    eventBus.publish(UserCreated { user })
    return user

// Independent consumers
EmailService: subscribe(UserCreated, sendWelcomeEmail)
AuditService: subscribe(UserCreated, createAuditLog)
```

**Cost:** Flow is hard to trace. Execution order not guaranteed. Complex debugging.

**Related:** Command (when the event must be executed reliably), Outbox (when delivery needs to be guaranteed)
