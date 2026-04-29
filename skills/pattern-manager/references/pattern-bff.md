# BFF — Backend for Frontend

**Layer:** 3 — Integration / Distributed Systems

**What it is:** An intermediate API specific to each type of client (web, mobile, n8n, third parties). Aggregates and formats backend data for the exact needs of each client.

**When to use:**
- Clients with radically different needs (mobile needs fewer fields, web needs more)
- n8n needs simple, direct endpoints that human clients do not need
- Reduce over-fetching / under-fetching by client type

**When NOT to use:**
- A single type of client
- The API is already sufficiently specific

**Minimal interface:**
```
// Generic backend
UserService: getUser(id): UserComplete

// BFF for Web
WebBFF: GET /user/:id → UserComplete (all fields)

// BFF for Mobile
MobileBFF: GET /user/:id → UserSummary (id, name, avatar only)

// BFF for n8n
N8nBFF: GET /user/:id/trigger-data → { id, webhookPayload }
```

**Cost:** More services to maintain. Duplicated code if not well abstracted.

**Related:** Adapter (each BFF adapts the backend API for the client)
