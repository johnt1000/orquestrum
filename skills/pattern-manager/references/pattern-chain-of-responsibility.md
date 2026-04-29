# Chain of Responsibility

**Layer:** 2 — Behavioral

**What it is:** Passes the request through a chain of handlers. Each handler decides to process and/or pass it forward.

**When to use:**
- Step-by-step validation pipelines (validate → authenticate → authorize → process)
- HTTP middleware (this pattern is already used in most frameworks)
- Data processing with multiple sequential transformations

**When NOT to use:**
- The chain has only 1-2 fixed steps (use a simple function)
- The order is not clear or changes frequently

**Minimal interface:**
```
interface IHandler:
  setNext(handler: IHandler): IHandler
  handle(request): Response | null

class AuthHandler implements IHandler:
  handle(req):
    if not authenticated: return 401
    return this.next.handle(req)

class RateLimitHandler implements IHandler:
  handle(req):
    if rateLimitExceeded: return 429
    return this.next.handle(req)
```

**Cost:** If a handler fails silently, the bug is hard to locate.

**Related:** Decorator (when all handlers always execute), Middleware (framework-specific implementation)
