# Fail Fast

**Layer:** 0 — Engineering Principles

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
