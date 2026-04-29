# Proxy

**Layer:** 1 — Structural

**What it is:** An object that controls access to another object, adding behavior (log, cache, auth) without changing the interface.

**When to use:**
- Add logging/tracing without modifying business code
- Transparent cache of costly operations
- Access control (auth check before executing)
- Lazy loading of heavy resources

**When NOT to use:**
- When framework middleware (Express, Fastify) already resolves the case
- When the additional logic is specific to 1 method, not the entire interface

**Minimal interface:**
```
interface IUserRepository: find(id): User

class CachedUserRepository implements IUserRepository:
  constructor(real: IUserRepository, cache: Cache)
  find(id):
    if cache.has(id): return cache.get(id)
    user = this.real.find(id)
    cache.set(id, user)
    return user
```

**Cost:** One more class per added responsibility. Flow can be confusing to trace.

**Related:** Decorator (when multiple responsibilities accumulate)
