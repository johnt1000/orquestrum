# Strategy

**Layer:** 2 — Behavioral

**What it is:** Defines a family of interchangeable algorithms/behaviors. The consumer does not know which one is in use.

**When to use:**
- `if/switch` in business logic based on type/provider (`if payment == 'stripe'`)
- Multiple providers of the same service (email, payment, storage)
- Behavior configurable by tenant/environment

**When NOT to use:**
- Only 1 algorithm exists and there are no plans to switch
- The switch is so rare that the complexity is not worth it

**Minimal interface:**
```
interface IPaymentStrategy:
  charge(amount, customer): Receipt

class StripeStrategy implements IPaymentStrategy: ...
class PaypalStrategy implements IPaymentStrategy: ...

class CheckoutService:
  constructor(payment: IPaymentStrategy)
  // does not know which provider it is using
```

**Cost:** More interfaces and classes. Dependency injection required.

**Related:** Adapter (when the external interface does not match IStrategy), Factory (to instantiate the correct strategy)
