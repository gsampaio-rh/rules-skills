---
paths:
  - "**/*.py"
  - "**/*.ts"
  - "**/*.tsx"
---
# Domain-Driven Design (DDD)

A set of patterns for tackling complex domains by placing the domain model at the center of the software. The code reflects the business, not the framework.

## When to Use

- Complex business domain with rules that change independently of the technology
- Domain experts are available and their language should be reflected in code
- Multiple bounded contexts with different models for the same real-world concept
- Business logic is the competitive advantage, not the technology stack

## When NOT to Use

- Simple CRUD applications with no meaningful domain logic — DDD adds ceremony without value
- ETL pipelines or data transformation jobs — functional composition is simpler
- Small teams on tight deadlines where the domain is well-understood and stable
- Prototypes or MVPs where the domain model is still being discovered (use exploratory code first)

## Key Principles

- **Ubiquitous language**: code uses the exact terminology domain experts use. If the business says "policy", the code says `Policy`, not `InsuranceRecord`.
- **Bounded contexts**: different parts of the system can model the same concept differently. A `Customer` in billing is not the same as a `Customer` in support. Each context has its own model.
- **Aggregate roots**: groups of related entities with a single root that enforces invariants. External code interacts only through the root, never reaching into child entities directly.
- **Value objects**: immutable objects defined by their attributes, not identity. `Money(100, "USD")` is equal to another `Money(100, "USD")`.
- **Domain events**: significant state changes emit events (`OrderPlaced`, `PaymentReceived`) to decouple side effects from the core action.
- **Anti-corruption layer**: when integrating with external systems or legacy code, translate between their model and yours at the boundary. Never let their model leak into your domain.

## Common Mistakes

- Applying DDD to the entire codebase instead of only the complex subdomain
- Anemic domain models: entities that are just data bags with getters/setters, all logic in services
- Missing bounded context boundaries: one giant model for everything
- Domain events used synchronously in the same transaction (defeats the purpose)
- Aggregate roots that are too large, causing contention and performance issues

## Evolution Path

1. **Identify the core domain**: which part of the business has the most complex rules?
2. **Establish ubiquitous language**: align code terminology with domain expert vocabulary
3. **Define bounded contexts**: draw boundaries around parts of the system that have different models
4. **Model aggregates**: group entities that must be consistent together under a single root
5. **Add domain events**: decouple side effects from core domain actions
