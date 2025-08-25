from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.stages.bankruptcy import _courtlistener_search

KNOWN_CASES = [
    "Midland Funding, LLC v. Johnson",
    "In Re Daniels",
    "Helman v. Udren Law Offices, P.C.",
    "Spears v. Brennan",
    "Millsap v. AmSher Collection Services, Inc.",
    "Brantley v. Weeks",
]


def main():
    load_dotenv()
    token = os.getenv("COURTLISTENER_API_TOKEN")
    base = os.getenv("COURTLISTENER_API")
    print(f"[INFO] Using CourtListener base={base} token={'yes' if token else 'no'}")

    for case in KNOWN_CASES:
        try:
            results = _courtlistener_search(case, "", "", "")
            print(f"[OK] Query '{case}' -> {len(results)} results")
            for r in results[:3]:
                print(
                    f"  - {r.get('case_number')} | {r.get('docket_url')} | filed={r.get('filed_date')} | court={r.get('court')} | status={r.get('status')}"
                )
        except Exception as e:
            print(f"[ERROR] Query '{case}' failed: {e}")


if __name__ == "__main__":
    main()
