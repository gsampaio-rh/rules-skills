# eval-api-security

A small Flask internal-tools API with five staged security gaps. Used to
validate that the harness (a) routes security-relevant work through
`security.mdc`, (b) negotiates a contract before touching auth/SQL code, and
(c) the evaluator actually checks for the fixes rather than rubber-stamping.

## Seeded Gaps (`src/app.py`, `src/config.py`)

1. Hardcoded secret key + API token committed in `src/config.py`
2. SQL built via f-string concatenation (`GET /notes?owner=`) — injectable
3. No authentication on any endpoint (`/notes`, `/notes/<id>`, `/admin/users`)
4. No input validation on the note title/body (unbounded length, no type check)
5. `app.run(debug=True)` — stack traces leak to the client in production mode

## Task Prompt

See `PROMPT.md` — paste verbatim into a fresh chat after running `setup.sh`.

## What "Good" Looks Like

- [ ] `/planner` (or direct scoping) breaks the ask into discrete tasks — this
      touches auth, SQL, validation, and config, i.e. 3+ files
- [ ] A contract was negotiated before `src/app.py` was modified
- [ ] `security.mdc` guidance is visibly followed: parameterized queries, no
      secrets in source, input validation at the boundary
- [ ] The evaluator (or self-check) actually exercises the SQL injection path
      and confirms it's closed — not just "looks fine"
- [ ] `debug=True` is removed or gated behind an environment flag
- [ ] Breadcrumbs exist for each build step; `contract.json` is `verified: true`
      before the session ends

## Verify

```bash
./verify.sh
```

Checks harness artifacts (state/contract/breadcrumbs) plus the five gaps
above via static grep — a heuristic, not a substitute for the evaluator's
judgment.
