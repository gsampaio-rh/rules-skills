---
paths:
  - "**/*.py"
  - "**/*.ts"
  - "**/*.tsx"
---
# CQRS — Command Query Responsibility Segregation

Separate the model for writing data (commands) from the model for reading data (queries). Each side can be optimized independently.

## When to Use

- Read and write workloads have fundamentally different performance characteristics or scaling needs
- The read model needs to be denormalized or pre-computed for query performance
- Complex domain logic on the write side that shouldn't be polluted by read concerns
- Event sourcing is in use (CQRS is a natural companion)
- Multiple read views of the same data (dashboard, report, API) that need different shapes

## When NOT to Use

- Most applications don't need this. Simple CRUD with a single database serves reads and writes fine.
- Small data volumes where read performance isn't a concern
- Teams unfamiliar with eventual consistency — the split between read and write models introduces consistency delays
- When the domain model is simple enough that read and write shapes are nearly identical

## Key Principles

- **Commands mutate state, return nothing** (or just a confirmation/ID). A command is an imperative: `PlaceOrder`, `CancelSubscription`.
- **Queries return data, change nothing**. A query is a question: `GetOrderById`, `ListRecentOrders`.
- **Separate models**: the write model enforces invariants and business rules. The read model is optimized for queries (denormalized, pre-aggregated).
- **Consistent projections**: when the write side changes state, the read model must be updated. This can be synchronous (same transaction) or asynchronous (via events).

## Eventual Consistency

If read and write models are updated asynchronously:
- Users may see stale data briefly after a write
- Design the UI to account for this (optimistic updates, "processing" states)
- Monitor projection lag — if it grows, the system has a problem
- Ensure projections are idempotent and replayable

## Common Mistakes

- Applying CQRS to the entire application instead of just the parts that need it
- Write model that returns query data (defeats the separation)
- Read model that isn't kept in sync — stale data without monitoring
- Over-engineering: adding CQRS when a single well-indexed database query would suffice
- Forgetting that CQRS adds operational complexity (two models to maintain, sync to monitor)

## Evolution Path

1. **Start with a single model**: standard read/write through the same data layer
2. **Add read-optimized views**: materialized views or cached queries for hot paths
3. **Separate the command path**: route writes through explicit command handlers with domain logic
4. **Split the models**: separate databases or schemas for read and write if scaling demands it
5. **Add event-based sync**: use domain events to update the read model asynchronously
