import re

import phonenumbers

USPS_ABBREVIATIONS = {
    "STREET": "ST",
    "AVENUE": "AVE",
    "BOULEVARD": "BLVD",
    "ROAD": "RD",
    "DRIVE": "DR",
    "COURT": "CT",
    "LANE": "LN",
    "TERRACE": "TER",
}


def normalize_name(first: str | None, last: str | None) -> str:
    parts = [p.strip() for p in [first or "", last or ""] if p and p.strip()]
    return " ".join(parts).upper()


def _usps_abbrev(street: str) -> str:
    s = street.upper()
    for long, short in USPS_ABBREVIATIONS.items():
        s = re.sub(rf"\b{long}\b", short, s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_address(
    line1: str, line2: str | None, city: str, state: str, zipcode: str
) -> dict[str, str]:
    line1_norm = _usps_abbrev(line1 or "")
    line2_norm = _usps_abbrev(line2 or "") if line2 else ""
    city_norm = re.sub(r"\s+", " ", (city or "").upper()).strip()
    state_norm = (state or "").upper().strip()
    zip5 = (zipcode or "").strip()[:5]
    return {
        "line1": line1_norm,
        "line2": line2_norm,
        "city": city_norm,
        "state": state_norm,
        "zip": zip5,
    }


def to_e164(raw_phone: str, default_region: str = "US") -> str | None:
    if not raw_phone:
        return None
    try:
        parsed = phonenumbers.parse(raw_phone, default_region)
        if not phonenumbers.is_possible_number(parsed) or not phonenumbers.is_valid_number(parsed):
            return None
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        return None


def usps_abbreviate(street: str) -> str:
    """Public helper to abbreviate common street suffixes using USPS style."""
    return _usps_abbrev(street or "")
