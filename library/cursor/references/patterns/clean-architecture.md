# Clean Architecture

Code organized into concentric layers with a strict Dependency Rule: source code dependencies may only point inward. Outer layers know about inner layers; inner layers know nothing about outer layers.

## Layers (outer to inner)

| Layer | What lives here |
|---|---|
| Frameworks & Drivers | HTTP framework, ORM, queues, 3rd-party SDKs, CLI |
| Interface Adapters | Controllers, presenters, repository implementations, gateways |
| Use Cases / Interactors | Application-specific business rules, orchestration |
| Entities | Enterprise-wide business rules, pure domain objects |

## When to Use

- Application has complex business logic that must survive framework changes
- Multiple delivery mechanisms (API, CLI, message consumer) share the same core logic
- Team needs to test business rules without booting infrastructure
- Long-lived codebase where framework lock-in is a real risk

## When NOT to Use

- Small scripts, prototypes, or throwaway code — the boilerplate isn't worth it
- Data pipelines where the "business logic" is just transformations — simpler module structure works
- CRUD apps with no real domain logic — adds layers without adding value
- Teams under 3 people on a short-lived project — pragmatism over purity

## Key Principles

- **Inward-only imports**: no inner layer imports from an outer layer
- **No framework in entities**: entity classes have zero framework imports
- **No framework in use cases**: use cases receive/return plain DTOs, not HTTP requests or ORM models
- **Repository interfaces in the domain**: interfaces defined in use-case/domain layer, implementations in infrastructure
- **Single-purpose use cases**: `CreateOrderUseCase`, not a generic `OrderService` with 15 methods
- **DTOs at boundaries**: data crossing layers uses plain data transfer objects

## Common Mistakes

- Putting business logic in controllers ("fat controllers")
- Entities that import ORM decorators or framework annotations
- Use cases that directly call HTTP clients instead of going through injected interfaces
- Skipping the interface and depending directly on the database implementation
- Creating use cases that are just pass-throughs to the repository (sign that the domain layer has no real logic)

## Evolution Path

1. **Start simple**: separate business logic from I/O in the same module
2. **Add interfaces**: define repository/gateway interfaces, inject implementations
3. **Organize layers**: move code into domain/application/infrastructure directories
4. **Screaming architecture**: reorganize top-level directories by domain concept, not technical layer
