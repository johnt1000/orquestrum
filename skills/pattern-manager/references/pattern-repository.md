# Repository

**Layer:** 1 — Structural

**What it is:** Abstracts data access behind an interface. Business code does not know whether data comes from SQL, NoSQL, an external API, or memory.

**When to use:**
- There is business logic that needs to be tested without a real database
- The database may change (or needs to be replaced in tests)
- Multiple services access the same data

**When NOT to use:**
- Simple CRUD script without business logic
- Throwaway prototype
- A single service with 2-3 simple queries

**Minimal interface:**
```
interface IUserRepository:
  find(id): User | null
  findBy(filters): User[]
  save(user): User
  delete(id): void
```

**Cost:** More files (interface + implementation). Dependency injection required.

**Related:** Adapter (for reuse of external sources), Unit of Work (for transactions)
