# Hexagonal Architecture (Ports & Adapters)

The application core defines ports (interfaces) for everything it needs from the outside world. Adapters implement those ports for specific technologies. The core has zero knowledge of frameworks, databases, or external services.

## When to Use

- Business logic must be testable without any infrastructure (database, HTTP, message broker)
- The application needs to support multiple delivery mechanisms (REST API, CLI, message consumer, scheduled job)
- External dependencies may change (swap databases, change message brokers, replace vendors)
- Long-lived codebase where isolating the core from infrastructure changes is worth the upfront investment

## When NOT to Use

- Small scripts or automation tools — the port/adapter boilerplate adds overhead with no benefit
- Data pipelines where the "logic" is mostly I/O transformations — a functional pipeline is simpler
- Prototypes where you're still discovering what the application should do
- When the team is small and the codebase is short-lived — pragmatism over purity

## Relationship to Clean Architecture

Hexagonal architecture and Clean Architecture express the same core idea (dependency inversion, infrastructure at the edges) with different vocabulary:

| Hexagonal | Clean Architecture |
|---|---|
| Ports | Interfaces / Boundaries |
| Adapters | Interface Adapters / Gateways |
| Application Core | Use Cases + Entities |

In practice, they're interchangeable. Use the vocabulary that makes more sense to your team.

## Key Principles

- **Ports are interfaces**: defined in the application core. `UserRepository`, `EmailSender`, `PaymentGateway`. They describe WHAT the core needs, not HOW it's provided.
- **Adapters implement ports**: `PostgresUserRepository`, `SendGridEmailSender`, `StripePaymentGateway`. They live outside the core.
- **Dependency inversion**: the core depends on abstractions (ports). Concrete implementations (adapters) are injected at startup.
- **Driving adapters**: adapt external input TO the application (HTTP controllers, CLI handlers, message consumers)
- **Driven adapters**: adapt the application TO external output (database, email, external APIs)

## Common Mistakes

- Creating ports that mirror the adapter's API instead of expressing the domain's needs
- Ports with too many methods (violating interface segregation) — keep them focused
- Adapters that contain business logic instead of just translating between the port interface and the technology
- Not having a composition root — the wiring of ports to adapters should happen in one place at startup
- Creating adapters for things that don't change (over-abstracting stable dependencies)

## Evolution Path

1. **Start with separation**: put business logic in pure functions/classes with no imports from infrastructure
2. **Define ports**: extract interfaces for external dependencies (repositories, clients, senders)
3. **Create adapters**: move infrastructure code behind those interfaces
4. **Composition root**: wire everything together at the application entry point
5. **Test with fakes**: write in-memory implementations of ports for fast, deterministic tests
