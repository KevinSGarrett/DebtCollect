from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


def _fresh_year(date_str: str | None, year_threshold: int = 2024) -> bool:
    if not date_str:
        return False
    try:
        year = int(str(date_str)[:4])
        return year >= year_threshold
    except Exception:
        return False


def run(debtor: dict[str, Any], dx: Any) -> dict[str, Any] | None:
    debtor_id = debtor.get("id")
    # Contactability (<=35)
    try:
        phones = dx.list_related("phones", {"debtor_id": {"_eq": debtor_id}}, limit=100)
    except Exception:
        phones = []
    try:
        emails = dx.list_related("emails", {"debtor_id": {"_eq": debtor_id}}, limit=100)
    except Exception:
        emails = []
    contactability = 0
    has_verified_phone = any(
        p.get("is_verified") and (p.get("line_type") in ("mobile", "voip", None)) for p in phones
    )
    has_verified_email = any(e.get("is_verified") for e in emails)
    if has_verified_phone:
        contactability += 25
    if has_verified_email:
        contactability += 10
    if has_verified_phone and has_verified_email:
        contactability = min(35, contactability + 5)

    # Address quality (<=10)
    address_quality = 10 if debtor.get("usps_standardized") else 0

    # Bankruptcy penalty (>= -20)
    try:
        cases = dx.list_related("bankruptcy_cases", {"debtor_id": {"_eq": debtor_id}}, limit=5)
    except Exception:
        cases = []
    bankruptcy_penalty = 0
    for c in cases:
        discharged = c.get("discharged_date")
        chapter = c.get("chapter")
        if chapter and str(chapter).startswith("7"):
            # recent discharge within 3 years = -20, 3–7 years -10
            if discharged and _fresh_year(discharged, datetime.now(UTC).year - 3):
                bankruptcy_penalty = min(bankruptcy_penalty, -20)
            elif discharged and _fresh_year(discharged, datetime.now(UTC).year - 7):
                bankruptcy_penalty = min(bankruptcy_penalty, -10)
            else:
                bankruptcy_penalty = min(bankruptcy_penalty, -5)

    # Capacity proxy (<=25)
    try:
        properties = dx.list_related("properties", {"debtor_id": {"_eq": debtor_id}}, limit=5)
    except Exception:
        properties = []
    market_value: float | None = None
    for p in properties:
        mv = p.get("market_value") or p.get("assessed_value")
        if mv is None:
            continue
        try:
            mv_num = float(mv)
        except (TypeError, ValueError):
            continue
        market_value = max(market_value or 0.0, mv_num)
    debt_owed_raw = debtor.get("debt_owed") or 0
    try:
        debt_owed = float(debt_owed_raw)
    except (TypeError, ValueError):
        debt_owed = 0.0
    capacity = 0
    if market_value is not None:
        ratio = market_value / (debt_owed + 1.0)
        if ratio >= 5:
            capacity = 25
        elif ratio >= 1:
            capacity = int(25 * (ratio / 5))
    else:
        # If only census median stored
        for p in properties:
            if p.get("value_source") == "census_zip_median" and p.get("market_value") is not None:
                try:
                    mv_num = float(p["market_value"])
                except (TypeError, ValueError):
                    continue
                ratio = mv_num / (debt_owed + 1.0)
                capacity = min(25, int(25 * (ratio / 5)))
    if any(p.get("owner_occupied") for p in properties):
        capacity = min(25, capacity + 3)

    # Business (<=10)
    try:
        business_confidence = int(debtor.get("business_confidence") or 0)
    except (TypeError, ValueError):
        business_confidence = 0
    business_points = min(
        10, (6 if business_confidence >= 50 else 0) + (4 if business_confidence >= 70 else 0)
    )

    # Stability/Freshness (<=10)
    stability = 0
    if debtor.get("usps_standardized"):
        stability += 3
    if any(_fresh_year(p.get("last_seen")) for p in phones):
        stability += 4
    # email verified recently is not tracked; approximate with is_verified
    if has_verified_email:
        stability += 3
    stability = min(10, stability)

    score = (
        50
        + contactability
        + address_quality
        + capacity
        + business_points
        + stability
        + bankruptcy_penalty
    )
    score = _clamp(int(score), 1, 100)

    reasons = []
    if has_verified_phone:
        reasons.append("verified phone")
    if has_verified_email:
        reasons.append("verified email")
    if debtor.get("usps_standardized"):
        reasons.append("address standardized")
    if bankruptcy_penalty:
        reasons.append("bankruptcy history")
    reason_text = ", ".join(reasons) or "baseline"

    snapshot = {
        "debtor_id": debtor_id,
        "score": score,
        "reason": reason_text,
        "created_at": datetime.now(UTC).isoformat(),
    }
    dx.create_row(
        "scoring_snapshots",
        {
            **snapshot,
            "inputs": "{}",
        },
    )
    return {"collectibility_score": score, "collectibility_reason": reason_text}
