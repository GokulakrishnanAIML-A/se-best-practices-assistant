# Google Engineering Practices — Code Review and Quality Guidelines

Authoritative guidelines from Google Engineering Practices on software design, code review standards, and change list hygiene.

## Small and Focused Changes
Changes should be small, self-contained, and focused on a single logical improvement.
- **Guideline:** Small changes are reviewed faster, result in higher quality reviews, contain fewer bugs, and are easier to revert if problems occur. A change should ideally be between 50 to 200 lines of code.
- **Violation Indicators:** Large, kitchen-sink pull requests mixing refactoring, feature additions, bug fixes, and reformatting into a single commit; changes affecting dozens of unrelated files.
- **Remediation:** Split large changes into a sequence of smaller, logically coherent changes (e.g., first refactor the interface in PR #1, then implement the new feature in PR #2).
- **Citation:** Google Engineering Practices — Small Changes.

## Design Simplicity and Over-Engineering
Software design should solve the current problem cleanly without introducing premature generalizations or unnecessary abstraction layers.
- **Guideline:** Keep the design simple and direct. Do not add speculative features or complex extensibility hooks for requirements that do not currently exist (You Aren't Gonna Need It — YAGNI).
- **Violation Indicators:** Excessive layers of indirection (e.g., a controller delegating to a manager, delegating to a provider, delegating to a handler, for a simple CRUD operation), unused generic parameters, factory classes that only produce one hardcoded instance.
- **Remediation:** Remove superfluous abstractions. Make the implementation obvious and direct. Refactor to introduce abstractions only when concrete extension needs emerge.
- **Citation:** Google Engineering Practices — Design Simplicity.

## Thorough Automated Test Coverage
Code changes must include comprehensive, reliable automated unit and integration tests.
- **Guideline:** Tests should verify both the happy path and edge cases/failure conditions. Tests should be isolated, deterministic, and maintainable.
- **Violation Indicators:** New functions or classes added without corresponding unit tests; tests that rely on external network/timing dependencies causing flakiness; tests that only assert `True` without verifying business outputs.
- **Remediation:** Author tests that cover expected inputs, boundaries, invalid inputs, and error paths. Use test doubles/fakes for external boundaries.
- **Citation:** Google Engineering Practices — Testing Standards.

## Documentation and Meaningful Comments
Comments should explain *why* something is done, not *what* the code is doing. The code itself should clearly show what is being done.
- **Guideline:** Document architectural decisions, non-obvious algorithms, edge cases, and external constraints. Public APIs must have clear docstrings specifying arguments, return types, and exceptions raised.
- **Violation Indicators:** Redundant comments that merely restate the code line (`i += 1  # increment i`), missing docstrings on public modules and API endpoints, or stale comments that contradict the code.
- **Remediation:** Delete obvious/noisy comments. Update comments to explain business rationale or obscure technical constraints.
- **Citation:** Google Engineering Practices — Writing Good Comments.
