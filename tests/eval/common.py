"""Shared utilities for the eval pipeline."""

from pathlib import Path

import yaml

EVAL_DIR = Path(__file__).parent
DATASET_PATH = EVAL_DIR / "dataset.yaml"
RESPONSES_DIR = EVAL_DIR / "responses"
HISTORY_DIR = EVAL_DIR / "history" / "runs"


def load_dataset() -> list[dict]:
    with open(DATASET_PATH) as f:
        return yaml.safe_load(f)


def filter_dataset(
    dataset: list[dict],
    pattern: str | None = None,
    category: str | None = None,
    difficulty: str | None = None,
) -> list[dict]:
    result = dataset

    if pattern:
        f = pattern.lower()
        result = [
            t for t in result
            if f in t["id"].lower()
            or f in t.get("category", "").lower()
            or any(f in tgt.lower() for tgt in t.get("targets", []))
        ]

    if category:
        result = [t for t in result if t.get("category") == category]

    if difficulty:
        result = [t for t in result if t.get("difficulty") == difficulty]

    return result
