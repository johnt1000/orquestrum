# SOLID — Liskov Substitution (L)

**Layer:** 0 — Engineering Principles

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
