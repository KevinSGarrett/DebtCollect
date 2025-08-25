from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

# Ensure src is importable when running as a script
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.directus_client import DirectusClient


def main() -> None:
    load_dotenv()
    dx = DirectusClient.from_env()
    debtor = {
        "first_name": "Kevin",
        "last_name": "Garrett",
        "address_line1": "1212 N Loop 336 West",
        "city": "Conroe",
        "state": "TX",
        "zip": "77301",
        "debt_owed": 75000,
        "enrichment_status": "pending",
    }
    created = dx.create_row("debtors", debtor)
    print({"created_debtor": created})


if __name__ == "__main__":
    main()
