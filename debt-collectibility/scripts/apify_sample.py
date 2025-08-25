from __future__ import annotations

import json
import os

import requests
from dotenv import load_dotenv


def run_sample(
    first_name: str, last_name: str, address_line1: str, city: str, state: str, zip5: str
) -> dict:
    load_dotenv()
    token = os.getenv("APIFY_TOKEN")
    base = "https://api.apify.com/v2/acts/one-api~skip-trace"
    payload = {
        "firstName": first_name,
        "lastName": last_name,
        "address": {
            "addressLine1": address_line1,
            "city": city,
            "state": state,
            "zip": zip5,
        },
        "addressLine1": address_line1,
        "city": city,
        "state": state,
        "zip": zip5,
    }
    r = requests.post(f"{base}/run-sync?token={token}", json=payload, timeout=120)
    r.raise_for_status()
    try:
        return r.json()
    except ValueError:
        # fallback to dataset items
        ds = requests.post(
            f"{base}/run-sync-get-dataset-items?token={token}", json=payload, timeout=120
        )
        ds.raise_for_status()
        try:
            return {"items": ds.json()}
        except ValueError:
            return {"items": []}


if __name__ == "__main__":
    data = run_sample("Dana", "Garrett", "1212 N Loop 336 West", "Conroe", "TX", "77301")
    print(json.dumps(data, default=str))
