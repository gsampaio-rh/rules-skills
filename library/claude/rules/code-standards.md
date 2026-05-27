# Code Standards

## "Code for AI, Optimize for Humans"

Write code that both AI and humans can easily understand, modify, and extend. Make intent explicit, not implicit.

## Explicit > Implicit
- Prefer explicit patterns over clever abstractions
- Make dependencies clear and obvious
- Use type hints and interfaces liberally
- Name things descriptively, even if verbose

## Single Responsibility
- Each function does exactly one thing
- Each file has a single, clear purpose
- Small, focused functions (10-20 lines ideal, max 50)
- If a function needs a comment to explain what it does, split it

## DRY (Don't Repeat Yourself)
- Extract repeated code into reusable functions
- Share common logic through proper abstraction
- Maintain single sources of truth

## Meaningful Names
- Variables, functions, and classes should reveal their purpose
- Names should explain why something exists and how it's used
- Avoid abbreviations unless universally understood
- `handle_user_profile_update` > `handle_update`

## Smart Comments
- Don't comment on what the code does — make code self-documenting
- Use comments to explain **why** something is done a certain way
- Document APIs, complex algorithms, and non-obvious side effects
- Use `TODO:` for future improvements with context

## Clean Structure
- Keep related code together
- Organize code in a logical hierarchy
- Use consistent file and folder naming conventions
- Encapsulate implementation details, expose clear interfaces

## Code Quality
- Refactor continuously — leave code cleaner than you found it
- Fix technical debt early
- Write tests for edge cases and error conditions

## File and Function Sizing
- **Functions**: max 50 lines (ideally under 20)
- **Files**: max 300 lines (ideally under 200)
- **Classes**: max 500 lines (ideally under 200)
- Functions exceeding 30 lines should be justified; exceeding 50 requires refactoring

## What AI Handles Well
- Consistent patterns across codebase
- Type-safe code with explicit types
- Small, focused functions
- Clear interfaces between components

## What AI Struggles With
- Clever abstractions (AI may not understand)
- Implicit behavior (magic, hidden side effects)
- Large functions (hard to modify safely)
- Dynamic types (`any` makes AI's job harder)
