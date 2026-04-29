# Law of Demeter — Don't talk to strangers

**Layer:** 0 — Engineering Principles

**What it is:** A method should only call: its own methods, methods of its direct parameters, methods of objects it created, methods of its fields.

**Violation signal:**
```
// Chained access — knows the internal structure of 3 objects:
order.getCustomer().getAddress().getCity()
user.getProfile().getSettings().getNotificationPreference()
```

**Correct:**
```
order.getDeliveryCity()           // Order encapsulates the access
user.getNotificationPreference()  // User encapsulates the access
```

**Cost of ignoring:** A change in the structure of Address breaks all code that accesses `order.getCustomer().getAddress()`. Implicit cascading coupling.

**Related:** Facade (hide internal structure), SRP (each object takes care of itself)
