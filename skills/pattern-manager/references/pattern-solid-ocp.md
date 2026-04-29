# SOLID — Open/Closed (O)

**Layer:** 0 — Engineering Principles

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
