# Facade

**Layer:** 1 — Structural

**What it is:** Provides a simplified interface to a complex subsystem of multiple classes.

**When to use:**
- Module has 5+ classes that consumers need to orchestrate
- Want to expose only a subset of a subsystem's operations
- Reduce coupling between layers

**When NOT to use:**
- The subsystem has only 1-2 classes
- Consumers need granular access to the subsystem

**Minimal interface:**
```
// Without Facade: the consumer knows 4 classes
class CheckoutService:
  checkout(cart):
    inventory.reserve(cart.items)
    payment.charge(cart.total)
    order.create(cart)
    notification.send(order)

// With Facade: the consumer knows 1
class OrderFacade:
  placeOrder(cart): Order
    // internally orchestrates the 4 classes
```

**Cost:** Can become a God Object if it grows without control.

**Related:** Mediator (when multiple objects communicate bidirectionally)
