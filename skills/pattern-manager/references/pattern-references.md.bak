# References — pattern-manager

Canonical catalog of language-agnostic engineering principles and design patterns. Organized in 5 layers — from the most fundamental to the most structural. Read before any `pattern-manager` operation.

---

<!-- inject:start -->
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

---

### DRY — Don't Repeat Yourself

**What it is:** Every piece of knowledge must have a single, unambiguous, authoritative representation in the system. Duplication of logic, not data.

**Violation signal:**
```
// Same email validation rule in 3 places:
UserService:  if email.includes('@') ...
AuthService:  if email.includes('@') ...
ImportService: if email.includes('@') ...
```

**Correct:**
```
EmailValidator.isValid(email)  // a single place, called by all 3
```

**When NOT to apply:** DRY applies to *business logic*, not structural code. Two functions that do `return id` do not violate DRY — they are coincidences, not knowledge duplications.

**Cost of ignoring:** A business rule change requires N edits in N places. One will be forgotten.

**Related:** SoC (separate to avoid duplication), Repository (centralize data access)

---

### KISS — Keep It Simple, Stupid


**What it is:** The simplest solution that works is the correct one. Complexity that does not solve a real problem is pre-paid technical debt without justification.

**Violation signal:**
```
// Abstraction for a single use:
class UserEmailValidationStrategyFactory:
  createStrategy(type): IValidationStrategy
    return new EmailValidationStrategy()   // only this one exists

// Simple and sufficient:
function isValidEmail(email): bool
```

**When NOT to apply:** When immediate simplicity creates future complexity. E.g.: hardcoding a value that will change → extraction to config is KISS in the right context.

**Cost of ignoring:** Code that is hard to read, test, and modify. New members take days to understand what could be understood in minutes.

**Related:** YAGNI (do not build what you do not need), Facade (simplify without hiding real complexity)

---

### YAGNI — You Aren't Gonna Need It

**What it is:** Do not implement functionality until it is needed. Speculative code is technical debt — it has maintenance cost without business value.

**Violation signal:**
```
// Task only asked to create a user. But the dev added:
createUser(data, options?: {
  sendWelcomeEmail?: bool,       // not requested
  createDefaultWorkspace?: bool, // not requested
  assignDefaultRole?: string,    // not requested
})
```

**Correct:** Only what the SPEC/Task requested. If the parameter did not come from a requirement, it does not exist.

**Cost of ignoring:** Code that nobody uses, tests, or understands. Increases attack surface. Increases onboarding time.

**Related:** KISS (do not complicate), task-manager guardrail ("do not mark as Completed with extra unrequested functionality")

---

### SOLID — Single Responsibility (S)

**What it is:** Each module/class/function must have **a single reason to change**. If two different stakeholders could request changes to the same component, it does two things.

**Violation signal:**
```
class UserController:
  createUser(req)         // business logic (domain)
  hashPassword(pwd)       // infrastructure (security)
  sendWelcomeEmail(user)  // side effect (notification)
  validateEmail(email)    // domain (validation)
```

**Correct:** `UserController` only receives the request and delegates. `PasswordHasher`, `EmailNotifier`, `UserValidator` are separate classes.

**Related:** SoC (separated concerns), Facade (aggregate without mixing)

---

### SOLID — Open/Closed (O)

**What it is:** Entities must be open for extension, closed for modification. Adding new behavior must not require changing existing code.

**Violation signal:**
```
function calculateDiscount(user):
  if user.type == 'premium': return 0.2
  if user.type == 'student': return 0.1
  if user.type == 'vip':     return 0.3  // added later
  // adding 'corporate' requires modifying this function
```

**Correct:** Strategy pattern — each user type has its own discount strategy. Adding `corporate` is creating a new class, not modifying the existing one.

**Related:** Strategy (natural solution for Open/Closed)

---

### SOLID — Liskov Substitution (L)

**What it is:** Subtypes must be substitutable for their supertypes without altering the correct behavior of the program.

**Violation signal:**
```
class Rectangle:
  setWidth(w); setHeight(h)

class Square extends Rectangle:
  setWidth(w): width = height = w  // violates! changes expected behavior
  setHeight(h): width = height = h
```

```
// Consumer that works with Rectangle breaks with Square:
r.setWidth(5); r.setHeight(3)
assert r.area() == 15  // Rectangle: 15 ✅ | Square: 9 ❌
```

**Related:** Adapter (when you need to adapt without inheritance), Composition > Inheritance

---

### SOLID — Interface Segregation (I)

**What it is:** Clients must not depend on interfaces they do not use. Large interfaces must be split into smaller, more specific interfaces.

**Violation signal:**
```
interface IWorker:
  work()
  eat()
  sleep()

class Robot implements IWorker:
  work()   // ok
  eat()    // ??? robots don't eat — empty implementation or throw
  sleep()  // ??? robots don't sleep
```

**Correct:**
```
interface IWorkable:  work()
interface IFeedable:  eat()
class Human implements IWorkable, IFeedable
class Robot implements IWorkable
```

**Related:** Adapter (when inheriting an incompatible interface is mandatory)

---

### SOLID — Dependency Inversion (D)

**What it is:** High-level modules must not depend on low-level modules. Both must depend on abstractions. Abstractions must not depend on details.

**Violation signal:**
```
class UserService:
  constructor():
    this.repo = new PostgresUserRepository()  // coupled to PostgreSQL
    this.email = new SendgridEmailClient()     // coupled to Sendgrid
```

**Correct:**
```
class UserService:
  constructor(repo: IUserRepository, email: IEmailClient)  // dependency injection
```

**Cost of ignoring:** Impossible to test without a real database and without Sendgrid. Switching providers requires rewriting the service.

**Related:** Repository, Adapter, any dependency injection

---

### Fail Fast

**What it is:** Detect and report errors as early as possible. Validations at the beginning of the function, not at the end after processing.

**Violation signal:**
```
function transferMoney(from, to, amount):
  debitAccount(from, amount)   // performs the operation
  creditAccount(to, amount)    // performs the operation
  if amount <= 0: throw Error  // validates after already having debited!
```

**Correct:**
```
function transferMoney(from, to, amount):
  if amount <= 0: throw InvalidAmountError
  if not accountExists(from): throw AccountNotFoundError
  // only then executes
  debitAccount(from, amount)
  creditAccount(to, amount)
```

**Cost of ignoring:** Partially modified state when an error occurs. Difficult to debug and revert.

**Related:** Guard Clauses (Fail Fast implementation technique)

---

### SoC — Separation of Concerns

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

---

### Composition over Inheritance

**What it is:** Prefer composing behavior via interfaces and dependency injection rather than implementation inheritance. Inheritance is tight coupling; composition is loose coupling.

**Violation signal:**
```
// Inheritance for behavior reuse:
class AdminUser extends User:
  class ModeratorUser extends AdminUser:  // deep inheritance
    class SuperAdminUser extends ModeratorUser:  // ...
```

**Correct:**
```
class User:
  constructor(permissions: IPermissionSet)  // composes behavior via injection

AdminPermissions implements IPermissionSet
ModeratorPermissions implements IPermissionSet
```

**Related:** Strategy (special case of composition), Decorator (add behavior by composition)

---

### Law of Demeter — Don't talk to strangers

**What it is:** A method should only call: its own methods, methods of its direct parameters, methods of objects it created, methods of its fields.

**Violation signal:**
```
// Chained access — knows the internal structure of 3 objects:
order.getCustomer().getAddress().getCity()
user.getProfile().getSettings().getNotificationPreference()
```

**Correct:**
```
order.getDeliveryCity()           // Order encapsulates the access
user.getNotificationPreference()  // User encapsulates the access
```

**Cost of ignoring:** A change in the structure of Address breaks all code that accesses `order.getCustomer().getAddress()`. Implicit cascading coupling.

**Related:** Facade (hide internal structure), SRP (each object takes care of itself)

<!-- inject:end -->

---

## Layer 1 — Structural

Patterns that organize how code is structured and how components relate.

---

### Repository

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

---

### Adapter

**What it is:** Converts the interface of an external/incompatible component to the interface the rest of the code expects. Isolates external dependencies.

**When to use:**
- Third-party SDK with a different interface than expected (e.g.: Stripe SDK vs `IPaymentProvider`)
- External API that may be swapped (e.g.: OpenAI may be replaced by Anthropic)
- Integration with a legacy system

**When NOT to use:**
- The external interface is already stable and will never change
- Small project where the abstraction creates more complexity than value

**Minimal interface:**
```
interface IEmailProvider:
  send(to, subject, body): void

class SendgridAdapter implements IEmailProvider:
  send(to, subject, body):
    sendgridSDK.mail.send({ to, subject, content: body })  // translates

class ResendAdapter implements IEmailProvider:
  send(to, subject, body):
    resendSDK.emails.send({ from, to, subject, html: body })  // translates
```

**Cost:** One extra layer of indirection. Only worth it when the source may change.

**Related:** Facade (when multiple classes need to be adapted)

---

### Facade

**What it is:** Provides a simplified interface to a complex subsystem of multiple classes.

**When to use:**
- Module has 5+ classes that consumers need to orchestrate
- Want to expose only a subset of a subsystem's operations
- Reduce coupling between layers

**When NOT to use:**
- The subsystem has only 1-2 classes
- Consumers need granular access to the subsystem

**Minimal interface:**
```
// Without Facade: the consumer knows 4 classes
class CheckoutService:
  checkout(cart):
    inventory.reserve(cart.items)
    payment.charge(cart.total)
    order.create(cart)
    notification.send(order)

// With Facade: the consumer knows 1
class OrderFacade:
  placeOrder(cart): Order
    // internally orchestrates the 4 classes
```

**Cost:** Can become a God Object if it grows without control.

**Related:** Mediator (when multiple objects communicate bidirectionally)

---

### Proxy

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

---

### Decorator

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

---

## Layer 2 — Behavioral

Patterns that define how components communicate and distribute responsibilities.

---

### Strategy

**What it is:** Defines a family of interchangeable algorithms/behaviors. The consumer does not know which one is in use.

**When to use:**
- `if/switch` in business logic based on type/provider (`if payment == 'stripe'`)
- Multiple providers of the same service (email, payment, storage)
- Behavior configurable by tenant/environment

**When NOT to use:**
- Only 1 algorithm exists and there are no plans to switch
- The switch is so rare that the complexity is not worth it

**Minimal interface:**
```
interface IPaymentStrategy:
  charge(amount, customer): Receipt

class StripeStrategy implements IPaymentStrategy: ...
class PaypalStrategy implements IPaymentStrategy: ...

class CheckoutService:
  constructor(payment: IPaymentStrategy)
  // does not know which provider it is using
```

**Cost:** More interfaces and classes. Dependency injection required.

**Related:** Adapter (when the external interface does not match IStrategy), Factory (to instantiate the correct strategy)

---

### Observer / Event Bus

**What it is:** Producer emits events without knowing who consumes them. Consumers register interest in specific events.

**When to use:**
- Business side effects (e.g.: user created → send email + create audit log + notify slack)
- Decouple modules that should not know each other
- n8n workflows triggered by business events
- Real-time notifications

**When NOT to use:**
- Simple linear flow where order matters and the producer needs to know the result
- When implicit coupling creates more confusion than explicit coupling

**Minimal interface:**
```
EventBus:
  publish(event: Event): void
  subscribe(eventType, handler: (event) => void): void

// Producer does not know consumers
UserService:
  createUser(data):
    user = repo.save(data)
    eventBus.publish(UserCreated { user })
    return user

// Independent consumers
EmailService: subscribe(UserCreated, sendWelcomeEmail)
AuditService: subscribe(UserCreated, createAuditLog)
```

**Cost:** Flow is hard to trace. Execution order not guaranteed. Complex debugging.

**Related:** Command (when the event must be executed reliably), Outbox (when delivery needs to be guaranteed)

---

### Chain of Responsibility

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

---

### State Machine

**What it is:** An object with well-defined states and explicit transitions between them. Makes invalid transitions impossible.

**When to use:**
- Entity with a complex lifecycle (Order: draft → confirmed → paid → shipped → delivered)
- Approval workflow with multiple steps
- Protocol connections (disconnected → connecting → connected → error)

**When NOT to use:**
- Entity with only 2 states (active/inactive — use boolean)
- States are just independent flags without transitions between them

**Minimal interface:**
```
States: DRAFT | CONFIRMED | PAID | SHIPPED | DELIVERED | CANCELLED

Transitions:
  DRAFT      → CONFIRMED  (on: confirm)
  DRAFT      → CANCELLED  (on: cancel)
  CONFIRMED  → PAID       (on: paymentReceived)
  PAID       → SHIPPED    (on: ship)
  SHIPPED    → DELIVERED  (on: deliver)

Order:
  currentState: State
  transition(event):
    if transition not allowed: throw InvalidTransitionError
    currentState = newState
```

**Cost:** More initial code. Worth it when the number of states > 3 with transitions.

**Related:** Event Sourcing (when transitions must be persisted as history)

---

### Command

**What it is:** Encapsulates an operation as an object. Allows queuing, undoing, recording, and repeating operations.

**When to use:**
- Task queue / job queue (asynchronous operations)
- Operations with undo/redo
- Action auditing (who did what and when)
- Retry of failed operations

**When NOT to use:**
- Simple operations that do not need to be queued or reversed
- When a simple `async function` resolves it

**Minimal interface:**
```
interface ICommand:
  execute(): Result
  undo(): void  // optional

class SendEmailCommand implements ICommand:
  constructor(to, subject, body)
  execute(): emailService.send(to, subject, body)
  undo(): // impossible — use compensating transaction

// Queue
commandQueue.add(new SendEmailCommand(...))
commandQueue.process()
```

**Cost:** More objects. Serialization required for persistence.

**Related:** Observer (Command can be emitted as an event), Saga (sequence of distributed Commands)

---

## Layer 3 — Integration / Distributed Systems

Critical patterns for systems that communicate with external services or operate in a distributed manner. Highly relevant for n8n and automations.

---

### Circuit Breaker

**What it is:** Monitors calls to an external service. When failures exceed a threshold, it "opens the circuit" and returns an immediate error (fail fast) for a period, preventing failure cascades.

**When to use:**
- Any HTTP call to a third-party API (OpenAI, Stripe, SMS, etc.)
- Integration with services that may be unstable
- Workers that process jobs via an external API

**When NOT to use:**
- In-memory internal communication
- Trivial idempotent operations

**States:**
```
CLOSED (normal) → failures accumulate
  ↓ threshold reached
OPEN (fail fast) → returns immediate error for N seconds
  ↓ time expired
HALF-OPEN (test) → lets 1 call through
  ↓ success → CLOSED
  ↓ failure → OPEN again
```

**Minimal interface:**
```
circuitBreaker = new CircuitBreaker(openaiClient.complete, {
  threshold: 5,       // failures before opening
  timeout: 30000,     // ms in OPEN before HALF-OPEN
  fallback: () => defaultResponse
})

result = circuitBreaker.execute(prompt)
```

**Cost:** More configuration. Asynchronous behavior harder to test.

**Related:** Retry + Backoff (first try retry, then open the circuit)

---

### Retry + Exponential Backoff

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

---

### Outbox Pattern

**What it is:** Guarantees that an event is published if and only if the database transaction is committed. Writes the event to an `outbox` table in the same transaction, then a worker publishes and removes it.

**When to use:**
- Business event must be published together with persistence (e.g.: UserCreated must go to n8n)
- At-least-once delivery guarantee for events
- Avoid inconsistent state (database saved but event not sent)

**When NOT to use:**
- Single-node system without messaging
- Event can be lost without issue

**Flow:**
```
BEGIN TRANSACTION
  INSERT INTO users (data)
  INSERT INTO outbox (event: 'UserCreated', payload: user)
COMMIT

// Separate worker (asynchronous):
LOOP:
  events = SELECT * FROM outbox WHERE published = false
  FOR event IN events:
    publish(event)
    UPDATE outbox SET published = true WHERE id = event.id
```

**Cost:** Extra table. Extra worker. Delivery latency (eventual consistency).

**Related:** Idempotent Consumer (the consumer must handle duplicates)

---

### Idempotent Consumer

**What it is:** Guarantees that processing the same event/message multiple times has the same effect as processing it once. Required for systems with retry and at-least-once delivery.

**When to use:**
- Any worker that consumes events or webhooks (may receive duplicates)
- After implementing Outbox or Retry
- Payment operations, resource creation

**Typical implementation:**
```
// Before processing, check if already processed
processEvent(event):
  if processedEvents.contains(event.id):
    return  // silent skip — already processed
  
  // process...
  
  processedEvents.add(event.id)
```

**Cost:** Storage of processed IDs (Redis, DB table). TTL required for cleanup.

**Related:** Outbox (produces events with unique IDs), Retry (reprocesses events)

---

### Saga

**What it is:** Coordinates a distributed transaction as a sequence of local transactions. Each step has a compensating transaction (manual rollback) if something fails.

**When to use:**
- Multi-step flow that touches multiple services (e.g.: checkout: reserve stock → charge → create order → notify)
- When 2PC (two-phase commit) is not viable
- n8n workflows with dependent steps

**Two styles:**

*Choreography (Event-driven):* each service listens to an event and acts
```
OrderService: CONFIRMED → publishes OrderConfirmed
InventoryService: listens to OrderConfirmed → reserves → publishes StockReserved
PaymentService: listens to StockReserved → charges → publishes PaymentDone
```

*Orchestration (Centralized):* an orchestrator directs the steps
```
SagaOrchestrator:
  step1: reserveInventory()  → if fails: compensate nothing (start)
  step2: chargePayment()     → if fails: compensate releaseInventory()
  step3: createOrder()       → if fails: compensate refundPayment() + releaseInventory()
```

**Cost:** High complexity. Compensations are hard to test and keep correct.

**Related:** State Machine (to model the Saga state), Command (each step is a Command)

---

### BFF — Backend for Frontend

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

---

## Layer 4 — Architectural

Patterns that define the macro structure of the system.

---

### Hexagonal Architecture (Ports & Adapters)

**What it is:** Isolates the business core (domain) from frameworks, databases, and external interfaces. The domain defines Ports (interfaces); Adapters implement those interfaces for each technology.

**When to use:**
- Any project with longevity > 1 year
- Business logic that needs to be tested without infrastructure
- Multiple drivers (HTTP + CLI + worker) for the same domain

**Structure:**
```
Domain (core):
  - Entities, Use Cases, Ports (interfaces)
  - Zero external dependencies

Adapters (edge):
  - Driving: HTTP Controller, CLI, Worker → calls Use Cases
  - Driven: Repository impl, Email impl, Queue impl → called by Use Cases

Ports:
  - IUserRepository (driven port)
  - IEmailNotifier (driven port)
```

**Cost:** More complex folder structure. Learning curve. Dependency injection mandatory.

**Related:** Repository (for data driven ports), Adapter (for external service driven ports)

---

### CQRS — Command Query Responsibility Segregation

**What it is:** Separates write operations (Commands, which change state) from read operations (Queries, which return data). Each side can have its own model and database.

**When to use:**
- Read and write have very different volumes
- The read model needs to be denormalized for performance
- Dashboards and reports with complex queries
- Independent scalability of read and write

**When NOT to use:**
- Simple CRUD where read = write
- Small team without experience — high complexity
- Eventual consistency is unacceptable

**Minimal interface:**
```
// Write side
CreateOrderCommand: { customerId, items, total }
  → handler: validates, persists, emits OrderCreated event

// Read side (denormalized, optimized for query)
OrderSummaryQuery: { orderId } → OrderSummaryView
  → handler: reads from read-store (can be Redis, Elasticsearch, materialized view)
```

**Cost:** Eventual consistency between write and read. Two models to maintain.

**Related:** Event Sourcing (frequently combined), State Machine (for the write model)

---

### Strangler Fig

**What it is:** Incremental migration of a legacy system. New features are built in the new system; the legacy is gradually "strangled" until it can be shut down.

**When to use:**
- Onboarding an existing project (phase -1 of the pipeline)
- Rewriting a production system without downtime
- Gradual modernization of a monolith

**Flow:**
```
Phase 1: Proxy in front of EVERYTHING → routes to Legacy
Phase 2: New feature X → built in New → Proxy routes X to New, rest to Legacy
Phase 3: Feature Y migrated → Proxy routes Y to New
...
Phase N: All traffic in New → Legacy shut down
```

**Cost:** Period of coexistence of both systems. Data synchronization between them.

**Related:** Adapter (for compatibility between legacy and new interfaces), Anti-Corruption Layer (protection against legacy model leakage)

---

### Event Sourcing

**What it is:** Entity state is derived from an immutable sequence of events. Never overwrites — only appends events. Current state = replay of all events.

**When to use:**
- Complete history of changes is a requirement (audit, compliance, LGPD — right of access)
- Undo/redo is required
- Debugging complex state
- Combined with CQRS in event-driven systems

**When NOT to use:**
- High-frequency events without history requirement (telemetry metrics)
- Team without experience — high learning curve
- Read performance is critical without projection infrastructure

**Flow:**
```
// Write
events = [
  UserRegistered { id, email, timestamp },
  EmailVerified { id, timestamp },
  SubscriptionStarted { id, plan, timestamp }
]
eventStore.append(userId, events)

// Read (replay)
user = eventStore.replay(userId)
  .reduce(initialState, applyEvent)
// user.status = 'subscribed'
```

**Cost:** Infrastructure complexity. Snapshots required for performance with long histories. Eventual consistency with read models.

**Related:** CQRS (reading via projections), State Machine (to validate event transitions)

---

<!-- inject:start -->
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
<!-- inject:end -->
