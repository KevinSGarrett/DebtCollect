from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.directus_client import DirectusClient
from src.stages.skiptrace_apify import run as apify_run


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


def test_apify_results(dx: DirectusClient, debtor_id: int, first: str, last: str):
    """Test Apify results for a specific debtor"""
    print(f"\n=== Testing {first} {last} ===")

    # Get the debtor record
    debtors = dx.list_related("debtors", {"id": {"_eq": debtor_id}}, limit=1)
    if not debtors:
        print(f"Debtor {debtor_id} not found")
        return
    debtor = debtors[0]

    print(f"Debtor ID: {debtor_id}")
    print(
        f"Address: {debtor.get('address_line1')}, {debtor.get('city')}, {debtor.get('state')} {debtor.get('zip')}"
    )

    # Run Apify stage
    try:
        result = apify_run(debtor, dx)
        print(f"Apify result: {result}")

        # Check what phones and emails were created
        phones = dx.list_related("phones", {"debtor_id": {"_eq": debtor_id}}, limit=10)
        emails = dx.list_related("emails", {"debtor_id": {"_eq": debtor_id}}, limit=10)

        print(f"\nPhones found ({len(phones)}):")
        for phone in phones:
            print(
                f"  - {phone.get('phone_e164')} (strength: {phone.get('match_strength')}, provenance: {phone.get('provenance')})"
            )

        print(f"\nEmails found ({len(emails)}):")
        for email in emails:
            print(
                f"  - {email.get('email')} (strength: {email.get('match_strength')}, provenance: {email.get('provenance')})"
            )

    except Exception as e:
        print(f"Error running Apify: {e}")
        import traceback

        traceback.print_exc()


def main() -> None:
    # Load .env from parent directory since that's where it's located
    load_dotenv("../.env")
    dx = DirectusClient.from_env()

    addr = {
        "line1": "1212 N Loop 336 W",
        "city": "Conroe",
        "state": "TX",
        "zip": "77301",
    }

    # Seed the three Garrett family members
    kevin_id = upsert_debtor(dx, "Kevin", "Garrett", addr, 25000)
    dana_id = upsert_debtor(dx, "Dana", "Garrett", addr, 20000)
    linda_id = upsert_debtor(dx, "Linda", "Garrett", addr, 18000)

    print(
        f"Seeded Garrett family: Kevin({kevin_id}), Dana({dana_id}), Linda({linda_id})"
    )

    # Test each one
    test_apify_results(dx, kevin_id, "Kevin", "Garrett")
    test_apify_results(dx, dana_id, "Dana", "Garrett")
    test_apify_results(dx, linda_id, "Linda", "Garrett")


if __name__ == "__main__":
    main()
