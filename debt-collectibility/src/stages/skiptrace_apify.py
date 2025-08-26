from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from src.utils.logger import get_logger
from src.utils.matching import match_name_address
from src.utils.normalize import to_e164


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _apify_skiptrace(
    first_name: str, last_name: str, address: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    token = _required_env("APIFY_TOKEN")
    base = "https://api.apify.com/v2/acts/one-api~skip-trace"
    # Use the correct input format that works with the API
    name_query = f"({first_name} {last_name}; {address.get('city') or ''}, {address.get('state') or ''} {address.get('zip') or ''})"
    payload = {"max_results": 3, "name": [name_query]}
    try:
        resp = requests.post(
            f"{base}/run-sync?token={token}", json=payload, timeout=120
        )
        resp.raise_for_status()
        try:
            data = resp.json()
        except ValueError:
            data = {}
        # debug dump
        try:
            log_dir = Path.cwd() / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            with (log_dir / "apify_raw.jsonl").open("a", encoding="utf-8") as fh:
                json.dump(
                    {
                        "ts": datetime.now(UTC).isoformat(),
                        "source": "run-sync",
                        "status": resp.status_code,
                        "payload": payload,
                        "body": data,
                    },
                    fh,
                )
                fh.write("\n")
        except Exception:
            pass
        # Normalize to list of candidates
        if isinstance(data, list):
            return data, {"source": "run-sync:list", "raw": None}
        elif isinstance(data, dict):
            if "results" in data and isinstance(data["results"], list):
                return data["results"], {"source": "run-sync:results", "raw": data}
            # Fallback to dataset items endpoint if OUTPUT is not structured
        # Try dataset items variant
        ds = requests.post(
            f"{base}/run-sync-get-dataset-items?token={token}",
            json=payload,
            timeout=120,
        )
        ds.raise_for_status()
        try:
            items = ds.json()
        except ValueError:
            items = []
        # debug dump
        try:
            log_dir = Path.cwd() / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            with (log_dir / "apify_raw.jsonl").open("a", encoding="utf-8") as fh:
                json.dump(
                    {
                        "ts": datetime.now(UTC).isoformat(),
                        "source": "run-sync-get-dataset-items",
                        "status": ds.status_code,
                        "payload": payload,
                        "body": items,
                    },
                    fh,
                )
                fh.write("\n")
        except Exception:
            pass
        if isinstance(items, list):
            return items, {"source": "run-sync-get-dataset-items", "raw": None}
        return [], {"source": "unknown", "raw": None}
    except requests.RequestException as e:
        raise RuntimeError(f"Apify error: {e}")


def _rapidapi_skiptrace(
    first_name: str, last_name: str, address: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fallback to RapidAPI when Apify fails"""
    try:
        # Use the RapidAPI key from environment
        api_key = os.getenv("RAPIDAPI_KEY")
        if not api_key:
            return [], {"source": "rapidapi:no-key", "raw": None}

        # Make request to RapidAPI
        headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": "usa-people-search-public-records.p.rapidapi.com",
        }

        # Search by name and location
        search_url = (
            "https://usa-people-search-public-records.p.rapidapi.com/SearchPeople"
        )
        search_params = {
            "FirstName": first_name,
            "LastName": last_name,
            "State": address.get("state") or "",
            "Page": "1",
        }

        resp = requests.get(
            search_url, headers=headers, params=search_params, timeout=30
        )
        resp.raise_for_status()

        data = resp.json()

        # Transform RapidAPI response to match Apify format
        candidates = []

        # Handle different response structures
        people_data = []
        if isinstance(data, list):
            people_data = data
        elif isinstance(data, dict):
            # Check for Source1 array (common RapidAPI format)
            if "Source1" in data and isinstance(data["Source1"], list):
                people_data = data["Source1"]
            # Check for other possible array fields
            elif "results" in data and isinstance(data["results"], list):
                people_data = data["results"]
            elif "data" in data and isinstance(data["data"], list):
                people_data = data["data"]

        for person in people_data:
            # Extract phone numbers and emails
            phones = []
            emails = []

            # Handle PeoplePhone array
            if "PeoplePhone" in person and isinstance(person["PeoplePhone"], list):
                for phone_item in person["PeoplePhone"]:
                    if isinstance(phone_item, dict) and phone_item.get("Phone"):
                        phones.append(
                            {
                                "number": phone_item["Phone"],
                                "type": phone_item.get("Type", "Unknown"),
                                "lastSeen": phone_item.get("LastSeen", ""),
                                "firstSeen": phone_item.get("FirstSeen", ""),
                                "provider": phone_item.get("Provider", ""),
                            }
                        )

            # Handle Email array
            if "Email" in person and isinstance(person["Email"], list):
                for email_item in person["Email"]:
                    if isinstance(email_item, dict) and email_item.get("Email"):
                        emails.append(email_item["Email"])
                    elif isinstance(email_item, str):
                        emails.append(email_item)

            # Look for other phone/email fields
            for key, value in person.items():
                if "phone" in key.lower() and value and isinstance(value, str):
                    phones.append(
                        {
                            "number": value,
                            "type": "Unknown",
                            "lastSeen": "",
                            "firstSeen": "",
                            "provider": "",
                        }
                    )
                elif "email" in key.lower() and value and isinstance(value, str):
                    emails.append(value)

            # Parse full name if available
            full_name = person.get("FullName", "")
            first_name_parsed = first_name
            last_name_parsed = last_name

            if full_name:
                # Try to extract first and last name from FullName
                name_parts = full_name.strip().split()
                if len(name_parts) >= 2:
                    # Check if the name matches what we're looking for
                    if (
                        name_parts[0].lower() == first_name.lower()
                        and name_parts[1].lower() == last_name.lower()
                    ):
                        first_name_parsed = name_parts[0]
                        last_name_parsed = name_parts[1]
                    else:
                        # Name doesn't match, skip this candidate
                        continue

            # Create candidate in Apify format
            candidate = {
                "First Name": first_name_parsed,
                "Last Name": last_name_parsed,
                "Street Address": person.get("Address", ""),
                "Address Locality": person.get(
                    "City", ""
                ),  # Use actual city from API response
                "Address Region": person.get(
                    "State", ""
                ),  # Use actual state from API response
                "Postal Code": person.get(
                    "Zip", ""
                ),  # Use actual zip from API response
            }

            # Add phones and emails
            for i, phone in enumerate(phones[:5], 1):
                candidate[f"Phone-{i}"] = phone["number"]
                candidate[f"Phone-{i} Type"] = phone["type"]
                candidate[f"Phone-{i} Last Reported"] = phone["lastSeen"]
                candidate[f"Phone-{i} First Reported"] = phone["firstSeen"]
                candidate[f"Phone-{i} Provider"] = phone["provider"]

            for i, email in enumerate(emails[:5], 1):
                candidate[f"Email-{i}"] = email

            candidates.append(candidate)

        return candidates, {"source": "rapidapi:fallback", "raw": data}

    except Exception as e:
        return [], {"source": "rapidapi:error", "raw": str(e)}


def _first_list(candidate: dict[str, Any], keys: list[list[str]]) -> list[Any]:
    for path in keys:
        node: Any = candidate
        ok = True
        for k in path:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                ok = False
                break
        if ok and isinstance(node, list):
            return node
    return []


def _phone_str(item: Any) -> str | None:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for k in ("e164", "number", "phone", "phoneNumber", "value"):
            v = item.get(k)
            if isinstance(v, str) and v.strip():
                return v
    return None


def _seen_dates(item: Any) -> tuple[str | None, str | None]:
    if not isinstance(item, dict):
        return None, None
    first = None
    last = None
    for k in ("firstSeen", "first_seen", "first_seen_at", "firstObserved"):
        if item.get(k):
            first = str(item.get(k))
            break
    for k in ("lastSeen", "last_seen", "last_seen_at", "lastObserved", "observedAt"):
        if item.get(k):
            last = str(item.get(k))
            break
    return first, last


def _parse_date_string(date_str: str) -> str | None:
    """Parse date strings like 'Last reported Jul 2025' into ISO format"""
    if not date_str or not isinstance(date_str, str):
        return None

    # Handle "Last reported Jul 2025" format
    if "Last reported" in date_str:
        try:
            # Extract month and year
            parts = date_str.replace("Last reported ", "").strip()
            if parts:
                # For now, just return the year as a date
                # This is a simplified approach - in production you might want more sophisticated parsing
                if len(parts) >= 4:  # At least "YYYY" format
                    return f"{parts[-4:]}-01-01"  # Use January 1st of the year
        except Exception:
            pass

    # If it's already a valid date format, return as is
    if len(date_str) == 10 and date_str.count("-") == 2:  # YYYY-MM-DD format
        return date_str

    return None


def _is_tabular_candidate(c: dict[str, Any]) -> bool:
    return any(k.startswith("Phone-1") or k.startswith("Email-1") for k in c.keys())


def _tabular_match_inputs(c: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": f"{c.get('First Name', '').strip()} {c.get('Last Name', '').strip()}",
        "street": (c.get("Street Address") or "").strip(),
        "state": (c.get("Address Region") or "").strip(),
        "zip": (c.get("Postal Code") or "").strip(),
    }


def _iter_tabular_phones(c: dict[str, Any]) -> list[dict[str, Any]]:
    phones: list[dict[str, Any]] = []
    for i in range(1, 10):
        num = (c.get(f"Phone-{i}") or "").strip()
        if not num:
            continue
        item = {
            "number": num,
            "type": (c.get(f"Phone-{i} Type") or "").strip(),
            "lastSeen": (c.get(f"Phone-{i} Last Reported") or "").strip(),
            "firstSeen": (c.get(f"Phone-{i} First Reported") or "").strip(),
            "provider": (c.get(f"Phone-{i} Provider") or "").strip(),
        }
        phones.append(item)
    return phones


def _iter_tabular_emails(c: dict[str, Any]) -> list[str]:
    emails: list[str] = []
    for i in range(1, 10):
        em = (c.get(f"Email-{i}") or "").strip()
        if em:
            emails.append(em)
    return emails


def _load_manual_candidates(first: str, last: str) -> list[dict[str, Any]]:
    """Load manual Apify-like candidates from MANUAL_APIFY_DIR/<First_Last>.json.
    Supports either a list or an object with key 'value' containing a list.
    """
    dir_path = os.getenv("MANUAL_APIFY_DIR")
    if not dir_path:
        return []
    file_path = Path(dir_path) / f"{first}_{last}.json"
    if not file_path.exists():
        # Also try with space instead of underscore
        alt_path = Path(dir_path) / f"{first} {last}.json"
        if alt_path.exists():
            file_path = alt_path
        else:
            return []
    try:
        with file_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and isinstance(data.get("value"), list):
            return data["value"]
        if isinstance(data, list):
            return data
        # If it's a single object, wrap
        if isinstance(data, dict):
            return [data]
    except Exception:
        return []
    return []


def run(debtor: dict[str, Any], dx: Any) -> dict[str, Any] | None:
    log = get_logger()
    first = debtor.get("first_name") or ""
    last = debtor.get("last_name") or ""
    address = {
        "address_line1": debtor.get("address_line1") or debtor.get("street") or "",
        "city": debtor.get("city") or "",
        "state": debtor.get("state") or "",
        "zip": debtor.get("zip") or debtor.get("postal_code") or "",
    }
    if not first or not last:
        return None
    try:
        if os.getenv("SIMULATE") == "1":
            # Simulated phones/emails for testing pipeline
            sample_phones = ["(214) 609-3137", "+1 214-609-3136"]
            sample_emails = ["jtpuente6972@outlook.com", "jrpuente69@yahoo.com"]
            for raw in sample_phones:
                e164 = to_e164(raw)
                if not e164:
                    continue
                exists = dx.list_related(
                    "phones",
                    {
                        "debtor_id": {"_eq": debtor.get("id")},
                        "phone_e164": {"_eq": e164},
                    },
                    limit=1,
                )
                if not exists:
                    dx.create_row(
                        "phones",
                        {
                            "debtor_id": debtor.get("id"),
                            "phone_e164": e164,
                            "match_strength": 50,
                            "provenance": "simulate:apify",
                            "raw_payload": json.dumps({"simulated": True, "raw": raw}),
                        },
                    )
            for em in sample_emails:
                exists = dx.list_related(
                    "emails",
                    {"debtor_id": {"_eq": debtor.get("id")}, "email": {"_eq": em}},
                    limit=1,
                )
                if not exists:
                    dx.create_row(
                        "emails",
                        {
                            "debtor_id": debtor.get("id"),
                            "email": em,
                            "match_strength": 50,
                            "provenance": "simulate:apify",
                            "raw_payload": json.dumps({"simulated": True}),
                        },
                    )
            return None
        # Manual override: if a file exists for this name, use it instead of live call
        manual_candidates = _load_manual_candidates(first, last)
        if manual_candidates:
            candidates = manual_candidates
            meta = {"source": "manual"}
        else:
            try:
                # Try Apify first
                candidates, meta = _apify_skiptrace(first, last, address)
                if not candidates:
                    # Fallback to RapidAPI if Apify returns no results
                    log.info(
                        f"Apify returned no results for {first} {last}, trying RapidAPI fallback"
                    )
                    candidates, meta = _rapidapi_skiptrace(first, last, address)
            except Exception as e:
                # If Apify fails completely, try RapidAPI
                log.warning(
                    f"Apify failed for {first} {last}: {e}, trying RapidAPI fallback"
                )
                candidates, meta = _rapidapi_skiptrace(first, last, address)
        accepted: list[dict[str, Any]] = []
        for c in candidates:
            if _is_tabular_candidate(c):
                cand_addr = _tabular_match_inputs(c)
            else:
                cand_addr = {
                    "name": c.get("fullName")
                    or c.get("name")
                    or c.get("firstName", "") + " " + c.get("lastName", ""),
                    "street": c.get("street")
                    or c.get("address1")
                    or c.get("addressLine1"),
                    "state": c.get("state"),
                    "zip": c.get("zip"),
                }

            # Strict name+address matching - require both name AND address to match
            name_score = match_name_address(
                {
                    "first_name": first,
                    "last_name": last,
                    "address_line1": address["address_line1"],
                    "state": address["state"],
                    "zip": address["zip"],
                },
                cand_addr,
            )

            # Only accept candidates with high confidence (90+) for strict matching
            if name_score >= 90:
                accepted.append({**c, "match_strength": name_score})
            elif name_score >= 80:
                # Medium confidence - check if address components match
                cand_state = (cand_addr.get("state") or "").upper().strip()
                cand_zip = (cand_addr.get("zip") or "").strip()
                target_state = (address.get("state") or "").upper().strip()
                target_zip = (address.get("zip") or "").strip()

                # Require state to match exactly and zip to be similar
                if cand_state == target_state and (
                    cand_zip == target_zip
                    or (
                        len(cand_zip) >= 5
                        and len(target_zip) >= 5
                        and cand_zip[:5] == target_zip[:5]
                    )
                ):
                    accepted.append({**c, "match_strength": name_score})

        # If no strict matches, try name-only with address verification
        if not accepted and candidates:
            log.info(
                f"No strict name+address matches for {first} {last}, trying name-only with address verification"
            )
            name_only_candidates = []
            for c in candidates:
                if _is_tabular_candidate(c):
                    cand_addr = _tabular_match_inputs(c)
                else:
                    cand_addr = {
                        "name": c.get("fullName")
                        or c.get("name")
                        or c.get("firstName", "") + " " + c.get("lastName", ""),
                        "street": c.get("street")
                        or c.get("address1")
                        or c.get("addressLine1"),
                        "state": c.get("state"),
                        "zip": c.get("zip"),
                    }

                # Check name similarity
                n = cand_addr.get("name", "").strip()
                ref = f"{first} {last}".strip()
                from src.utils.matching import name_similarity

                name_sim = name_similarity(ref, n)

                if name_sim >= 85:  # High name similarity
                    # Verify address components
                    cand_state = (cand_addr.get("state") or "").upper().strip()
                    cand_zip = (cand_addr.get("zip") or "").strip()
                    target_state = (address.get("state") or "").upper().strip()
                    target_zip = (address.get("zip") or "").strip()

                    if cand_state == target_state and (
                        cand_zip == target_zip
                        or (
                            len(cand_zip) >= 5
                            and len(target_zip) >= 5
                            and cand_zip[:5] == target_zip[:5]
                        )
                    ):
                        name_only_candidates.append({**c, "match_strength": 75})

            # Take top 2 name-only candidates with verified addresses
            accepted = sorted(
                name_only_candidates,
                key=lambda x: x.get("match_strength", 0),
                reverse=True,
            )[:2]

        for cand in accepted:
            # phones (support multiple possible shapes)
            if _is_tabular_candidate(cand):
                phone_iter = _iter_tabular_phones(cand)
            else:
                phone_iter = _first_list(
                    cand,
                    [
                        ["phones"],
                        ["phoneNumbers"],
                        ["contact_phones"],
                        ["contacts", "phones"],
                        ["contacts", "phoneNumbers"],
                    ],
                )
            for ph in phone_iter or []:
                e164_raw = _phone_str(ph)
                e164 = to_e164(e164_raw) if e164_raw else None
                if not e164:
                    continue
                exists = dx.list_related(
                    "phones",
                    {
                        "debtor_id": {"_eq": debtor.get("id")},
                        "phone_e164": {"_eq": e164},
                    },
                    limit=1,
                )
                if exists:
                    continue
                first_seen, last_seen = _seen_dates(ph)
                # Parse date strings to proper format
                parsed_first_seen = (
                    _parse_date_string(first_seen) if first_seen else None
                )
                parsed_last_seen = _parse_date_string(last_seen) if last_seen else None

                dx.create_row(
                    "phones",
                    {
                        "debtor_id": debtor.get("id"),
                        "phone_e164": e164,
                        "first_seen": parsed_first_seen,
                        "last_seen": parsed_last_seen,
                        "match_strength": cand.get("match_strength"),
                        "provenance": meta.get("source", "unknown"),
                        "raw_payload": json.dumps(ph),
                    },
                )
            # emails (support strings or objects)
            if _is_tabular_candidate(cand):
                email_iter = _iter_tabular_emails(cand)
            else:
                email_iter = _first_list(
                    cand, [["emails"], ["emailAddresses"], ["contacts", "emails"]]
                )
            for em in email_iter or []:
                email_norm = None
                if isinstance(em, str):
                    email_norm = em.lower().strip()
                elif isinstance(em, dict):
                    for k in ("email", "address", "value"):
                        v = em.get(k)
                        if isinstance(v, str) and v.strip():
                            email_norm = v.lower().strip()
                            break
                if not email_norm:
                    continue
                exists = dx.list_related(
                    "emails",
                    {
                        "debtor_id": {"_eq": debtor.get("id")},
                        "email": {"_eq": email_norm},
                    },
                    limit=1,
                )
                if exists:
                    continue
                dx.create_row(
                    "emails",
                    {
                        "debtor_id": debtor.get("id"),
                        "email": email_norm,
                        "match_strength": cand.get("match_strength"),
                        "provenance": meta.get("source", "unknown"),
                        "raw_payload": json.dumps(em),
                    },
                )

        # Update debtor with verified information from top candidate
        patch: dict[str, Any] = {}
        top = accepted[0] if accepted else None
        if top:
            # Handle age - prefer numeric age, fallback to parsing from text
            age = top.get("age")
            if age:
                if isinstance(age, str):
                    # Try to extract numeric age from strings like "39 years old"
                    import re

                    age_match = re.search(r"(\d+)", str(age))
                    if age_match:
                        patch["age"] = int(age_match.group(1))
                    else:
                        patch["age"] = age
                elif isinstance(age, (int, float)):
                    patch["age"] = int(age)

            # Handle DOB - prefer date format, fallback to parsing
            dob = top.get("dob") or top.get("dateOfBirth") or top.get("birthDate")
            if dob:
                if isinstance(dob, str):
                    # Try to parse various date formats
                    parsed_dob = _parse_date_string(dob)
                    if parsed_dob:
                        patch["dob"] = parsed_dob
                    else:
                        patch["dob"] = dob
                else:
                    patch["dob"] = dob

            # Persist age/dob to Directus immediately
            if patch:
                try:
                    dx.update_row("debtors", debtor.get("id"), patch)
                    log.info(f"Updated debtor {debtor.get('id')} with: {patch}")
                except Exception as e:
                    log.warning(
                        f"Failed to update debtor {debtor.get('id')} with age/dob: {e}"
                    )

        return patch or None
    except Exception as e:
        log.warning(f"Apify skip-trace failed debtor {debtor.get('id')}: {e}")
        return None
