<!--
Sync Impact Report
Version change: template -> 1.0.0
Modified principles:
- Template Principle 1 -> I. Object-Oriented Design First
- Template Principle 2 -> II. Depend on Abstractions
- Template Principle 3 -> III. SOLID with Strict Typing
- Template Principle 4 -> IV. Test-Driven Development Mandatory
- Template Principle 5 -> V. Clarity and Maintainability Over Cleverness
Added sections:
- Engineering Constraints
- Delivery Workflow and Quality Gates
Removed sections:
- None
Templates requiring updates:
- ✅ updated .specify/templates/plan-template.md
- ✅ updated .specify/templates/spec-template.md
- ✅ updated .specify/templates/tasks-template.md
- ✅ no command templates present under .specify/templates/commands/
- ✅ no runtime guidance documents requiring synchronization were found
Follow-up TODOs:
- None
-->

# Oficina SDD Constitution

## Core Principles

### I. Object-Oriented Design First
All production code MUST be modeled through explicit objects with clear
responsibilities, stable public contracts, and cohesive behavior. Features MUST
be decomposed into domain entities, value objects, services, and orchestration
components instead of procedural scripts or ad hoc utility flows. Object
composition is the default mechanism for behavior reuse; inheritance is allowed
only when it preserves substitutability and reduces duplication without hiding
control flow. Rationale: a consistent object model improves traceability,
isolates change, and keeps the system understandable as it grows.

### II. Depend on Abstractions
High-level policies MUST depend on interfaces, protocols, or abstract base
classes rather than concrete implementations. Infrastructure concerns such as
I/O, persistence, external services, clocks, and randomness MUST enter the
system through injectable abstractions so they can be replaced in tests and
evolved without rewriting domain logic. Direct construction of concrete
dependencies inside business rules is prohibited unless the component itself is
the composition root. Rationale: dependency inversion reduces coupling and keeps
the codebase open to change without destabilizing core behavior.

### III. SOLID with Strict Typing
Every change MUST satisfy the SOLID principles and MUST preserve strict Python
typing across production and test code. Single Responsibility, Open/Closed,
Liskov Substitution, Interface Segregation, and Dependency Inversion are review
criteria, not optional guidance. Public APIs, internal collaborators, fixtures,
and data structures MUST declare precise types; use of untyped defs, implicit
Any, or broad object-shaped contracts is prohibited unless an explicit and
documented boundary makes it unavoidable. Rationale: strict types and SOLID
design create mechanically verifiable contracts and prevent architecture drift.

### IV. Test-Driven Development Mandatory
TDD is non-negotiable for every behavior change. Work MUST proceed in the
red-green-refactor cycle: define the expected behavior, write an automated test
that fails for the intended reason, implement the smallest change that makes the
test pass, and then refactor while keeping the suite green. Unit tests are the
default proof for domain logic; integration and contract tests MUST cover
cross-boundary behavior, dependency wiring, and regressions in shared contracts.
No production implementation may be merged without prior failing test evidence
or an explicit written exception approved during review. Rationale: TDD keeps
requirements executable and protects maintainability under change.

### V. Clarity and Maintainability Over Cleverness
Implementations MUST favor readable names, small methods, explicit invariants,
and straightforward control flow over terse abstractions or speculative
generalization. Each module MUST have a single obvious purpose, each class MUST
expose behavior through intention-revealing methods, and each change MUST reduce
or contain cognitive load. Optimizations, framework indirection, and advanced
language features require a measurable need and a simpler alternative analysis.
Rationale: this project optimizes for long-term operability, not short-term
novelty.

## Engineering Constraints

- Python code MUST run with strict static type checking enabled and MUST not
  introduce new type-checking suppressions without documented justification.
- Architectural boundaries MUST be explicit in plans, specs, and tasks,
  including which abstractions isolate domain logic from infrastructure.
- New features MUST define unit test scope and any required integration or
  contract coverage before implementation begins.
- Shared utilities MUST emerge only after duplication is observed in at least
  two concrete use cases; premature frameworks and god objects are prohibited.
- Reviews MUST reject changes that bypass abstractions, collapse object
  responsibilities, or trade maintainability for local convenience.

## Delivery Workflow and Quality Gates

Every implementation plan MUST include a constitution check that verifies object
boundaries, abstraction-driven dependencies, SOLID impact, strict typing, and
TDD strategy. Every feature specification MUST capture independently testable
user scenarios plus explicit architectural and quality constraints. Every task
list MUST sequence tests before implementation and include work for typing,
design boundaries, and refactoring where required. Before merge, reviewers MUST
confirm that tests were authored first, the automated suite passes, and no new
architectural shortcuts or typing regressions were introduced.

## Governance

This constitution overrides conflicting local practices for the repository.
Amendments require: (1) a written proposal describing the governance change,
(2) synchronization of affected templates and workflow documents, and (3)
explicit review approval from project maintainers. Versioning follows semantic
rules for governance documents: MAJOR for incompatible principle changes or
removals, MINOR for new principles or materially expanded obligations, and PATCH
for clarifications that do not change compliance behavior. Compliance review is
mandatory for every plan, spec, task list, and code review; violations MUST be
documented in the relevant artifact with a time-bounded remediation decision.

**Version**: 1.0.0 | **Ratified**: 2026-03-13 | **Last Amended**: 2026-03-13
