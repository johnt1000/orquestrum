# Composition over Inheritance

**Layer:** 0 — Engineering Principles

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
