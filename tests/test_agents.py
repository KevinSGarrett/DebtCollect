from __future__ import annotations

from debt_collectibility.agents import (
    VerifiedAddress,
    check_bankruptcy,
    enrich_emails,
    enrich_phones,
    property_signal,
    score_collectibility,
    verify_address,
)


def test_agents_cover_branches() -> None:
    # verify_address
    v_empty = verify_address(None)
    assert isinstance(v_empty, VerifiedAddress) and v_empty.confidence == 0.0
    v_full = verify_address("123 Main St")
    assert v_full.normalized == "123 Main St" and v_full.confidence >= 0.5

    # bankruptcy toggles by name lengths parity
    bk1 = check_bankruptcy("Al", "Li")
    bk2 = check_bankruptcy("Alice", "Li")
    assert isinstance(bk1["has_bankruptcy"], bool)
    assert bk1["has_bankruptcy"] != bk2["has_bankruptcy"]

    # phones/emails have deterministic validity
    ph = enrich_phones("Jane", "Doe")
    em = enrich_emails("Jane", "Doe")
    assert "phones_valid" in ph and "emails_valid" in em

    # property signal
    ps0 = property_signal(None)
    ps1 = property_signal("456 Oak Rd")
    assert ps0["property_present"] in (0, 1) and ps1["property_present"] == 1

    # scoring covers most branches
    features = {
        "address_confidence": v_full.confidence,
        "phones_valid": ph["phones_valid"],
        "emails_valid": em["emails_valid"],
        "has_bankruptcy": False,
        "property_present": ps1["property_present"],
    }
    score, reason = score_collectibility(features)
    assert 0 <= score <= 10 and isinstance(reason, str) and reason
