# Hexagonal Architecture (Ports & Adapters)

**Layer:** 4 — Architectural

**What it is:** Isolates the business core (domain) from frameworks, databases, and external interfaces. The domain defines Ports (interfaces); Adapters implement those interfaces for each technology.

**When to use:**
- Any project with longevity > 1 year
- Business logic that needs to be tested without infrastructure
- Multiple drivers (HTTP + CLI + worker) for the same domain

**Structure:**
```
Domain (core):
  - Entities, Use Cases, Ports (interfaces)
  - Zero external dependencies

Adapters (edge):
  - Driving: HTTP Controller, CLI, Worker → calls Use Cases
  - Driven: Repository impl, Email impl, Queue impl → called by Use Cases

Ports:
  - IUserRepository (driven port)
  - IEmailNotifier (driven port)
```

**Cost:** More complex folder structure. Learning curve. Dependency injection mandatory.

**Related:** Repository (for data driven ports), Adapter (for external service driven ports)
