# CQRS — Command Query Responsibility Segregation

**Layer:** 4 — Architectural

**What it is:** Separates write operations (Commands, which change state) from read operations (Queries, which return data). Each side can have its own model and database.

**When to use:**
- Read and write have very different volumes
- The read model needs to be denormalized for performance
- Dashboards and reports with complex queries
- Independent scalability of read and write

**When NOT to use:**
- Simple CRUD where read = write
- Small team without experience — high complexity
- Eventual consistency is unacceptable

**Minimal interface:**
```
// Write side
CreateOrderCommand: { customerId, items, total }
  → handler: validates, persists, emits OrderCreated event

// Read side (denormalized, optimized for query)
OrderSummaryQuery: { orderId } → OrderSummaryView
  → handler: reads from read-store (can be Redis, Elasticsearch, materialized view)
```

**Cost:** Eventual consistency between write and read. Two models to maintain.

**Related:** Event Sourcing (frequently combined), State Machine (for the write model)
