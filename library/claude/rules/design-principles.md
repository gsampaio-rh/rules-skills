# Design Principles: "Less but Better"

Additional methodology documentation in this repository loads automatically as rules when those files are in scope.

Our design philosophy synthesizes principles from master designers: **Dieter Rams** (less but better), **BJ Fogg** (behavior-driven simplicity), **Steve Jobs** (user-centric focus), **Jony Ive** (minimalist craftsmanship), and **Le Corbusier** (functionalism).

## Core Philosophy

### Good Design is Honest (Dieter Rams)
- **Transparency**: UI elements clearly communicate their function
- **No deception**: never mislead users about what actions will do
- **Clear feedback**: every interaction provides honest, immediate feedback
- **Error states**: show what went wrong and how to fix it

### Good Design is Unobtrusive (Dieter Rams)
- **Invisible when perfect**: the interface gets out of the user's way
- **Content first**: design supports content, never competes with it
- **Minimal chrome**: remove unnecessary UI elements
- **Progressive disclosure**: show only what's needed, when needed

### Good Design Makes a Product Useful (Dieter Rams + Le Corbusier)
- **Form follows function**: every element serves a clear purpose
- **Functional beauty**: beauty emerges from solving problems elegantly
- **No decoration**: remove decorative elements that don't enhance usability
- **Purpose-driven**: every screen, component, and interaction has a defined purpose

### Simplicity Through Focus (Steve Jobs)
- **One thing well**: each screen does one thing exceptionally well
- **Eliminate the unnecessary**: if it doesn't add value, remove it
- **Clarity over cleverness**: simple, obvious solutions over complex ones
- **Intuitive first**: users should understand without explanation

### Behavior-Driven Design (BJ Fogg)
**B=MAT Model**: Behavior = Motivation + Ability + Trigger
- **Motivation**: make the value proposition clear and compelling
- **Ability**: make actions easy to perform (reduce friction)
- **Trigger**: provide clear calls-to-action at the right moment
- **Reduce cognitive load**: break complex tasks into simple steps

### Craftsmanship (Jony Ive)
- **Pixel-perfect**: every detail matters, from spacing to typography
- **Consistent rhythm**: use systematic spacing and sizing (8px grid)
- **Refined interactions**: smooth animations, appropriate timing, natural feel
- **Quality over quantity**: fewer, polished features over many half-finished ones

## Visual Design

### Typography
- Clear typographic hierarchy guides users through content
- Readability-optimized typefaces, limited type scale (12/14/16/20/24/32px)
- Optimal line length: 45-75 characters

### Color
- Purposeful: colors communicate meaning, not just decoration
- WCAG AA contrast ratios minimum (4.5:1 for text)
- Limited palette: primary, secondary, neutral, semantic (error/success/warning/info)

### Spacing & Layout
- 8px grid system for all spacing
- Generous whitespace improves readability and focus
- Consistent alignment to a clear grid

## Interaction Design

### Clarity
- Obvious actions: users immediately understand what they can do
- Clear labels: descriptive, action-oriented
- Visual affordances: elements look clickable/tappable when they are
- State communication: hover, active, disabled, loading states

### Feedback
- Immediate response for every action
- Progress indication for long-running operations
- Clear, actionable error messages
- Appropriate success confirmation

### Efficiency
- Keyboard shortcuts for power users
- Smart defaults and remembered preferences
- Minimize steps to complete tasks

## Accessibility

### Universal Design
- **Keyboard navigation**: all functionality accessible via keyboard
- **Screen readers**: proper ARIA labels and semantic HTML
- **Color independence**: don't rely solely on color to convey information
- **Focus indicators**: clear focus states for keyboard navigation

### Inclusive Design
- Multiple input methods: mouse, keyboard, touch, voice
- Adjustable: allow text size and preference customization
- Error prevention before error recovery

### Responsive Design
- Mobile-first: design for smallest screen first, enhance for larger
- Breakpoints: mobile 320px+, tablet 768px+, desktop 1024px+
- Touch targets: minimum 44x44px
- Flexible layouts with relative units

## Design System
- Reusable components with consistent API
- Design tokens: colors, typography, spacing, shadows, borders
- Standard patterns: navigation, forms, feedback, layouts
- Documentation with usage guidelines for each component

## Questions to Ask When Designing
1. Does this solve a real problem?
2. Can we remove anything?
3. Is this the simplest solution?
4. Does this make the user's task easier?
5. Is this consistent with the rest of the system?
6. Will users understand this immediately?
7. Does this feel crafted?
8. Is this accessible to everyone?
