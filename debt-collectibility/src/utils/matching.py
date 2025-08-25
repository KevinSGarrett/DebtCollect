from rapidfuzz import fuzz

from .normalize import usps_abbreviate


def name_similarity(a: str, b: str) -> int:
    a_norm = (a or "").upper().strip()
    b_norm = (b or "").upper().strip()
    if not a_norm or not b_norm:
        return 0
    return int(fuzz.token_sort_ratio(a_norm, b_norm))


def street_similarity(a: str, b: str) -> int:
    a_norm = usps_abbreviate((a or "").upper().strip())
    b_norm = usps_abbreviate((b or "").upper().strip())
    if not a_norm or not b_norm:
        return 0
    return int(fuzz.ratio(a_norm, b_norm))


def match_name_address(debtor: dict, candidate: dict) -> int:
    debtor_name = ((debtor.get("first_name") or "") + " " + (debtor.get("last_name") or "")).strip()
    candidate_name = candidate.get("name") or candidate.get("full_name") or ""
    name_score = name_similarity(debtor_name, candidate_name)

    debtor_state = (debtor.get("state") or debtor.get("address_state") or "").upper().strip()
    candidate_state = (candidate.get("state") or "").upper().strip()
    debtor_zip = (debtor.get("zip") or debtor.get("address_zip") or "").strip()[:5]
    candidate_zip = (candidate.get("zip") or "").strip()[:5]

    if debtor_state and candidate_state and debtor_state != candidate_state:
        return 0
    if debtor_zip and candidate_zip and debtor_zip != candidate_zip:
        return 0

    debtor_street = (debtor.get("address_line1") or debtor.get("street") or "").upper().strip()
    candidate_street = (
        (candidate.get("street") or candidate.get("address_line1") or "").upper().strip()
    )
    street_score = street_similarity(debtor_street, candidate_street)

    # Require strong street match
    if street_score < 85:
        return 0

    return int(0.6 * name_score + 0.4 * street_score)
