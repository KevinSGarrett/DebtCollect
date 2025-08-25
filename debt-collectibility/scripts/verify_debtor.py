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
    debtors = dx.list_related(
        "debtors", {"first_name": {"_eq": "Kevin"}, "last_name": {"_eq": "Garrett"}}, limit=5
    )
    if not debtors:
        print(json.dumps({"error": "debtor not found"}))
        return
    d = debtors[0]
    debtor_id = d.get("id")

    def safe_list(coll, filt, limit=50):
        try:
            return dx.list_related(coll, filt, limit=limit)
        except Exception:
            return []

    addresses = safe_list("addresses", {"debtor_id": {"_eq": debtor_id}})
    phones = safe_list("phones", {"debtor_id": {"_eq": debtor_id}})
    emails = safe_list("emails", {"debtor_id": {"_eq": debtor_id}})
    properties = safe_list("properties", {"debtor_id": {"_eq": debtor_id}})
    businesses = safe_list("debtor_businesses", {"debtor_id": {"_eq": debtor_id}})
    bankruptcies = safe_list("bankruptcy_cases", {"debtor_id": {"_eq": debtor_id}})
    snapshots = safe_list("scoring_snapshots", {"debtor_id": {"_eq": debtor_id}}, limit=5)
    runs = safe_list("enrichment_runs", {"debtor_id": {"_eq": debtor_id}}, limit=5)

    out = {
        "debtor": {
            "id": debtor_id,
            "first_name": d.get("first_name"),
            "last_name": d.get("last_name"),
            "enrichment_status": d.get("enrichment_status"),
            "usps_standardized": d.get("usps_standardized"),
            "best_phone_id": d.get("best_phone_id"),
            "best_email_id": d.get("best_email_id"),
            "collectibility_score": d.get("collectibility_score"),
            "collectibility_reason": d.get("collectibility_reason"),
        },
        "counts": {
            "addresses": len(addresses),
            "phones": len(phones),
            "emails": len(emails),
            "properties": len(properties),
            "business_links": len(businesses),
            "bankruptcy_cases": len(bankruptcies),
            "scoring_snapshots": len(snapshots),
            "enrichment_runs": len(runs),
        },
        "last_snapshot": snapshots[-1] if snapshots else None,
        "last_run": runs[-1] if runs else None,
    }
    print(json.dumps(out, default=str))


if __name__ == "__main__":
    main()
