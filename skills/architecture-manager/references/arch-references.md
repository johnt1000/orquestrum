<!-- inject:start -->
# Formal Reference: System Design and Documentation

## 1. Separation Principles

- **Components:** Must be modular. Each item listed in `Components` must have a clear responsibility (Single Responsibility Principle applied at the system level).
- **Coupling:** The `System Diagram` must make clear where critical dependencies and single points of failure exist.

## 2. Diagramming Patterns (Mermaid)

- **User Flows:** Use `sequenceDiagram` for complex interactions between client and server.
- **Structure:** Use `graph TD` or `graph LR` for network topology, services, and databases.
- **State:** Use `stateDiagram-v2` if the business logic involves complex state machines (e.g.: payment processing).

## 3. Maintainability

An architecture document is a living organism.

- Whenever a new component is added to the system, the `Components` field and the `System Diagram` MUST be updated simultaneously.
- The `Data Flow` section must highlight whether there is asynchronous processing (queues, webhooks) or synchronous processing (REST APIs).
<!-- inject:end -->

## 4. Integration with ADRs

The architecture is the final result of multiple decisions. Each link in `Decisions` must point to the ADR that justifies the existence of that system design.

## 5. Patterns and Architecture

Adopted design patterns must be explicitly referenced in the `Components` section of the architecture document. The architecture must not only describe the components — it must indicate HOW they relate structurally.

**Instruction:** Before finalizing any architecture document:

1. Check if `docs/00-discovery/patterns/PATTERNS.md` exists
   - If yes: read the adopted patterns and reference them in the components where they apply
   - If no: signal to Forge that the pattern catalog has not yet been created

2. For each component in the diagram, if it implements a known pattern, document it:
   ```
   | UserRepository | User data abstraction | Repository Pattern |
   | PaymentAdapter | Stripe/PayPal integration | Adapter + Strategy |
   | OrderStateMachine | Order lifecycle | State Machine |
   ```

3. In the Mermaid diagram, use comments or labels to indicate patterns:
   ```mermaid
   graph TD
     Service[UserService] -->|Repository Pattern| Repo[IUserRepository]
     Repo -->|Adapter| DB[(PostgreSQL)]
   ```

**Complete pattern reference:** `./references/pattern-references.md`

---
