from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main():
    load_dotenv()
    base = os.getenv(
        "COURTLISTENER_API", "https://www.courtlistener.com/api/rest/v4/dockets/"
    )
    token = os.getenv("COURTLISTENER_API_TOKEN")
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Token {token}"

    try:
        r = requests.get(
            "https://www.courtlistener.com/api/rest/v4/", headers=headers, timeout=20
        )
        print(f"root status={r.status_code}")
    except Exception as e:
        print(f"root error: {e}")

    try:
        r = requests.get(base, headers=headers, params={"page_size": 1}, timeout=20)
        print(f"dockets status={r.status_code}")
        if r.ok:
            js = r.json()
            results = js.get("results", [])
            print(f"dockets results={len(results)}")
            if results:
                first = results[0]
                print(
                    f"first id={first.get('id')} docket_number={first.get('docket_number')} filed={first.get('date_filed')}"
                )
    except Exception as e:
        print(f"dockets error: {e}")


if __name__ == "__main__":
    main()
