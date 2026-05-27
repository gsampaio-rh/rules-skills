# Event-Driven Architecture

Systems communicate through events — records of facts that have happened. Producers emit events without knowing who consumes them. Consumers react asynchronously.

## When to Use

- Multiple services need to react to the same state change independently
- Temporal decoupling: producer doesn't need to wait for consumers to finish
- Audit trail or event sourcing is a business requirement
- Workloads are spiky and need to be buffered (queue-based load leveling)
- Cross-service data synchronization without tight coupling

## When NOT to Use

- Simple request/response flows where the caller needs an immediate answer — synchronous is simpler and easier to debug
- Operations that must be strictly consistent within a single transaction
- Small monolithic applications where in-process function calls suffice
- When the team lacks experience with distributed systems debugging (distributed tracing, dead letter queues, replay)

## Key Principles

- **Events are facts in past tense**: `OrderPlaced`, `PaymentReceived`, not `PlaceOrder` (that's a command)
- **Versioned event schemas**: events include a version field. Consumers handle unknown versions gracefully.
- **Idempotent consumers**: processing the same event twice produces the same result. Design for at-least-once delivery.
- **Dead letter queue**: unprocessable messages routed to a DLQ for inspection, not silently dropped
- **Ordering guarantees**: be explicit about whether ordering matters. If it does, partition by entity ID. If not, document that consumers handle out-of-order delivery.

## Event Sourcing vs Event Notification

- **Event notification**: events signal that something happened. Consumers query the source for details if needed. Simpler, good for decoupling.
- **Event sourcing**: events ARE the source of truth. State is derived by replaying events. Powerful but complex — only use when audit trail or temporal queries are a hard requirement.

## Saga Patterns

When a business process spans multiple services:
- **Choreography**: each service reacts to events and emits its own. No central coordinator. Simple but hard to trace.
- **Orchestration**: a central saga coordinator tells each service what to do. Easier to reason about. Use when the process has many steps or conditional branches.

## Common Mistakes

- Using events for everything, including simple in-process communication
- Not handling message ordering or duplicate delivery
- No dead letter queue — poison messages block the entire queue
- Event schemas without versioning — breaking consumers on schema changes
- Mixing commands and events (commands tell someone to do something; events record that something happened)

## Evolution Path

1. **Start with synchronous**: direct service calls, understand the data flow
2. **Identify decoupling points**: where does the caller not need to wait for the result?
3. **Introduce event notification**: emit events at key state changes, add consumers
4. **Add infrastructure**: dead letter queues, distributed tracing, schema registry
5. **Consider event sourcing**: only if audit trail or temporal queries are a hard requirement
