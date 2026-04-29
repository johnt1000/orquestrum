# Saga

**Layer:** 3 — Integration / Distributed Systems

**What it is:** Coordinates a distributed transaction as a sequence of local transactions. Each step has a compensating transaction (manual rollback) if something fails.

**When to use:**
- Multi-step flow that touches multiple services (e.g.: checkout: reserve stock → charge → create order → notify)
- When 2PC (two-phase commit) is not viable
- n8n workflows with dependent steps

**Two styles:**

*Choreography (Event-driven):* each service listens to an event and acts
```
OrderService: CONFIRMED → publishes OrderConfirmed
InventoryService: listens to OrderConfirmed → reserves → publishes StockReserved
PaymentService: listens to StockReserved → charges → publishes PaymentDone
```

*Orchestration (Centralized):* an orchestrator directs the steps
```
SagaOrchestrator:
  step1: reserveInventory()  → if fails: compensate nothing (start)
  step2: chargePayment()     → if fails: compensate releaseInventory()
  step3: createOrder()       → if fails: compensate refundPayment() + releaseInventory()
```

**Cost:** High complexity. Compensations are hard to test and keep correct.

**Related:** State Machine (to model the Saga state), Command (each step is a Command)
