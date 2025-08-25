"""Utilities: simple, deterministic mocks + helpers."""

from __future__ import annotations


def has_api_keys() -> bool:
    """Detect if real API keys are present (mocked off by default)."""
    # Extend as needed to detect env keys; default false for deterministic tests.
    return False


def deterministic_hash(name: str) -> int:
    """Return a small deterministic hash in the 0..10 range for tests."""
    return sum(ord(c) for c in name) % 11
