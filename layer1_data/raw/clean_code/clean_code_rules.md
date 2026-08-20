# Clean Code Principles and Maintainability Guidelines

Authoritative reference summaries for writing readable, maintainable, and robust software.

## Meaningful Names and Intention-Revealing Identifiers
Variable, function, and class names must reveal their intent, context, and purpose without needing explanatory comments.
- **Violation Indicators:** Single-letter variables outside short loop indices (e.g., `d`, `tmp`, `val`, `data`, `res`), cryptic abbreviations, misleading names that do not match variable types, encoding type or scope into names (Hungarian notation), or naming classes with generic suffixes like `DataHolder` or `DoHelper`.
- **Remediation:** Choose names that answer why it exists, what it does, and how it is used (e.g., `elapsed_time_in_days` instead of `d`, `unpaid_invoices` instead of `list1`).
- **Citation:** Robert C. Martin, Clean Code — Chapter 2: Meaningful Names.

## Small Functions and Single Level of Abstraction (SLA)
Functions should be small (ideally under 20–30 lines), do exactly one thing, and do it well. Statements within a function should all be at the same level of abstraction.
- **Violation Indicators:** Functions longer than 40–50 lines, functions containing deep nested loops or conditionals (nesting depth > 3), mixing high-level business orchestration with low-level string manipulation or raw SQL queries.
- **Remediation:** Extract paragraphs and conditional blocks into separate, descriptive helper functions. Keep functions to one level of abstraction below their stated purpose.
- **Citation:** Robert C. Martin, Clean Code — Chapter 3: Functions.

## Function Arguments and Command-Query Separation (CQS)
Functions should ideally take 0 to 2 arguments (monadic or dyadic). Triadic functions should be rare, and polyadic functions (> 3 arguments) should be refactored into argument objects. Functions should either do something (command) or answer something (query), but not both.
- **Violation Indicators:** Functions taking 4 or more positional parameters, boolean flag arguments that cause the function to do two different things depending on the boolean (`process_order(order, is_express=True)`), or functions that mutate state while returning a boolean status.
- **Remediation:** Encapsulate multiple parameters into dedicated data classes or config objects. Split flag-based functions into two distinct functions (`process_express_order` and `process_standard_order`). Separate commands from queries.
- **Citation:** Robert C. Martin, Clean Code — Chapter 3: Functions.

## Don't Repeat Yourself (DRY) and Duplication
Every piece of knowledge or business logic must have a single, unambiguous, authoritative representation within a system.
- **Violation Indicators:** Duplicate algorithm blocks, copy-pasted validation checks or database query structures across multiple endpoints or methods, identical business calculations repeated with minor variable name changes.
- **Remediation:** Centralize shared logic into reusable utility functions, base classes, or middleware components. Parameterize variations cleanly.
- **Citation:** Andy Hunt & Dave Thomas, The Pragmatic Programmer — DRY Principle.

## Error Handling and Exception Strategy
Error handling is important, but if it obscures logic, it is wrong. Use exceptions rather than return codes or error flags to separate business logic from error handling.
- **Violation Indicators:** Returning special error codes (`-1`, `None`, `"ERROR"`) that callers must manually check, empty catch/except blocks that swallow exceptions silently (`except Exception: pass`), catch-all exception handling without logging or re-raising, or nested try-catch blocks cluttering core logic.
- **Remediation:** Throw domain-specific exceptions. Handle exceptions at boundaries or centralized middleware. Never silently swallow exceptions. Use context managers for resource clean-up.
- **Citation:** Robert C. Martin, Clean Code — Chapter 7: Error Handling.

## Cyclomatic Complexity and Deep Nesting
High cyclomatic complexity makes code difficult to comprehend, test, and maintain.
- **Violation Indicators:** Cyclomatic complexity (radon grade C/D/F, CC > 10), deeply nested `if/for/while/try` blocks exceeding a nesting depth of 3 or 4.
- **Remediation:** Use early returns / guard clauses (`if not condition: return`), extract subroutines, or replace complex switch/case structures with polymorphism or lookup maps.
- **Citation:** Thomas J. McCabe, Structured Testing: A Testing Methodology Using the Cyclomatic Complexity Metric.
