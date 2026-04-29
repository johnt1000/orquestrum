# Adapter

**Layer:** 1 — Structural

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
