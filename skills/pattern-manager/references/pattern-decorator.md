# Decorator

**Layer:** 1 — Structural

**What it is:** Dynamically adds responsibilities to an object without inheritance. Each decorator wraps the previous one.

**When to use:**
- Multiple optional behaviors that combine (e.g.: log + cache + retry)
- Alternative to multiple inheritance
- Data transformation pipelines

**When NOT to use:**
- When the order of decorators is not clear
- When only 1 extra behavior is needed (simple Proxy resolves it)

**Minimal interface:**
```
interface IHandler: handle(request): Response

class AuthDecorator implements IHandler:
  constructor(next: IHandler)
  handle(req): if not req.isAuthenticated: throw; return next.handle(req)

class LogDecorator implements IHandler:
  constructor(next: IHandler)
  handle(req): log(req); result = next.handle(req); log(result); return result

// Composition:
handler = LogDecorator(AuthDecorator(RealHandler()))
```

**Cost:** Hard to debug — the stack trace has N layers. Order matters.

**Related:** Chain of Responsibility (when handlers can stop the chain)
