---
paths:
  - "**/*.tsx"
  - "**/*.jsx"
  - "**/*.html"
  - "**/*.css"
---
# Design Systems

A design system is the single source of truth for a product's visual language and component library. It bridges design and engineering with shared vocabulary, tokens, and reusable components.

## When to Build vs Adopt

**Build your own when**: the product has a strong brand identity, the team is large enough to maintain it, and existing systems don't fit the domain (e.g., data-heavy dashboards, healthcare UIs).

**Adopt an existing system when**: the team is small, time-to-market matters more than brand differentiation, or the domain is well-served by existing systems (Material, Ant Design, Radix).

**Extend an existing system when**: you need a foundation but with domain-specific components on top. Most teams end up here.

## Design Tokens

Variables that encode design decisions. The bridge between design intent and code implementation.

### Token Layers
- **Global tokens**: raw values. `color-blue-500: #3B82F6`, `spacing-4: 16px`
- **Semantic tokens**: purpose-mapped. `color-primary: color-blue-500`, `spacing-component-gap: spacing-4`
- **Component tokens**: scoped to a component. `button-padding: spacing-component-gap`

### Token Categories
| Category | Examples |
|---|---|
| Color | Primary, secondary, neutral, semantic (success, error, warning, info) |
| Typography | Font families, sizes, weights, line heights, letter spacing |
| Spacing | Consistent scale (4px base: 4, 8, 12, 16, 24, 32, 48, 64) |
| Elevation | Shadow definitions for depth (low, medium, high) |
| Border | Radius (none, small, medium, large, full), widths |
| Motion | Duration (fast, normal, slow), easing curves |

### Implementation
- Store tokens in a format that can be consumed by both design tools and code (JSON, YAML)
- Generate platform-specific outputs: CSS custom properties, Tailwind config, iOS/Android values
- Version tokens independently from components

## Component API Conventions

- **Props over configuration objects**: `<Button variant="primary" size="lg">` not `<Button config={{variant: "primary", size: "lg"}}>`
- **Variants**: predefined visual options (primary, secondary, ghost, destructive)
- **States**: interactive states (default, hover, active, disabled, loading, error)
- **Sizes**: consistent scale (sm, md, lg) applied uniformly across components
- **Composition**: components should be composable. `<Card><CardHeader /><CardBody /></Card>` over `<Card header="..." body="..." />`

## Documentation Standards

For each component, document:
- **When to use**: the scenario this component is designed for
- **When NOT to use**: and what to use instead
- **Props/API**: all props with types, defaults, and descriptions
- **States**: all visual states with examples
- **Accessibility**: keyboard behavior, ARIA attributes, screen reader behavior
- **Examples**: common usage patterns with code

## Versioning

- Use semantic versioning for the design system package
- Breaking changes (removing props, changing defaults) require a major version bump
- Document migration paths for breaking changes
- Deprecate before removing: mark as deprecated in one version, remove in the next
