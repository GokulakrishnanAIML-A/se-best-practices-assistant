# PEP 8 — Style Guide for Python Code

Authoritative reference standards for Pythonic code style, conventions, and idiomatic practices.

## Naming Conventions
Follow standard Python naming conventions across identifiers.
- **Rules:**
  - Classes: `CapWords` (PascalCase), e.g., `OrderProcessor`, `UserAccount`.
  - Functions and Methods: `snake_case` (lowercase with words separated by underscores), e.g., `calculate_tax()`, `get_user_by_id()`.
  - Variables: `snake_case`, e.g., `total_amount`, `retry_count`.
  - Constants: `ALL_CAPS_SNAKE_CASE` (uppercase with words separated by underscores), e.g., `MAX_RETRY_ATTEMPTS`, `DEFAULT_TIMEOUT`.
  - Private attributes/methods: Leading single underscore `_internal_method` or `_helper`.
- **Violation Indicators:** CamelCase variable or function names (`getUserData()`), uppercase variable names for mutable instances, mixed styles.
- **Citation:** Python Software Foundation — PEP 8: Naming Conventions.

## Imports Formatting and Organization
Imports should always be on separate lines and grouped into three distinct sections separated by a blank line.
- **Rules:**
  1. Standard library imports (e.g., `import os`, `import sys`).
  2. Related third party imports (e.g., `import requests`, `import pydantic`).
  3. Local application/library specific imports (e.g., `from layer1_data.types import Chunk`).
  - Avoid wildcard imports (`from module import *`) because they pollute the namespace and obscure symbol origin.
- **Violation Indicators:** Wildcard imports, single-line comma-separated module imports (`import os, sys, json`), mixed unordered standard and third-party imports.
- **Citation:** Python Software Foundation — PEP 8: Imports.

## Idiomatic Python Comparisons and Boolean Evaluation
Leverage Python's idiomatic expressions for equality, identity, and sequence truthiness.
- **Rules:**
  - Compare singletons like `None` and booleans using identity `is` or `is not`, never `== None` or `== True`.
  - Check sequence emptiness using `if not seq:` instead of `if len(seq) == 0:` or `if seq == []:`.
  - Catch specific exception classes (`except ValueError:`) instead of bare `except:`.
- **Violation Indicators:** `if val == None:`, `if flag == True:`, `if len(items) == 0:`, bare `except:` clauses.
- **Citation:** Python Software Foundation — PEP 8: Programming Recommendations.
