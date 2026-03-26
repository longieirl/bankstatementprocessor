# REFERENCE.md — GitHub Issue RFC Guide

Used by Claude and developers when writing architectural refactor issues for this repository.

---

## GitHub Issue RFC Template

Use this structure for all refactor / architecture RFC issues:

```markdown
## Why
[What creates the friction and why it matters technically.
Cover: which modules are affected, root cause of the friction
(coupling, shallow interface, silent failure, poor testability),
and the concrete technical consequence if left unaddressed.]

## Current behaviour
[A real code snippet — not prose — showing the problem.]

## Expected outcome
[Bulleted vision of the module after the refactor.
Not a task list — describe the end state.]

## Acceptance criteria
- [ ] Specific, verifiable requirement
- [ ] Each item can be checked by a reviewer without knowing the implementation
- [ ] Include test requirements explicitly
```

### Section guidance

**Why** must answer:
- Which file(s) and line(s) are the friction source?
- What design principle is violated (coupling, shallow module, implicit contract, etc.)?
- What breaks or degrades as a result (testability, observability, maintainability)?

**Current behaviour** must show code, not describe it. One focused snippet is better than many.

**Expected outcome** describes the *shape* of the solution, not the steps. A reader should be able to evaluate it without reading the implementation plan.

**Acceptance criteria** are checkbox items. Each must be independently verifiable. Include at least one test-related criterion.

---

## Four Dependency Categories

Use these when classifying the coupling between modules in a candidate refactor:

| Category | Description | Example |
|----------|-------------|---------|
| **Intra-layer** | Both modules in the same package; no I/O or external state | `template_registry.py` ↔ `template_model.py` within `templates/` |
| **Cross-package** | One module depends on another installed package | `bankstatements_core` → `pdfplumber` for PDF extraction |
| **Cross-boundary (I/O)** | Depends on filesystem, network, environment variables, or external process | `TemplateRegistry` reading template JSON from disk; `column_config.py` reading `TABLE_COLUMNS` env var |
| **Cross-boundary (time)** | Depends on system clock, scheduled jobs, or time-sensitive state | Any service checking dates or timeouts at runtime |

---

## Dependency Strategy Patterns

How to handle each dependency category when designing a deep module:

| Strategy | When to use | How |
|----------|-------------|-----|
| **Constructor injection** | Intra-layer or cross-package stable deps | Accept as constructor parameter with a sensible default |
| **Parameter injection** | Cross-package, per-call variability | Accept as a function/method parameter |
| **Port (Protocol/ABC)** | Cross-boundary I/O; want testability without real I/O | Define a Protocol; inject real impl in production, test double in tests |
| **Inline with env fallback** | Single cross-boundary dep with one obvious source | Read from env var directly; expose an override parameter for tests |

---

## Deep Module Checklist

A module is **deep** (Ousterhout, *A Philosophy of Software Design*) when its interface is significantly simpler than its implementation. Before raising a refactor RFC, verify the friction is real:

- [ ] Must a caller read the *implementation* (not just the signature) to use the module correctly?
- [ ] Does the module leak I/O, error handling, retry logic, or data transformation into its interface?
- [ ] Are dependencies hardcoded or constructed internally, making the module untestable without patching?
- [ ] Does the module raise built-in exception types from *its dependencies* rather than its own typed exceptions?
- [ ] Is there more than one construction path, or a multi-branch constructor choosing between behaviours?

If any of these is yes, the module is a candidate.

A module is **shallow** (and worth consolidating, not splitting) when:
- Its interface has nearly as many concepts as its implementation
- Tests mock internals rather than testing at the boundary
- An abstraction (Protocol, base class) exists with only one implementation and no planned others

---

## Worked Examples

Issues #62–#64 on this repository are RFCs written using this format. They cover:

- [#62](https://github.com/longieirl/bankstatementprocessor/issues/62) — hardcoded Euro symbol in output column names
- [#63](https://github.com/longieirl/bankstatementprocessor/issues/63) — currency-specific internal TypedDict field names
- [#64](https://github.com/longieirl/bankstatementprocessor/issues/64) — inconsistent currency-symbol stripping across code paths

Use them as style reference.
