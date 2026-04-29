# Circuit Breaker

**Layer:** 3 — Integration / Distributed Systems

**What it is:** Monitors calls to an external service. When failures exceed a threshold, it "opens the circuit" and returns an immediate error (fail fast) for a period, preventing failure cascades.

**When to use:**
- Any HTTP call to a third-party API (OpenAI, Stripe, SMS, etc.)
- Integration with services that may be unstable
- Workers that process jobs via an external API

**When NOT to use:**
- In-memory internal communication
- Trivial idempotent operations

**States:**
```
CLOSED (normal) → failures accumulate
  ↓ threshold reached
OPEN (fail fast) → returns immediate error for N seconds
  ↓ time expired
HALF-OPEN (test) → lets 1 call through
  ↓ success → CLOSED
  ↓ failure → OPEN again
```

**Minimal interface:**
```
circuitBreaker = new CircuitBreaker(openaiClient.complete, {
  threshold: 5,       // failures before opening
  timeout: 30000,     // ms in OPEN before HALF-OPEN
  fallback: () => defaultResponse
})

result = circuitBreaker.execute(prompt)
```

**Cost:** More configuration. Asynchronous behavior harder to test.

**Related:** Retry + Backoff (first try retry, then open the circuit)
