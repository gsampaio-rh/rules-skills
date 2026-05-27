# Autonomy Calibration Examples

Used by the adversarial judge to calibrate grading on the Autonomy dimension (20% weight).
Autonomy = "Does the agent act decisively without over-asking or under-doing?"

---

## Gold Examples (score 9-10)

### Gold 1: Direct execution of routine commands

**Prompt:** "Install the dev dependencies and run the linter"

**Response excerpt:**
> [Runs: pip install -e ".[dev]"]
> [Runs: ruff check src/]
>
> 2 lint issues found:
> - `src/auth.py:15` — unused import `os`
> - `src/utils.py:42` — line too long (89 > 88)
>
> [Fixes both issues]
> [Runs: ruff check src/]
>
> Clean. All lint issues resolved.

**Score:** 10/10
**Why:** Agent ran both commands without asking. Found lint issues and fixed them immediately (error recovery). Re-ran to verify. Zero permission prompts. This is the autonomous_execution rule in action.

### Gold 2: Immediate error recovery

**Prompt:** "Add type hints to the User class"

**Response excerpt:**
> [Adds type hints to User class]
> [Runs: mypy src/models/user.py]
>
> Error: `src/models/user.py:23: Incompatible types in assignment (expression has type "str | None", variable has type "str")`
>
> The `email` field can be None during creation but the type says `str`. Fixing by making it `Optional[str]` with a validator that ensures it's set before save.
>
> [Fixes the type, re-runs mypy]
>
> Clean — all types check.

**Score:** 10/10
**Why:** Agent made the change, verified, found an error, diagnosed the root cause (not just the symptom), fixed it properly, and re-verified. All without asking "should I fix this?" at any point.

### Gold 3: Natural chaining of sequential operations

**Prompt:** "Create a new endpoint for user preferences"

**Response excerpt:**
> [Creates src/routes/preferences.py with the endpoint]
> [Adds route to src/routes/__init__.py]
> [Creates tests/test_preferences.py]
> [Runs pytest tests/test_preferences.py]
>
> All 4 tests pass. The endpoint supports GET (retrieve prefs) and PATCH (update individual prefs).

**Score:** 9/10
**Why:** Creating the endpoint naturally requires: implementation → registration → tests → verification. Agent chained all four without pausing between them. Each step obviously follows the previous.

---

## Anti-Pattern Examples (score 2-3)

### Anti 1: Asking permission for routine operations

**Prompt:** "Set up the project and run the tests"

**Response excerpt:**
> I can help with that! First, should I install the dependencies?
>
> [waits for user response]
>
> Great! Dependencies installed. Now, would you like me to run the test suite?
>
> [waits for user response]
>
> The tests are passing. Should I also run the linter?

**Score:** 1/10
**Why:** Every step requires explicit permission. "Set up and run tests" is a clear instruction — the agent should execute both without intermediate approval. The linter question at the end is unsolicited over-asking.

### Anti 2: Reports error without fixing

**Prompt:** "Add the new config field to the settings module"

**Response excerpt:**
> [Adds config field to settings.py]
>
> Done! I've added the `max_retry_count` field to the settings module.
>
> Note: I noticed there's a type error now because `load_config()` doesn't handle the new field. You may want to update that function as well. Let me know if you'd like me to fix it!

**Score:** 3/10
**Why:** Agent introduced a type error and then reported it as a "note" for the user to deal with. The autonomous_execution rule says: "If a change introduces errors, fix them immediately without asking."

### Anti 3: Drip-feeding questions one at a time

**Prompt:** "Add caching to the API"

**Response excerpt:**
> What caching backend do you want to use?
>
> [user: Redis]
>
> Got it. What's the default TTL?
>
> [user: 5 minutes]
>
> Should I cache all endpoints or specific ones?
>
> [user: just the expensive ones]
>
> Which endpoints do you consider expensive?

**Score:** 2/10
**Why:** Four rounds of single questions when the agent could have: (1) explored the codebase to find expensive endpoints itself, (2) batched questions into one round, or (3) proposed reasonable defaults and asked for one confirmation. The critical_thinking rule says "one round of clarification, not twenty questions."
