# SOLID Principles for Software Engineering

Authoritative reference guidelines for object-oriented design and architecture.

## Single Responsibility Principle (SRP)
A class or module should have one, and only one, reason to change. Every class should encapsulate a single responsibility or business actor concern.
- **Violation Indicators:** A class having multiple unrelated duties (e.g., handling business calculation, SQL database persistence, and HTTP/email notification formatting in a single class such as `UserManager` or `OrderProcessor`), classes with excessive method counts (God classes with > 8 methods), or high line counts (> 200 lines).
- **Remediation:** Extract secondary responsibilities into dedicated collaborating services or helper classes (e.g., separate `UserRepository`, `NotificationService`, and `UserValidator`).
- **Citation:** Robert C. Martin, SOLID Principles — Single Responsibility.

## Open/Closed Principle (OCP)
Software entities (classes, modules, functions) should be open for extension, but closed for modification. You should be able to add new functionality without editing existing, tested source code.
- **Violation Indicators:** Functions or methods with extensive `if/elif/else` chains or `match/switch` statements checking object type/enum codes to execute type-specific behavior (e.g., `calculate_discount(order_type)` modifying the core function whenever a new discount type arrives).
- **Remediation:** Use polymorphism, strategy patterns, or abstract base classes / protocols. Define an interface and inject concrete strategy implementations.
- **Citation:** Robert C. Martin, SOLID Principles — Open/Closed.

## Liskov Substitution Principle (LSP)
Subtypes must be substitutable for their base types without altering the correctness of the program. If class S is a subtype of class T, objects of type T may be replaced with objects of type S without breaking functionality.
- **Violation Indicators:** Overridden methods in subclasses throwing `NotImplementedError`, returning unexpected dummy values, weakening preconditions, strengthening postconditions, or type-checking subclasses (`isinstance(obj, Subclass)`) in client code.
- **Remediation:** Ensure subclasses fulfill the entire base contract. If a subclass cannot fulfill the base contract, favor composition over inheritance or refine the abstraction hierarchy.
- **Citation:** Barbara Liskov, SOLID Principles — Liskov Substitution.

## Interface Segregation Principle (ISP)
Clients should not be forced to depend upon interfaces or methods they do not use. Prefer many small, client-specific interfaces over one large, monolithic general-purpose interface.
- **Violation Indicators:** Fat interfaces where implementing classes leave several methods empty or raise `NotImplementedError` because the interface bundled unrelated capabilities (e.g., a `Worker` interface bundling `code()`, `test()`, `deploy()`, and `hire()`).
- **Remediation:** Break bloated interfaces into smaller, cohesive role interfaces or mixins (e.g., `Codeable`, `Testable`, `Deployable`).
- **Citation:** Robert C. Martin, SOLID Principles — Interface Segregation.

## Dependency Inversion Principle (DIP)
High-level modules should not depend on low-level modules; both should depend on abstractions (interfaces or protocols). Abstractions should not depend on details; details should depend on abstractions.
- **Violation Indicators:** Direct instantiation of concrete database drivers, HTTP clients, or file system handlers inside business logic classes (e.g., `self.db = MySQLClient()` inside an `OrderService.__init__`), making unit testing with mocks impossible.
- **Remediation:** Introduce abstract interfaces and pass dependencies via constructor injection (Dependency Injection).
- **Citation:** Robert C. Martin, SOLID Principles — Dependency Inversion.
