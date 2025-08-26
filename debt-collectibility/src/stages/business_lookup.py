from __future__ import annotations

import json
import os
from typing import Any

import requests

from src.utils.logger import get_logger  # noqa: F401


def _google_places_search(
    query: str, lat: float | None, lng: float | None
) -> dict[str, Any]:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"results": []}
    params = {"query": query, "key": api_key}
    if lat is not None and lng is not None:
        params["location"] = f"{lat},{lng}"
        params["radius"] = "10000"
    try:
        resp = requests.get(
            "https://maps.googleapis.com/maps/api/place/textsearch/json",
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {"results": []}


def _apollo_search_person(name: str) -> dict[str, Any]:
    api_key = os.getenv("APOLLO_API_KEY")
    if not api_key:
        return {"people": []}
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        resp = requests.get(
            "https://api.apollo.io/v1/people/match",
            params={"name": name},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {"people": []}


def run(debtor: dict[str, Any], dx: Any) -> dict[str, Any] | None:
    full_name = (
        f"{debtor.get('first_name') or ''} {debtor.get('last_name') or ''}".strip()
    )
    query = full_name
    places = _google_places_search(query, None, None)
    confidence = 0
    for biz in places.get("results", [])[:5]:
        name = biz.get("name")
        website = biz.get("website") or biz.get("url")
        phone = biz.get("formatted_phone_number") or None
        # upsert business by name+website
        exists = dx.list_related("businesses", {"name": {"_eq": name}}, limit=1)
        if exists:
            biz_row = exists[0]
        else:
            biz_row = dx.create_row(
                "businesses",
                {
                    "name": name,
                    "website": website,
                    "phone": phone,
                    "provenance": "google_places",
                    "raw_payload": json.dumps(biz),
                },
            )
        # link
        link_exists = dx.list_related(
            "debtor_businesses",
            {
                "debtor_id": {"_eq": debtor.get("id")},
                "business_id": {"_eq": biz_row.get("id")},
            },
            limit=1,
        )
        if not link_exists:
            dx.create_row(
                "debtor_businesses",
                {
                    "debtor_id": debtor.get("id"),
                    "business_id": biz_row.get("id"),
                    "role": "owner",
                },
            )
        confidence = max(confidence, 70 if website and phone else 50)

    if confidence == 0:
        ap = _apollo_search_person(full_name)
        if ap.get("people"):
            confidence = 40

    return {"business_confidence": confidence}
