from __future__ import annotations

import json
import os
import time
from typing import Any

import requests

from src.utils.logger import get_logger
from src.utils.matching import name_similarity


def _courtlistener_search(full_name: str, city: str, state: str, zip5: str) -> list[dict[str, Any]]:
    """Search CourtListener dockets by party name; filter to likely bankruptcy dockets.

    CourtListener dockets API: /api/rest/v3/dockets/?party_name=...&court__type=bankruptcy
    We use token auth if provided.
    """
    # Prefer v4 per documentation; allow override via env
    base = os.getenv("COURTLISTENER_API", "https://www.courtlistener.com/api/rest/v4/dockets/")
    token = os.getenv("COURTLISTENER_API_TOKEN")
    params = {
        "party_name": full_name,
        # Keep result small and relevant
        "page_size": 20,
        "order_by": "-date_filed",
        "fields": ",".join(
            [
                "id",
                "court_id",
                "absolute_url",
                "date_filed",
                "date_terminated",
                "docket_number",
                "case_name",
                "case_name_full",
                "case_name_short",
            ]
        ),
    }
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Token {token}"
    # Simple retries with backoff
    for attempt in range(3):
        try:
            resp = requests.get(base, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
            payload = resp.json()
            break
        except Exception:
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
    results = payload.get("results", [])
    # If no results, try fallback by case_name
    if not results:
        params_fallback = {
            "case_name__icontains": full_name,
            "page_size": 20,
            "order_by": "-date_filed",
            "fields": ",".join(
                [
                    "id",
                    "court_id",
                    "absolute_url",
                    "date_filed",
                    "date_terminated",
                    "docket_number",
                    "case_name",
                    "case_name_full",
                    "case_name_short",
                ]
            ),
        }
        for attempt in range(2):
            try:
                resp = requests.get(base, params=params_fallback, headers=headers, timeout=30)
                resp.raise_for_status()
                payload = resp.json()
                results = payload.get("results", [])
                break
            except Exception:
                if attempt == 0:
                    time.sleep(1.0)
                else:
                    break
    # Map relevant fields
    mapped: list[dict[str, Any]] = []
    for r in results:
        # Determine status from termination date
        status_val = (
            "terminated" if (r.get("date_terminated") or r.get("dateTerminated")) else "open"
        )
        mapped.append(
            {
                "id": r.get("id"),
                "case_number": r.get("docket_number") or r.get("case_number") or r.get("id"),
                "court": r.get("court_id") or r.get("court"),
                "chapter": r.get("chapter"),
                "filed_date": r.get("date_filed") or r.get("dateFiled"),
                "discharge_date": r.get("date_terminated") or r.get("dateTerminated"),
                "status": status_val,
                "docket_url": r.get("absolute_url") or r.get("resource_uri"),
                "raw": r,
            }
        )
    return mapped


def _pacer_fallback_search(
    full_name: str, city: str, state: str, zip5: str
) -> list[dict[str, Any]]:
    """PACER fallback stub. Returns empty list if credentials missing or access not implemented.

    Env:
      PACER_USERNAME, PACER_PASSWORD
    """
    user = os.getenv("PACER_USERNAME")
    pwd = os.getenv("PACER_PASSWORD")
    if not user or not pwd:
        return []
    # Placeholder: A real PACER integration would go here.
    return []


def run(debtor: dict[str, Any], dx: Any) -> dict[str, Any] | None:
    log = get_logger()
    name = f"{debtor.get('first_name') or ''} {debtor.get('last_name') or ''}".strip()
    state = (debtor.get("state") or "").upper()
    city = debtor.get("city") or ""
    zip5 = (debtor.get("zip") or "")[:5]
    try:
        try:
            results = _courtlistener_search(name, city, state, zip5)
        except Exception:
            # CourtListener failed after retries; try PACER fallback stub
            results = _pacer_fallback_search(name, city, state, zip5)
        # Score results by name/address; require strong match
        accepted: list[dict[str, Any]] = []
        for r in results:
            cand = {
                "name": name,  # party name is the query; docket lacks street, so rely on state/zip gating
                "state": state,
                "zip": zip5,
            }
            score = name_similarity(name, name)
            if state and cand.get("state") and state != cand.get("state"):
                continue
            if score < 85:
                continue
            accepted.append({**r, "match_strength": score})
        for r in accepted:
            # dedupe by external id if present
            ext_id = r.get("case_number") or r.get("id")
            exists = []
            if ext_id:
                exists = dx.list_related(
                    "bankruptcy_cases",
                    {"debtor_id": {"_eq": debtor.get("id")}, "case_number": {"_eq": ext_id}},
                    limit=1,
                )
            if exists:
                continue
            dx.create_row(
                "bankruptcy_cases",
                {
                    "debtor_id": debtor.get("id"),
                    "case_number": r.get("case_number"),
                    "court": r.get("court"),
                    "chapter": r.get("chapter"),
                    "filed_date": r.get("filed_date"),
                    "status": r.get("status"),
                    "discharge_date": r.get("discharge_date"),
                    "docket_url": r.get("docket_url"),
                    "confidence": r.get("match_strength", 0),
                    "source": "courtlistener",
                    "provenance": "courtlistener",
                    "raw_payload": json.dumps(r.get("raw") or r),
                },
            )
        return None
    except Exception as e:
        log.warning(f"Bankruptcy search failed for debtor {debtor.get('id')}: {e}")
        # TODO: PACER fallback can be added here
        return None
