---
paths:
  - "**/*.tsx"
  - "**/*.jsx"
  - "**/*.html"
  - "**/*.css"
---
# UX Research Methods

Practical guide to understanding users. Choose the method based on what you need to learn, not what's familiar.

## Method Selection

| You need to learn... | Use... | Sample size |
|---|---|---|
| WHY users behave a certain way | User interviews | 5-8 per segment |
| WHERE users struggle in a flow | Usability testing | 5 per round |
| WHAT the full experience looks like | Journey mapping | Based on interview data |
| WHO your users are | Persona construction | Based on research data |
| HOW MANY users are affected | Surveys, analytics | 100+ for quantitative |

**Rule of thumb**: qualitative first (understand the problem), quantitative second (measure the scale).

## User Interviews

**Goal**: understand motivations, mental models, pain points, and context of use.

**Question design**:
- Open-ended: "Tell me about the last time you..." not "Did you like...?"
- Behavioral: "What did you do?" not "What would you do?"
- Non-leading: "How was that experience?" not "Wasn't that frustrating?"
- Follow-up: "Why?" and "Tell me more about that" are your most powerful tools

**Anti-patterns**: leading questions, asking about hypothetical future behavior, interviewing stakeholders instead of users, not recording/transcribing.

## Usability Testing

**Goal**: observe real users attempting real tasks with your product.

**Task design**:
- Scenario-based: "You want to find a doctor near your home. Show me how you'd do that."
- Not instructional: "Click the search button" tests nothing
- Ordered by priority: test the most critical flows first

**Think-aloud protocol**: ask users to verbalize their thoughts as they work. "What are you thinking right now?" when they pause.

**5 users catch ~85% of usability issues** (Nielsen). Run multiple rounds of 5 rather than one round of 20.

## Journey Mapping

**Goal**: visualize the end-to-end experience across touchpoints.

**Components**:
- **Stages**: the phases of the user's experience (awareness, consideration, use, support)
- **Actions**: what the user does at each stage
- **Thoughts**: what they're thinking
- **Emotions**: how they feel (map highs and lows)
- **Pain points**: where things break down
- **Moments of truth**: where the experience is won or lost

**Build from research data**, not assumptions. A journey map based on stakeholder opinions is fiction.

## Persona Construction

**Goal**: represent user segments as concrete, relatable archetypes.

**Data-driven, not fictional**:
- Built from interview and behavioral data, not marketing demographics
- Focus on goals, behaviors, and pain points — not age/gender/stock photo
- 3-5 personas maximum. If you have 12, you have none.
- Each persona should lead to different design decisions. If two personas would use the product identically, merge them.

**Anti-patterns**: personas based on assumptions, personas that are just demographic profiles, too many personas, personas that never get referenced in design decisions.

## When to Use Qual vs Quant

- **Qualitative** (interviews, usability tests): early in the process, when you don't know WHAT questions to ask
- **Quantitative** (surveys, analytics, A/B tests): later, when you know WHAT to measure and need to know HOW MUCH
- **Mixed**: use qualitative findings to generate hypotheses, quantitative data to validate them
