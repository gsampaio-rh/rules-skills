"""Captured response storage and discovery for the eval pipeline.

Handles reading, writing, and inspecting agent responses under responses/.
Automated capture via auto_capture.py; manual paste workflow via manual_capture.py.
"""

from pathlib import Path

from common import RESPONSES_DIR


def _is_valid_response(text: str) -> bool:
    return bool(text.strip()) and not text.strip().startswith("<!-- Response for:")


def responses_dir(model: str) -> Path:
    return RESPONSES_DIR / model


def discover_models() -> list[str]:
    if not RESPONSES_DIR.exists():
        return []
    return sorted(
        d.name for d in RESPONSES_DIR.iterdir()
        if d.is_dir() and any(d.glob("*.md"))
    )


def load_response(test_id: str, model: str | None = None) -> str | None:
    if model:
        path = responses_dir(model) / f"{test_id}.md"
        if path.exists():
            text = path.read_text().strip()
            if _is_valid_response(text):
                return text

    path = RESPONSES_DIR / f"{test_id}.md"
    if path.exists():
        text = path.read_text().strip()
        if _is_valid_response(text):
            return text
    return None


def has_response(test_id: str, model: str | None = None) -> bool:
    if model:
        return load_response(test_id, model) is not None

    if load_response(test_id) is not None:
        return True

    for subdir in discover_models():
        if load_response(test_id, subdir) is not None:
            return True
    return False


def save_response(test_id: str, model: str, response: str) -> Path:
    out_dir = responses_dir(model)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{test_id}.md"
    path.write_text(response)
    return path


def create_response_file(test_id: str) -> Path:
    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
    path = RESPONSES_DIR / f"{test_id}.md"
    if not path.exists():
        path.write_text(
            f"<!-- Response for: {test_id} -->\n"
            f"<!-- Paste the agent's full response below this line -->\n\n"
        )
    return path


def count_captured(dataset: list[dict], model: str | None) -> int:
    return sum(1 for t in dataset if load_response(t["id"], model))


def capture_status(test_id: str, model: str | None) -> str:
    return "has response" if load_response(test_id, model) else "needs capture"


def print_eval_plan(dataset: list[dict], model: str | None = None) -> None:
    print(f"Would evaluate {len(dataset)} test cases:\n")
    for t in dataset:
        status = capture_status(t["id"], model)
        dims = list(t.get("rubric", {}).keys()) or ["behavioral", "negative"]
        print(f"  {t['id']:50s} [{t.get('difficulty', '?'):6s}] {status} dims={dims}")


def print_compare(dataset: list[dict], models: list[str]) -> None:
    print("\n" + "=" * 70)
    print("MODEL COMPARISON")
    print("=" * 70)

    for m in models:
        count = count_captured(dataset, m)
        print(f"  {m}: {count}/{len(dataset)} responses captured")
