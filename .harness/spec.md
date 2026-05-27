# Spec: Multi-Tenant Billing Platform

## Vision

Build a multi-tenant billing platform that lets organizations track product usage, receive accurate invoices, and pay through Stripe — with a web admin dashboard for both platform operators and tenant administrators. The product serves SaaS providers who need tenant isolation, transparent metering, and reliable payment collection without building billing infrastructure from scratch. Starting from a greenfield state in this repo (existing JWT helpers only), the platform should grow feature-by-feature into a cohesive billing system that can eventually meter any billable event the product emits.

## Technical Direction

**Stack and architecture**

- **Backend:** Python API service using hexagonal (ports-and-adapters) / clean architecture — domain logic isolated from HTTP, persistence, and third-party integrations.
- **Database:** PostgreSQL for tenants, users, usage events, invoices, and payment state. Row-level or schema-level tenant isolation enforced at the persistence boundary.
- **Auth:** Extend the existing JWT helpers (`src/auth.py`, `src/token_validation.py`) to support tenant-scoped claims, roles, and API authentication. Tokens should carry tenant context for all tenant-bound operations.
- **Payments:** Stripe as the payment processor — Checkout, Customer Portal, Subscriptions, and Invoices where applicable. Webhook endpoint for asynchronous payment lifecycle events (success, failure, subscription changes).
- **Admin UI:** Separate web frontend (React or similar SPA) consuming the API. Server-rendered pages are acceptable for an MVP if they accelerate delivery, but the dashboard should feel like a modern admin product.
- **Metering pipeline:** Append-only usage event ingestion with idempotency, periodic aggregation into billable quantities, and auditability (who consumed what, when).
- **Deployment assumptions:** Local development via Docker Compose (API + Postgres + optional Stripe CLI for webhooks). Production deployment details deferred to later features.

**Key constraints**

- Tenant data must never leak across tenant boundaries — isolation is a first-class requirement, not an afterthought.
- Stripe is the source of truth for payment instruments and charge outcomes; the local database mirrors Stripe state via webhooks and reconciliation.
- All monetary calculations use explicit currency and rounding rules stored with the invoice, not inferred at display time.
- The repo today has no API layer, database, or frontend — each feature should establish just enough infrastructure for its scope without over-building ahead.

## Features

### Feature 1: Multi-Tenant Identity and Tenancy Foundation

**User stories:**

- As a platform operator, I want to create and manage tenant organizations so that each customer has an isolated billing context.
- As a tenant admin, I want to invite and manage users within my organization so that my team can access billing data without seeing other tenants.
- As an API consumer, I want every authenticated request scoped to exactly one tenant so that data isolation is guaranteed by default.
- As a developer integrating the platform, I want clear tenant and user roles (e.g., platform admin, tenant admin, tenant member) so that authorization rules are predictable.

**Scope notes:** Includes tenant and user domain models, persistence, tenant-scoped authentication extending existing JWT helpers, basic REST API for tenant/user CRUD, and role-based access control foundations. Does NOT include usage metering, invoicing, Stripe integration, or the admin dashboard UI (API-only for this feature; manual/API testing is sufficient).

### Feature 2: Usage Tracking and Metering

**User stories:**

- As a product engineer, I want to record billable usage events via API so that consumption is captured in near real time.
- As a tenant admin, I want to view current-period usage summaries so that I can understand consumption before an invoice arrives.
- As a platform operator, I want to define meter types (e.g., API calls, storage GB-hours, seats) so that different products can be billed on different dimensions.
- As a billing system, I want idempotent event ingestion so that retries and duplicate submissions do not double-count usage.

**Scope notes:** Includes meter definitions, usage event ingestion API, storage and aggregation queries for a billing period, and basic usage reporting endpoints. Does NOT include invoice line-item generation, pricing tiers, or Stripe metered billing sync (those belong to Features 3 and 4).

### Feature 3: Invoice Generation

**User stories:**

- As a billing system, I want to generate invoices from aggregated usage for a billing period so that tenants receive accurate charges.
- As a tenant admin, I want to view and download invoices for past and current periods so that I have records for accounting and audit.
- As a platform operator, I want to configure billing cycles (e.g., monthly) and see invoice status (draft, finalized, paid, void) so that revenue operations stay organized.
- As a finance stakeholder, I want invoice line items tied back to meter types and usage totals so that charges are explainable.

**Scope notes:** Includes invoice and line-item domain models, billing period logic, generation from usage aggregates, invoice lifecycle (draft → finalized), and API endpoints to list/retrieve invoices. Does NOT include payment collection (Feature 4) or dashboard UI (Feature 5). PDF/export is in scope if straightforward; otherwise defer to Feature 5.

### Feature 4: Stripe Payment Processing

**User stories:**

- As a tenant admin, I want to add a payment method and pay invoices through Stripe so that outstanding balances are settled securely.
- As a tenant admin, I want to manage subscriptions (where applicable) so that recurring plans are billed automatically.
- As the platform, I want to receive Stripe webhooks for payment success, failure, and subscription changes so that local invoice and subscription state stays synchronized.
- As a platform operator, I want failed payments flagged and invoice status updated accordingly so that dunning and follow-up can happen.

**Scope notes:** Includes Stripe Customer linkage per tenant, Checkout or Payment Intent flows for invoice payment, subscription setup where the pricing model supports it, webhook handler with signature verification, and reconciliation of Stripe events to local invoice/payment records. Does NOT include the admin dashboard UI (Feature 5) or advanced dunning automation.

### Feature 5: Admin Dashboard

**User stories:**

- As a platform operator, I want a dashboard to view all tenants, their usage, invoices, and payment status so that I can operate the billing platform.
- As a tenant admin, I want a self-service portal to see usage, invoices, and payment methods so that I do not need to contact support for routine billing tasks.
- As a tenant admin, I want to pay open invoices and update payment methods from the dashboard so that billing is self-service.
- As any admin user, I want clear navigation, status indicators, and error feedback so that billing operations feel trustworthy and understandable.

**Scope notes:** Includes web UI for platform-admin and tenant-admin views, authentication flow integrated with the API, pages for tenants/users (Feature 1), usage summaries (Feature 2), invoice list/detail (Feature 3), and payment actions via Stripe (Feature 4). Does NOT include mobile apps, advanced analytics, or white-label theming beyond a clean default design.

## Design Direction

- **Visual identity:** Clean, professional admin aesthetic — light background, clear typography, restrained color palette with semantic status colors (green paid, amber pending, red failed/overdue).
- **Layout:** Sidebar navigation for primary sections (Overview, Usage, Invoices, Payments, Settings). Platform admin sees a tenant switcher or global tenant list; tenant admin sees only their organization context.
- **Interaction patterns:** Data tables with sort/filter for invoices and usage; detail drawers or pages for invoice line items; prominent CTAs for "Pay invoice" and "Add payment method"; toast notifications for async actions (webhook-driven status updates).
- **Accessibility:** Follow WCAG 2.1 AA basics — keyboard navigation, sufficient contrast, form labels, and status messages not conveyed by color alone.
- **Empty states:** Friendly guidance when a tenant has no usage yet, no invoices, or no payment method on file.
- **Consistency:** Reuse a component library (e.g., shadcn/ui, MUI, or similar) rather than bespoke styling per page.

## Open Questions

- **Pricing model:** Pure usage-based, flat subscription, tiered plans, or hybrid? This affects meter definitions, invoice logic, and Stripe product setup.
- **Billable events:** What specific usage dimensions should the MVP meter (e.g., API requests only, or multiple meter types from day one)?
- **Tenant onboarding:** Self-service signup with email verification, or platform-operator-provisioned tenants only?
- **Currency:** Single currency (USD) for MVP, or multi-currency from the start?
- **Subscription vs. invoice-only:** Should tenants be on Stripe Subscriptions, pay-as-you-go invoices, or both?
- **Tax:** Are sales tax / VAT calculations required for MVP, or out of scope?
- **Platform admin access:** Separate super-admin auth, or a role flag on the same user model?
- **Existing JWT secret:** The current dev-only hardcoded secret — migrate to environment-based configuration as part of Feature 1?

## Trade-offs

| Decision | Alternative considered | Reasoning |
|----------|----------------------|-----------|
| Hexagonal architecture in Python | Monolithic MVC in a single framework layer | Billing touches payments, metering, and tenancy — clean boundaries reduce risk when swapping Stripe adapters or adding new meter types. |
| PostgreSQL with application-level tenant scoping | Separate database per tenant | Shared Postgres with strict tenant_id filtering is simpler for MVP and matches typical SaaS billing platforms; can revisit isolation hardening later. |
| Extend existing JWT auth | Adopt OAuth2/OIDC provider (Auth0, Keycloak) | Repo already has JWT helpers; extending them avoids new infrastructure for a greenfield MVP. OAuth can be added later. |
| Stripe as sole payment processor | Pluggable multi-processor abstraction | Stripe covers subscriptions, invoicing, and webhooks well; premature abstraction adds complexity before a second processor is needed. |
| Separate admin SPA | Server-rendered admin pages | SPA gives richer UX for dashboards and aligns with modern admin tooling; slightly more setup cost upfront. |
| Feature-ordered delivery (tenancy → metering → invoices → payments → UI) | Build dashboard first | Backend-first ensures each UI feature has real data and APIs; reduces mock-driven frontend work. |
| Webhook-driven Stripe sync | Polling Stripe API | Webhooks are real-time and Stripe-recommended; polling reserved for reconciliation jobs if needed later. |
