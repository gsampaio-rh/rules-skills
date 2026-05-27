# Microservices

An architectural style where a system is composed of small, independently deployable services, each owning its own data and communicating over the network.

## When to Use

- Multiple teams need to deploy independently without coordinating releases
- Different parts of the system have fundamentally different scaling needs
- Parts of the system need different technology stacks
- The domain is well-understood and service boundaries are clear
- Deployment frequency needs to be high (multiple times per day per service)

## When NOT to Use

- Small team (under 5-8 engineers) — the coordination overhead exceeds the benefit
- Domain boundaries are unclear — you'll draw the wrong boundaries and pay for it with cross-service data problems
- Greenfield project with unclear requirements — start with a modular monolith
- The team doesn't have distributed systems experience (networking, eventual consistency, distributed tracing)

## Key Principles

- **No shared databases**: services do not share database tables. Data exchanged via API or events. Violating this creates invisible coupling.
- **Service boundaries follow domain boundaries**: align services with bounded contexts, not technical layers. `OrderService`, not `DatabaseService`.
- **Independent deployability**: changing and deploying one service does not require changing or deploying another
- **Contract testing**: inter-service contracts tested independently. Don't rely on integration environments for contract validation.
- **Distributed tracing**: trace IDs propagated across all service calls. Without this, debugging production issues is nearly impossible.
- **Graceful degradation**: if a downstream service is unavailable, the upstream service degrades gracefully rather than failing entirely

## Distributed System Costs

These costs are real and must be accepted before choosing microservices:
- Network latency on every inter-service call
- Partial failures (one service is down, others are up)
- Eventual consistency between services
- Operational complexity (monitoring, logging, deployment of N services)
- Data joins across services are expensive or impossible
- Distributed transactions are hard (use sagas instead)

## Common Mistakes

- Extracting microservices too early, before domain boundaries are clear
- "Micro" services that are actually nano-services — too fine-grained, causing excessive network calls
- Shared libraries that create hidden coupling (deploying the library requires redeploying all consumers)
- Synchronous chains: A calls B calls C calls D — fragile and slow
- No API versioning — breaking consumers on every change

## Evolution Path

1. **Start as a modular monolith**: single deployment, but with clear module boundaries and interfaces
2. **Identify extraction candidates**: modules with different scaling needs, different team ownership, or different deployment cadences
3. **Extract one service**: pick the module with the clearest boundary and least coupling
4. **Add infrastructure**: API gateway, service discovery, distributed tracing, centralized logging
5. **Extract more as needed**: each extraction should solve a specific problem, not be done for its own sake
