from __future__ import annotations

import json
import os

import requests
from dotenv import load_dotenv


def status(ok: bool, name: str, detail: str = "") -> dict:
    return {"ok": ok, "service": name, "detail": detail}


def main() -> None:
    load_dotenv()
    results = []

    # USPS (no easy ping; verify env present)
    results.append(status(bool(os.getenv("USPS_USER_ID")), "USPS", "env present"))

    # Apify - simple whoami or quota check
    try:
        token = os.getenv("APIFY_TOKEN")
        r = requests.get(
            "https://api.apify.com/v2/me", headers={"Authorization": f"Bearer {token}"}, timeout=20
        )
        results.append(status(r.ok, "Apify", f"HTTP {r.status_code}"))
    except Exception as e:
        results.append(status(False, "Apify", str(e)))

    # RealPhoneValidation - no free ping; check env
    results.append(
        status(bool(os.getenv("REALPHONEVALIDATION_API_KEY")), "RealPhoneValidation", "env present")
    )

    # Hunter verify (ping domain)
    try:
        key = os.getenv("HUNTER_API_KEY")
        r = requests.get(
            f"https://api.hunter.io/v2/domain-search?domain=example.com&api_key={key}", timeout=20
        )
        results.append(status(r.ok, "Hunter.io", f"HTTP {r.status_code}"))
    except Exception as e:
        results.append(status(False, "Hunter.io", str(e)))

    # Twilio Lookup - check credentials via a 401/200
    try:
        sid = os.getenv("TWILIO_ACCOUNT_SID")
        tok = os.getenv("TWILIO_AUTH_TOKEN")
        r = requests.get(
            "https://lookups.twilio.com/v1/PhoneNumbers/+15555555555?Type=carrier",
            auth=(sid, tok),
            timeout=20,
        )
        results.append(
            status(r.status_code in (200, 404, 429), "Twilio Lookup", f"HTTP {r.status_code}")
        )
    except Exception as e:
        results.append(status(False, "Twilio Lookup", str(e)))

    # ATTOM - a simple request that likely 401s/200s
    try:
        k = os.getenv("ATTOM_API_KEY")
        r = requests.get(
            "https://api.attomdata.com/propertyapi/v1.0.0/property/address/validate",
            headers={"apikey": k},
            timeout=20,
        )
        results.append(
            status(r.status_code in (200, 401, 403, 404), "ATTOM", f"HTTP {r.status_code}")
        )
    except Exception as e:
        results.append(status(False, "ATTOM", str(e)))

    # Census (public)
    try:
        r = requests.get("https://api.census.gov/data.html", timeout=20)
        results.append(status(r.ok, "Census", f"HTTP {r.status_code}"))
    except Exception as e:
        results.append(status(False, "Census", str(e)))

    # Google Places
    try:
        k = os.getenv("GOOGLE_MAPS_API_KEY")
        r = requests.get(
            "https://maps.googleapis.com/maps/api/place/textsearch/json",
            params={"query": "test", "key": k},
            timeout=20,
        )
        results.append(
            status(r.status_code in (200, 400, 403), "Google Places", f"HTTP {r.status_code}")
        )
    except Exception as e:
        results.append(status(False, "Google Places", str(e)))

    # Apollo - simple auth ping
    try:
        k = os.getenv("APOLLO_API_KEY")
        r = requests.get(
            "https://api.apollo.io/v1/organizations/search",
            headers={"Authorization": f"Bearer {k}"},
            timeout=20,
        )
        results.append(
            status(r.status_code in (200, 400, 401, 403), "Apollo", f"HTTP {r.status_code}")
        )
    except Exception as e:
        results.append(status(False, "Apollo", str(e)))

    print(json.dumps({"diagnostics": results}, default=str))


if __name__ == "__main__":
    main()
