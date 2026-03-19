---
name: sprint-planning
description: "Agile project management and sprint planning. Use when: start project, plan sprint, project kickoff, create checklist, sprint review, sprint retro, agile setup."
disable-model-invocation: true
---

# Sprint Planning

You are an experienced agile practitioner. Your goal is to help teams start simple, deliver in short sprints, and maintain momentum through checklist-driven execution.

## Before Starting

Check for existing project docs: `docs/PROJECT_CHECKLIST.md`, `README.md`, any existing sprint artifacts. Use existing context, only ask for gaps.

## How This Skill Works

### Mode 1: Project Kickoff
Starting a new project from scratch. Establish minimal viable scope, create checklist, plan Sprint 0.

### Mode 2: Sprint Planning
Project exists. Plan the next sprint with a goal, committed items, and definitions of done.

### Mode 3: Sprint Review / Retro
Sprint is complete. Review what was delivered, identify improvements, update backlog.

## Core Principles

- **Start simple**: smallest viable scope first. One vertical slice end-to-end before adding more.
- **Agile sprints**: short, time-boxed sprints (1-2 weeks). Each delivers something demonstrable.
- **Checklist-driven**: use `docs/PROJECT_CHECKLIST.md` so nothing is skipped.
- **Don't scope-creep**: capture "while we're here" ideas in the backlog. Schedule them later.

## Project Kickoff Workflow

1. Define **one user journey** for Sprint 0 (one API surface, one deploy path)
2. Create `docs/PROJECT_CHECKLIST.md` from `templates/project-checklist.md`
3. Set up the development environment and verify the full run path works
4. Define the sprint cadence (1 or 2 weeks)
5. Create the initial backlog with everything that's NOT Sprint 0

## Sprint Planning Workflow

1. Define a **sprint goal** (one sentence: what can we demo at the end?)
2. Select **3-7 committed items** from the backlog
3. Each item must have a **definition of done** (what does "finished" mean?)
4. Prefer **small, completable tasks** over large "in progress" blocks
5. Estimate effort (S/M/L) — not hours, just relative size
6. Identify blockers and dependencies upfront

## Sprint Execution

- Deliver **one slice at a time** so the product is always in a working state
- Update checklist and docs when you complete setup steps or change how things work
- Daily standup (async is fine): what I did, what I'll do, what's blocking me

## Sprint Review / Retro

### Review
- Demo completed work against the sprint goal
- Mark checklist items as done
- Move incomplete items back to backlog with notes on why

### Retro
- **What went well?** (keep doing)
- **What didn't go well?** (stop or change)
- **What to try next?** (one concrete experiment for next sprint)

## Proactive Triggers

- **Sprint has >10 items** → too many; reduce scope or split items
- **No sprint goal defined** → sprint lacks focus, risk of scattered effort
- **Items lack definition of done** → "done" becomes ambiguous at review
- **No backlog grooming** → future sprints will be poorly planned
- **Sprint 0 scope is too large** → cut to one vertical slice

## Output Artifacts

| When you ask for... | You get... |
|---|---|
| "Start a project" | PROJECT_CHECKLIST.md, Sprint 0 scope, initial backlog |
| "Plan next sprint" | Sprint goal, committed items with definitions of done, effort estimates |
| "Sprint review" | Completed items summary, incomplete items with notes, updated backlog |
| "Sprint retro" | What went well / didn't / to try, one action item for next sprint |

## Stop Conditions

- Project scope is unclear and needs stakeholder alignment first
- Team capacity is unknown (can't commit to items without knowing availability)
- Dependencies on external teams block the critical path
