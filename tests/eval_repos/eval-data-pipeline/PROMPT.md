# Initial Prompt

Paste this into a fresh chat once the workspace is open:

> This nightly sales pipeline keeps breaking in production and nobody can
> tell why until the on-call engineer greps through terminal scrollback.
> Make it production-ready.

Deliberately vague — do not clarify further unless the agent asks. If it
asks a clarifying question, a reasonable answer is:

> It's run as a cron job with no one watching. We need it to survive bad
> input, tell us what happened, and have some tests so we stop finding out
> about breakage from the pipeline just silently not running.
