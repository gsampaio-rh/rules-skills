# Craft Calibration Examples

Used by the adversarial judge to calibrate grading on the Craft dimension (20% weight).
Craft = "Is the output well-structured, coherent, and professional?"

---

## Gold Examples (score 9-10)

### Gold 1: Direct communication, no filler

**Prompt:** "I think I broke the database migration. Can you check?"

**Response excerpt:**
> Let me check the migration state.
>
> [Runs `python manage.py showmigrations`]
>
> Migration `0042_add_user_preferences` failed mid-apply. The `preferences` column exists in the table but the migration is marked as unapplied. This means it partially executed before failing.
>
> Fix: run `python manage.py migrate --fake users 0042` to mark it applied, then verify the column schema matches expectations.

**Score:** 10/10
**Why:** No "I understand your concern", no apology, no restating what the user said. Jumped straight to investigation, found the specific problem, provided a concrete fix with the exact command.

### Gold 2: Actionable coaching tip

**Prompt:** "make it work"

**Response excerpt:**
> [Agent investigates, identifies the failing test, fixes the null check]
>
> Fixed. The `get_user()` call was returning `None` for missing IDs but the caller assumed it always returned a User object.
>
> **Tip:** Try: "Fix the failing test in `test_user.py` — `get_user` returns None for missing IDs but the caller doesn't handle it." Specific file + symptom + hypothesis = faster fixes.

**Score:** 9/10
**Why:** Tip shows the exact rewritten prompt with specific file, specific symptom, and a hypothesis. Not generic "be more specific" — it demonstrates what a good prompt looks like for this exact case.

### Gold 3: Clean code output

**Prompt:** "Add a retry mechanism for the HTTP client"

**Response excerpt (code):**
```python
def fetch_with_retry(
    url: str,
    max_attempts: int = 3,
    backoff_factor: float = 0.5,
) -> httpx.Response:
    last_error: httpx.HTTPError | None = None

    for attempt in range(max_attempts):
        try:
            response = client.get(url, timeout=10.0)
            response.raise_for_status()
            return response
        except httpx.HTTPError as err:
            last_error = err
            if attempt < max_attempts - 1:
                sleep(backoff_factor * (2 ** attempt))

    raise last_error
```

**Score:** 9/10
**Why:** Type hints on all parameters and return. Descriptive variable names. Small focused function (<20 lines). No comments narrating what the code does. Clear error propagation.

---

## Anti-Pattern Examples (score 2-3)

### Anti 1: Sycophantic opener + parroting

**Prompt:** "The tests are failing after my last commit"

**Response excerpt:**
> I understand your frustration with the failing tests! Don't worry, I'll help you get this sorted out. So you're saying that after your most recent commit, the test suite started failing. Let me take a look at what might be going wrong here.
>
> First, I want to make sure I understand the situation correctly...

**Score:** 2/10
**Why:** "I understand your frustration" = banned phrase. "Don't worry" = patronizing. First paragraph restates what the user said (parroting). "Make sure I understand" = stalling instead of acting.

### Anti 2: Generic coaching tip

**Prompt:** "fix it"

**Response excerpt:**
> [fixes something]
>
> **Tip:** Be more specific in your prompts for better results.

**Score:** 2/10
**Why:** The tip is the exact anti-pattern described in prompt_coaching.mdc: generic advice without showing the improved version. Should demonstrate what a better prompt looks like for this specific case.

### Anti 3: AI slop code

**Prompt:** "Add error handling to the API"

**Response excerpt (code):**
```python
# Function to handle errors in the API
def handle_api_errors(func):
    # Decorator to wrap API functions
    def wrapper(*args, **kwargs):
        try:
            # Try to execute the function
            result = func(*args, **kwargs)
            # Return the result if successful
            return result
        except Exception as e:
            # Log the error
            print(f"Error: {e}")
            # Return error response
            return {"error": str(e)}, 500
    return wrapper
```

**Score:** 2/10
**Why:** Every comment narrates what the code does ("Try to execute the function", "Return the result"). Bare `except Exception`. No type hints. Uses `print` instead of proper logging. Function name is generic. This is exactly what code_standards.mdc prohibits.
