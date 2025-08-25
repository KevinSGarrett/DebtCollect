from __future__ import annotations

import json
import os
import sys

from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.directus_client import DirectusClient


def main() -> None:
    load_dotenv()
    dx = DirectusClient.from_env()
    checks = {}

    # Round-trip write/read for a temp email row
    debtor = dx.get_debtors_to_enrich(1)
    debtor_id = (debtor[0].get("id") if debtor else None) or None
    if debtor_id is None:
        # Fallback: find any debtor
        any_debtor = dx.list_related("debtors", {}, limit=1)
        if not any_debtor:
            print(
                json.dumps(
                    {"directus_checks": {"emails_round_trip": False, "reason": "no debtor found"}}
                )
            )
            return
        debtor_id = any_debtor[0].get("id")
    # ensure unique email per debtor to avoid unique constraint
    from uuid import uuid4

    test_email = f"diagnostic+{uuid4().hex[:8]}@example.com"
    email = {
        "debtor_id": debtor_id,
        "email": test_email,
        "provenance": "diagnostic",
        "raw_payload": "{}",
    }
    created = dx.create_row("emails", email)
    readback = dx.list_related("emails", {"id": {"_eq": created.get("id")}}, limit=1)
    checks["emails_round_trip"] = bool(readback)

    # Cleanup (best-effort)
    # Directus delete not implemented in client; leave for manual cleanup if needed

    print(json.dumps({"directus_checks": checks}, default=str))


if __name__ == "__main__":
    main()
