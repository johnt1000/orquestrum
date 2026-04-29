# SOLID — Interface Segregation (I)

**Layer:** 0 — Engineering Principles

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
