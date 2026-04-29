# Command

**Layer:** 2 — Behavioral

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
