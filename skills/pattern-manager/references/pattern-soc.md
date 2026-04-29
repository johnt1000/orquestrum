# SoC — Separation of Concerns

**Layer:** 0 — Engineering Principles

**What it is:** Each component must be responsible for a single aspect of the problem. Different aspects (business, persistence, presentation, security) must be separated.

**Violation signal:**
```
// HTTP route with mixed business logic, SQL, and formatting:
app.post('/users', (req, res) => {
  const hash = bcrypt.hash(req.body.password)    // infra (security)
  db.query('INSERT INTO users...')                // infra (persistence)
  if (!req.body.email.includes('@')) throw Error  // domain (validation)
  res.json({ message: 'ok', user: { ...user }})  // presentation
})
```

**Correct:** Controller → Service → Repository → DB. Each layer with its own concern.

**Related:** Hexagonal Architecture (maximum separation), SRP (class level)
