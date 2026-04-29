# Outbox Pattern

**Layer:** 3 — Integration / Distributed Systems

**What it is:** Guarantees that an event is published if and only if the database transaction is committed. Writes the event to an `outbox` table in the same transaction, then a worker publishes and removes it.

**When to use:**
- Business event must be published together with persistence (e.g.: UserCreated must go to n8n)
- At-least-once delivery guarantee for events
- Avoid inconsistent state (database saved but event not sent)

**When NOT to use:**
- Single-node system without messaging
- Event can be lost without issue

**Flow:**
```
BEGIN TRANSACTION
  INSERT INTO users (data)
  INSERT INTO outbox (event: 'UserCreated', payload: user)
COMMIT

// Separate worker (asynchronous):
LOOP:
  events = SELECT * FROM outbox WHERE published = false
  FOR event IN events:
    publish(event)
    UPDATE outbox SET published = true WHERE id = event.id
```

**Cost:** Extra table. Extra worker. Delivery latency (eventual consistency).

**Related:** Idempotent Consumer (the consumer must handle duplicates)
