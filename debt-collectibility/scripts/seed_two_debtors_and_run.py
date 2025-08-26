from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.directus_client import DirectusClient


def upsert_debtor(
    dx: DirectusClient, first: str, last: str, address: dict[str, str], debt: float
) -> int:
    # try find existing
    existing = dx.list_related(
        "debtors",
        {
            "first_name": {"_eq": first},
            "last_name": {"_eq": last},
            "address_line1": {"_eq": address["line1"]},
            "zip": {"_eq": address["zip"]},
        },
        limit=1,
    )
    if existing:
        debtor = existing[0]
        dx.update_row(
            "debtors",
            debtor["id"],
            {"debt_owed": float(debt), "enrichment_status": "pending"},
        )
        return int(debtor["id"])
    created = dx.create_row(
        "debtors",
        {
            "first_name": first,
            "last_name": last,
            "address_line1": address["line1"],
            "city": address["city"],
            "state": address["state"],
            "zip": address["zip"],
            "debt_owed": float(debt),
            "enrichment_status": "pending",
        },
    )
    return int(created["id"])


def main() -> None:
    load_dotenv()
    dx = DirectusClient.from_env()

    addr = {
        "line1": "1212 N Loop 336 West",
        "city": "Conroe",
        "state": "TX",
        "zip": "77301",
    }
    d1 = upsert_debtor(dx, "Dana", "Garrett", addr, 20000)
    d2 = upsert_debtor(dx, "Linda", "Garrett", addr, 20000)
    # Also seed a known-good subject (from sample) to prove persistence
    addr2 = {
        "line1": "3828 Double Oak Ln",
        "city": "Irving",
        "state": "TX",
        "zip": "75061",
    }
    d3 = upsert_debtor(dx, "Hortencia", "Puente", addr2, 15000)

    print({"seeded": [d1, d2, d3]})


if __name__ == "__main__":
    main()
