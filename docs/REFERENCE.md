# REFERENCE.md — GitHub Issue RFC Guide

Used by Claude and developers when writing architectural refactor issues for this repository.

## Skills that use this file

- [`improve-codebase-architecture`](https://github.com/mattpocock/skills/tree/main/improve-codebase-architecture) — surface architectural friction and propose deep-module refactors as GitHub issue RFCs
- `gsd` suite — built-in Claude Code workflow tool for structured project planning, phase execution, and delivery

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
| **In-process** | Pure computation, in-memory state, no I/O. Always deepenable — merge modules and test directly. | `template_registry.py` ↔ `template_model.py` within `templates/` |
| **Local-substitutable** | Dependencies with local test stand-ins. Deepenable if the substitute exists. | `TemplateRegistry` reading JSON from disk — testable with `tmp_path` |
| **Remote but owned (Ports & Adapters)** | Your own services across a network boundary. Define a port (interface); inject an in-memory adapter for tests, real adapter in production. | Internal APIs or services you control |
| **True external (Mock)** | Third-party services you don't control. Mock at the boundary; inject as a port. | External auth providers, third-party APIs |

---

## Dependency Strategy Patterns

How to handle each category when designing a deep module:

| Category | Strategy |
|----------|----------|
| **In-process** | Merge modules; test the combined boundary directly |
| **Local-substitutable** | Test with the local stand-in running in-process (e.g. `tmp_path`, in-memory store) |
| **Remote but owned** | Define a Protocol port; production uses real adapter, tests use in-memory adapter |
| **True external** | Define a Protocol port; inject a mock in tests |

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
