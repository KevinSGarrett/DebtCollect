from __future__ import annotations

import json
import os
from typing import Any

import requests

from src.utils.logger import get_logger
from src.utils.normalize import normalize_address


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _usps_validate(addr: dict[str, Any]) -> dict[str, Any]:
    user_id = _required_env("USPS_USER_ID")
    # USPS API uses XML normally; here we use the JSON Web Tools endpoint if available, otherwise stub
    # For production, integrate the official API.
    params = {
        "API": "Verify",
        "XML": f"<AddressValidateRequest USERID='{user_id}'><Address ID='0'><Address1>{addr.get('line2')}</Address1><Address2>{addr.get('line1')}</Address2><City>{addr.get('city')}</City><State>{addr.get('state')}</State><Zip5>{addr.get('zip')}</Zip5><Zip4></Zip4></Address></AddressValidateRequest>",
    }
    resp = requests.get(
        "https://secure.shippingapis.com/ShippingAPI.dll", params=params, timeout=30
    )
    resp.raise_for_status()
    text = resp.text
    # Naive parse/stub confidence. In production, parse XML properly.
    dpv_confirmed = "DPVConfirmation>Y<" in text
    return {
        "dpv_confirmation": "Y" if dpv_confirmed else "N",
        "zip5": addr.get("zip"),
        "zip4": "",
        "raw": text,
    }


def run(debtor: dict[str, Any], dx: Any) -> dict[str, Any] | None:
    log = get_logger()
    if os.getenv("SIMULATE") == "1":
        address = normalize_address(
            debtor.get("address_line1") or "",
            debtor.get("address_line2"),
            debtor.get("city") or "",
            debtor.get("state") or "",
            debtor.get("zip") or "",
        )
        existing = dx.list_related(
            "addresses",
            {
                "debtor_id": {"_eq": debtor.get("id")},
                "line1": {"_eq": address["line1"]},
                "zip5": {"_eq": (debtor.get("zip") or "")[:5]},
            },
            limit=1,
        )
        if existing:
            addr_row = existing[0]
        else:
            addr_row = dx.create_row(
                "addresses",
                {
                    "debtor_id": debtor.get("id"),
                    "line1": address["line1"],
                    "line2": address["line2"],
                    "city": address["city"],
                    "state": address["state"],
                    "zip5": (debtor.get("zip") or "")[:5],
                    "zip4": "1234",
                    "dpv_confirmation": "Y",
                    "confidence": 100,
                    "provenance": "simulate:usps",
                    "raw_payload": json.dumps({"simulated": True}),
                },
            )
        patch: dict[str, Any] = {"usps_standardized": True}
        if addr_row and addr_row.get("id"):
            patch["standardized_address_id"] = addr_row["id"]
        return patch
    address = normalize_address(
        debtor.get("address_line1") or debtor.get("street") or "",
        debtor.get("address_line2"),
        debtor.get("city") or "",
        debtor.get("state") or "",
        debtor.get("zip") or debtor.get("postal_code") or "",
    )
    try:
        result = _usps_validate(address)
        dpv = result.get("dpv_confirmation") == "Y"
        raw_payload = result.get("raw")
        # Idempotent create address row if not exists
        existing = dx.list_related(
            "addresses",
            {
                "debtor_id": {"_eq": debtor.get("id")},
                "line1": {"_eq": address["line1"]},
                "zip5": {"_eq": result.get("zip5")},
            },
            limit=1,
        )
        if existing:
            addr_row = existing[0]
        else:
            addr_row = dx.create_row(
                "addresses",
                {
                    "debtor_id": debtor.get("id"),
                    "line1": address["line1"],
                    "line2": address["line2"],
                    "city": address["city"],
                    "state": address["state"],
                    "zip5": result.get("zip5"),
                    "zip4": result.get("zip4"),
                    "dpv_confirmation": result.get("dpv_confirmation"),
                    "confidence": 100 if dpv else 70,
                    "provenance": "usps:webtools",
                    "raw_payload": json.dumps({"response": raw_payload}),
                },
            )
        patch: dict[str, Any] = {"usps_standardized": bool(dpv)}
        if addr_row and addr_row.get("id"):
            patch["standardized_address_id"] = addr_row["id"]
        return patch
    except Exception as e:
        log.warning(f"USPS validation failed for debtor {debtor.get('id')}: {e}")
        return None
