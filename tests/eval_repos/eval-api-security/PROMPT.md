# Initial Prompt

Paste this into a fresh chat once the workspace is open:

> We're about to expose this internal notes API to a partner integration.
> Harden it for external use: add authentication, fix any injection
> vulnerabilities, stop leaking secrets, and add input validation on the
> note endpoints. Don't change the existing URL routes or response shapes —
> partners already have a draft integration against them.

## Optional Follow-Up (after the first pass)

> Also make sure the app doesn't leak stack traces to clients in production.
