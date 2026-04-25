# Formal Reference: Epic Management and Decomposition

## 1. Epic Definition

An Epic represents a set of tasks that, once completed, deliver clear business value or a complete systemic feature (e.g.: "Authentication System", "Payment Gateway Integration").

## 2. Scope Criteria

- **Vertical Slicing:** Prefer Epics that deliver end-to-end functionality (Database + API + Interface) rather than horizontal slices (Database only).
- **Traceability:** Each Epic MUST point to a `Spec`. If there is no Spec, the Epic must not exist.

## 3. Dependency Management

- **T1, T2, T3:** Must be names of task files to be created later.
- The `Execution Flow` in the template serves to identify bottlenecks. If all tasks depend on a single initial task (T1), this indicates a critical risk point.

## 4. Domain Definition

Help the AI filter context using clear domains:

- **Core:** Pure business logic.
- **Integration:** External APIs, Webhooks, n8n.
- **Infrastructure:** Proxmox, Docker, AWS.
- **AI/Automation:** MCP Servers, Agent logic.

## 5. Size Criterion

An Epic is well-sized if:
- It can be delivered in 3 to 10 Tasks
- It generates observable business value when completed
- It can be demonstrated independently

If an Epic would have fewer than 3 Tasks → it may be a standalone Task.
If an Epic would have more than 10 Tasks → break it into 2 smaller Epics.

## 6. Slicing Examples

**Horizontal (avoid):**
```
E001 — Create all database tables
E002 — Create all API endpoints
E003 — Create all user interface
```

**Vertical (prefer):**
```
E001 — Authentication System (DB schema + API /login + /logout + login interface)
E002 — Session Scheduling (DB sessions + API CRUD + calendar UI)
```
