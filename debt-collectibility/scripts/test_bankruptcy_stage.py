from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.directus_client import DirectusClient
from src.stages.bankruptcy import run as bankruptcy_run


def main():
    load_dotenv()
    dx = DirectusClient.from_env()
    print("[OK] Directus client initialized")

    debtors = [
        {
            "first_name": "Kevin",
            "last_name": "Garrett",
            "address_line1": "1212 N Loop 336 W",
            "city": "Conroe",
            "state": "TX",
            "zip": "77301",
        },
        {
            "first_name": "Dana",
            "last_name": "Garrett",
            "address_line1": "1212 N Loop 336 W",
            "city": "Conroe",
            "state": "TX",
            "zip": "77301",
        },
        {
            "first_name": "Linda",
            "last_name": "Garrett",
            "address_line1": "1212 N Loop 336 W",
            "city": "Conroe",
            "state": "TX",
            "zip": "77301",
        },
    ]

    for d in debtors:
        debtor = dx.create_row("debtors", d)
        debtor_id = debtor.get("id")
        print(
            f"[OK] Created debtor {debtor_id}: {debtor.get('first_name')} {debtor.get('last_name')}"
        )

        try:
            bankruptcy_run(debtor, dx)
            cases = dx.list_related("bankruptcy_cases", {"debtor_id": {"_eq": debtor_id}}, limit=50)
            print(f"[INFO] Bankruptcy cases for debtor {debtor_id}: {len(cases)}")
            for c in cases:
                print(
                    f"  - {c.get('case_number')} | chapter={c.get('chapter')} | filed={c.get('filed_date')} | status={c.get('status')} | court={c.get('court')}"
                )
        finally:
            # cleanup
            for c in dx.list_related(
                "bankruptcy_cases", {"debtor_id": {"_eq": debtor_id}}, limit=200
            ):
                try:
                    dx.delete_row("bankruptcy_cases", c.get("id"))
                except Exception as e:
                    print(f"[WARN] Could not delete case {c.get('id')}: {e}")
            dx.delete_row("debtors", debtor_id)
            print(f"[CLEANUP] Deleted debtor {debtor_id}")


if __name__ == "__main__":
    main()
