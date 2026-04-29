# Pattern Index — pattern-manager

Canonical catalog of language-agnostic engineering principles and design patterns. Organized in 5 layers — from the most fundamental to the most structural.

> **Usage:** Read this index first to identify relevant patterns, then load only the specific pattern files needed. Each pattern lives in its own file: `pattern-{slug}.md`.

---

## How to use this catalog

For each principle and pattern:
- **When to use** — concrete signals that indicate need
- **When NOT to use** — common over-engineering pitfalls
- **Violation signal / Minimal interface** — language-agnostic code smell or pseudocode
- **Cost** — the real price of adopting
- **Related** — other principles/patterns that frequently appear together

---

## Layer 0 — Engineering Principles

> Principles are different from patterns. Patterns are reusable structural solutions. **Principles are quality criteria for already-written code** — they are the grammar that makes code readable, maintainable, and safe to change. Verify them in all written code, regardless of tier.

| Slug | Name | File | Summary |
|------|------|------|---------|
| `dry` | DRY — Don't Repeat Yourself | `pattern-dry.md` | Every piece of knowledge must have a single, unambiguous, authoritative representation. Duplication of logic, not data. |
| `kiss` | KISS — Keep It Simple, Stupid | `pattern-kiss.md` | The simplest solution that works is the correct one. Complexity without justification is pre-paid technical debt. |
| `yagni` | YAGNI — You Aren't Gonna Need It | `pattern-yagni.md` | Do not implement functionality until it is needed. Speculative code is technical debt. |
| `solid-srp` | SOLID — Single Responsibility (S) | `pattern-solid-srp.md` | Each module/class/function must have a single reason to change. |
| `solid-ocp` | SOLID — Open/Closed (O) | `pattern-solid-ocp.md` | Entities must be open for extension, closed for modification. |
| `solid-lsp` | SOLID — Liskov Substitution (L) | `pattern-solid-lsp.md` | Subtypes must be substitutable for their supertypes without altering correct behavior. |
| `solid-isp` | SOLID — Interface Segregation (I) | `pattern-solid-isp.md` | Clients must not depend on interfaces they do not use. |
| `solid-dip` | SOLID — Dependency Inversion (D) | `pattern-solid-dip.md` | High-level modules must not depend on low-level modules. Both must depend on abstractions. |
| `fail-fast` | Fail Fast | `pattern-fail-fast.md` | Detect and report errors as early as possible. Validations at the beginning, not the end. |
| `soc` | SoC — Separation of Concerns | `pattern-soc.md` | Each component must be responsible for a single aspect of the problem. |
| `composition-over-inheritance` | Composition over Inheritance | `pattern-composition-over-inheritance.md` | Prefer composing behavior via interfaces and DI rather than implementation inheritance. |
| `law-of-demeter` | Law of Demeter | `pattern-law-of-demeter.md` | A method should only call its own methods, its direct parameters, objects it created, and its fields. |

---

## Layer 1 — Structural

Patterns that organize how code is structured and how components relate.

| Slug | Name | File | Summary |
|------|------|------|---------|
| `repository` | Repository | `pattern-repository.md` | Abstracts data access behind an interface. Business code does not know the data source. |
| `adapter` | Adapter | `pattern-adapter.md` | Converts the interface of an external/incompatible component to the interface the rest of the code expects. |
| `facade` | Facade | `pattern-facade.md` | Provides a simplified interface to a complex subsystem of multiple classes. |
| `proxy` | Proxy | `pattern-proxy.md` | Controls access to another object, adding behavior (log, cache, auth) without changing the interface. |
| `decorator` | Decorator | `pattern-decorator.md` | Dynamically adds responsibilities to an object without inheritance. Each decorator wraps the previous one. |

---

## Layer 2 — Behavioral

Patterns that define how components communicate and distribute responsibilities.

| Slug | Name | File | Summary |
|------|------|------|---------|
| `strategy` | Strategy | `pattern-strategy.md` | Defines a family of interchangeable algorithms/behaviors. The consumer does not know which one is in use. |
| `observer-event-bus` | Observer / Event Bus | `pattern-observer-event-bus.md` | Producer emits events without knowing who consumes them. Consumers register interest in specific events. |
| `chain-of-responsibility` | Chain of Responsibility | `pattern-chain-of-responsibility.md` | Passes the request through a chain of handlers. Each handler decides to process and/or pass it forward. |
| `state-machine` | State Machine | `pattern-state-machine.md` | An object with well-defined states and explicit transitions. Makes invalid transitions impossible. |
| `command` | Command | `pattern-command.md` | Encapsulates an operation as an object. Allows queuing, undoing, recording, and repeating operations. |

---

## Layer 3 — Integration / Distributed Systems

Critical patterns for systems that communicate with external services or operate in a distributed manner.

| Slug | Name | File | Summary |
|------|------|------|---------|
| `circuit-breaker` | Circuit Breaker | `pattern-circuit-breaker.md` | Monitors calls to an external service. Opens the circuit on excessive failures to prevent cascades. |
| `retry-exponential-backoff` | Retry + Exponential Backoff | `pattern-retry-exponential-backoff.md` | Retries failed operations with increasing intervals. Avoids overloading the service. |
| `outbox` | Outbox Pattern | `pattern-outbox.md` | Guarantees that an event is published iff the database transaction is committed. |
| `idempotent-consumer` | Idempotent Consumer | `pattern-idempotent-consumer.md` | Processing the same event multiple times has the same effect as processing it once. |
| `saga` | Saga | `pattern-saga.md` | Coordinates a distributed transaction as a sequence of local transactions with compensating rollback. |
| `bff` | BFF — Backend for Frontend | `pattern-bff.md` | An intermediate API specific to each type of client. Aggregates and formats backend data per client. |

---

## Layer 4 — Architectural

Patterns that define the macro structure of the system.

| Slug | Name | File | Summary |
|------|------|------|---------|
| `hexagonal-architecture` | Hexagonal Architecture (Ports & Adapters) | `pattern-hexagonal-architecture.md` | Isolates the business core from frameworks, databases, and external interfaces via Ports and Adapters. |
| `cqrs` | CQRS | `pattern-cqrs.md` | Separates write operations (Commands) from read operations (Queries). Each side can have its own model. |
| `strangler-fig` | Strangler Fig | `pattern-strangler-fig.md` | Incremental migration of a legacy system. New features built in new system; legacy gradually replaced. |
| `event-sourcing` | Event Sourcing | `pattern-event-sourcing.md` | Entity state derived from an immutable sequence of events. Never overwrites — only appends. |

---

## Quick Selection Guide

Given a situation, which pattern(s) to consider?

| Situation | Pattern(s) |
|---------|-----------|
| "I need to swap the database" | Repository |
| "I have `if provider == 'stripe'` in the service" | Strategy + Adapter |
| "User created triggers 4 actions" | Observer / Event Bus |
| "External HTTP call that may go down" | Circuit Breaker + Retry |
| "Webhook may be delivered twice" | Idempotent Consumer |
| "Event must be published only if database saves" | Outbox Pattern |
| "Checkout flow touches 3 services" | Saga |
| "Business API with longevity > 1 year" | Hexagonal Architecture |
| "Order status has 6 states" | State Machine |
| "I need to migrate the legacy system" | Strangler Fig |
| "Read is much more frequent than write" | CQRS |
| "Mobile and web need different data" | BFF |
| "I want to add logging without changing the code" | Proxy / Decorator |
