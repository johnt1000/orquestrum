# Retry + Exponential Backoff

**Layer:** 3 — Integration / Distributed Systems

**What it is:** Retries failed operations with increasing intervals. Avoids overloading the service with simultaneous retries.

**When to use:**
- Any network operation (HTTP, queue, database)
- Transient failures (timeout, 503, network hiccup)
- n8n workers with steps that may fail

**When NOT to use:**
- Permanent errors (400 Bad Request, 401 Unauthorized) — retry will not resolve them
- Non-idempotent operations without idempotency protection

**Backoff formula:**
```
delay = baseDelay * (2 ^ attemptNumber) + jitter
// Example: 1s, 2s, 4s, 8s, 16s (+ randomness to avoid thundering herd)
```

**Minimal interface:**
```
retry(operation, {
  maxAttempts: 3,
  baseDelay: 1000,
  retryOn: [503, 429, 'NetworkError'],
  onRetry: (attempt, error) => log(attempt, error)
})
```

**Cost:** Latency increases on failure. Idempotency required in the operation.

**Related:** Circuit Breaker (upper limit of retries), Idempotent Consumer
