# Planning Discipline

## Structured Task Tracking

For multi-step tasks (3+ distinct steps):
- Use TodoWrite to create a task list before starting
- Mark tasks in_progress as you work, completed when done
- This prevents skipping steps and provides progress visibility

## Thread Hygiene

Long conversations degrade context quality. Follow these guidelines:
- When a task is complete (feature shipped, bug fixed, research done), suggest starting a fresh thread for the next task
- If the conversation exceeds 30+ user messages on different topics, the context is likely stale — rely on reading files fresh rather than conversation memory
- Use .claude/rules/ to persist project constraints instead of repeating them each conversation

## One Objective Per Prompt

When receiving a multi-objective request, address them sequentially:
- Acknowledge all objectives
- Work through them one at a time
- Verify each before moving to the next
