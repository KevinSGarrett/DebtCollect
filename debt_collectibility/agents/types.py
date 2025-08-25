from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class VerifiedAddress:
    raw: str | None
    normalized: str | None
    confidence: float


def verify_address(possible_address: str | None) -> VerifiedAddress:
    """Deterministic dummy: returns normalized == raw, confidence based on presence."""
    if not possible_address:
        return VerifiedAddress(raw=None, normalized=None, confidence=0.0)

    conf = 0.9 if len(possible_address) > 5 else 0.5
    return VerifiedAddress(
        raw=possible_address,
        normalized=possible_address.strip(),
        confidence=conf,
    )


def check_bankruptcy(first_name: str, last_name: str) -> dict[str, Any]:
    """Deterministic dummy bankruptcy flag for tests."""
    risky = (len(last_name) + len(first_name)) % 2 == 0
    return {"has_bankruptcy": risky, "chapter": "7" if risky else None}


def enrich_phones(first_name: str, last_name: str) -> dict[str, int]:
    """Deterministic dummy: pretend we found 1 phone and it is valid if name hash is odd."""
    valid = ((len(first_name) * 3 + len(last_name) * 7) % 2) == 1
    return {"phones_found": 1 if valid else 0, "phones_valid": int(valid)}


def enrich_emails(first_name: str, last_name: str) -> dict[str, int]:
    valid = ((len(first_name) + len(last_name)) % 3) == 0
    return {"emails_found": 1 if valid else 0, "emails_valid": int(valid)}


def property_signal(possible_address: str | None) -> dict[str, float | int]:
    has_addr = 1 if possible_address else 0
    return {"property_present": has_addr, "owner_occupied_likelihood": 0.6 if has_addr else 0.0}


def score_collectibility(features: dict[str, Any]) -> tuple[int, str]:
    """Very simple scoring to satisfy tests; Cursor will later replace with real model."""
    score = 0
    score += 2 if features.get("address_confidence", 0) >= 0.8 else 0
    score += 2 if features.get("phones_valid", 0) else 0
    score += 2 if features.get("emails_valid", 0) else 0
    score += 2 if not features.get("has_bankruptcy", False) else 0
    score += 2 if features.get("property_present", 0) else 0
    score = max(0, min(10, score))
    reason = "addr/phone/email/bk/property heuristic"
    return score, reason
