from __future__ import annotations

import json
import os
from typing import Any

import requests

from src.utils.logger import get_logger  # noqa: F401


def _attom_lookup(address: dict[str, Any]) -> dict[str, Any] | None:
    api_key = os.getenv("ATTOM_API_KEY")
    if not api_key:
        return None
    params = {
        "address": f"{address.get('line1')}, {address.get('city')}, {address.get('state')} {address.get('zip')}",
        "apikey": api_key,
    }
    try:
        resp = requests.get(
            "https://api.attomdata.com/propertyapi/v1.0.0/property/detail",
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _census_zip_median(zip5: str) -> dict[str, Any] | None:
    api_key = os.getenv("CENSUS_API_KEY")
    if not api_key or not zip5:
        return None
    # Placeholder; would query a relevant Census endpoint and compute medians.
    return {"zip": zip5, "median_value": 250000}


def run(debtor: dict[str, Any], dx: Any) -> dict[str, Any] | None:
    if os.getenv("SIMULATE") == "1":
        # Create median property value using Census fallback style
        address = {
            "line1": debtor.get("address_line1") or debtor.get("street"),
            "city": debtor.get("city"),
            "state": debtor.get("state"),
            "zip": (debtor.get("zip") or "")[:5],
        }
        exists = dx.list_related(
            "properties",
            {
                "debtor_id": {"_eq": debtor.get("id")},
                "address_line1": {"_eq": address.get("line1")},
                "zip": {"_eq": address.get("zip")},
            },
            limit=1,
        )
        if not exists:
            dx.create_row(
                "properties",
                {
                    "debtor_id": debtor.get("id"),
                    "address_line1": address.get("line1"),
                    "city": address.get("city"),
                    "state": address.get("state"),
                    "zip": address.get("zip"),
                    "market_value": 250000.00,
                    "value_source": "simulate:census_zip_median",
                    "owner_occupied": True,
                    "raw_payload": json.dumps({"simulated": True}),
                },
            )
        return None
    # Prefer standardized address if present
    std_addr_id = debtor.get("standardized_address_id")
    address = None
    if std_addr_id:
        rows = dx.list_related("addresses", {"id": {"_eq": std_addr_id}}, limit=1)
        address = rows[0] if rows else None
    if not address:
        address = {
            "line1": debtor.get("address_line1") or debtor.get("street"),
            "city": debtor.get("city"),
            "state": debtor.get("state"),
            "zip": (debtor.get("zip") or "")[:5],
        }

    attom = _attom_lookup(address)
    if attom and attom.get("property"):
        prop = attom["property"][0]
        exists = dx.list_related(
            "properties",
            {
                "debtor_id": {"_eq": debtor.get("id")},
                "address_line1": {"_eq": address.get("line1")},
                "zip": {"_eq": address.get("zip")},
            },
            limit=1,
        )
        if not exists:
            dx.create_row(
                "properties",
                {
                    "debtor_id": debtor.get("id"),
                    "address_line1": address.get("line1"),
                    "city": address.get("city"),
                    "state": address.get("state"),
                    "zip": address.get("zip"),
                    "market_value": prop.get("assessment", {}).get("market") or None,
                    "assessed_value": prop.get("assessment", {}).get("assessed")
                    or None,
                    "annual_tax": prop.get("assessment", {}).get("taxamt") or None,
                    "owner_occupied": prop.get("summary", {}).get("ownocc") == "Y",
                    "value_source": "attom",
                    "raw_payload": json.dumps(attom),
                },
            )
        return None

    # Fallback to Census ZIP medians
    census = _census_zip_median(address.get("zip") or "")
    if census:
        exists = dx.list_related(
            "properties",
            {
                "debtor_id": {"_eq": debtor.get("id")},
                "address_line1": {"_eq": address.get("line1")},
                "zip": {"_eq": address.get("zip")},
            },
            limit=1,
        )
        if not exists:
            dx.create_row(
                "properties",
                {
                    "debtor_id": debtor.get("id"),
                    "address_line1": address.get("line1"),
                    "city": address.get("city"),
                    "state": address.get("state"),
                    "zip": address.get("zip"),
                    "market_value": census.get("median_value"),
                    "value_source": "census_zip_median",
                    "raw_payload": json.dumps(census),
                },
            )
    return None
