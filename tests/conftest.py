"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from src.api.rate_limit import reset_rate_limits


@pytest.fixture(autouse=True)
def _reset_rate_limits() -> None:
    """Isolate rate-limit counters so the suite does not share global state."""
    reset_rate_limits()
    yield
    reset_rate_limits()
