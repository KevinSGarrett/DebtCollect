from __future__ import annotations

import json
import os
import re
from typing import Any

import requests

from src.utils.logger import get_logger


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _rpv_lookup(phone_e164: str) -> dict[str, Any]:
    """Lookup phone number using RealValidation Turbo v3 API.

    - Converts input to 10-digit US phone per vendor requirement
    - Default endpoint: https://api.realvalidation.com/rpvWebService/TurboV3.php
    - Params: output=json, phone=##########, token=TOKEN
    - Disable via REALPHONEVALIDATION_ENABLED=0
    - Override base via REALPHONEVALIDATION_URL
    """
    if os.getenv("REALPHONEVALIDATION_ENABLED", "1") == "0":
        raise RuntimeError("RPV disabled via env")
    api_key = _required_env("REALPHONEVALIDATION_API_KEY")
    base_url = os.getenv(
        "REALPHONEVALIDATION_URL",
        os.getenv("REALVALIDATION_URL", "https://api.realvalidation.com/rpvWebService/TurboV3.php"),
    )
    # Normalize to 10 digits
    digits = re.sub(r"\D", "", phone_e164 or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) > 10:
        digits = digits[-10:]
    if len(digits) != 10:
        raise RuntimeError(f"RPV requires 10-digit US number, got: {phone_e164}")
    params = {"output": "json", "phone": digits, "token": api_key}
    try:
        resp = requests.get(base_url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.SSLError:
        resp = requests.get(base_url, params=params, timeout=30, verify=False)
        resp.raise_for_status()
        return resp.json()


def _twilio_lookup(phone_e164: str) -> dict[str, Any]:
    """Lookup phone number using Twilio API as fallback."""
    sid = _required_env("TWILIO_ACCOUNT_SID")
    token = _required_env("TWILIO_AUTH_TOKEN")
    enable_cnam = os.getenv("TWILIO_ENABLE_CALLER_NAME", "0") == "1"
    types = ["carrier"] + (["caller-name"] if enable_cnam else [])
    qs = "&".join([f"Type={t}" for t in types])
    url = f"https://lookups.twilio.com/v1/PhoneNumbers/{phone_e164}?{qs}"
    resp = requests.get(url, auth=(sid, token), timeout=30)
    resp.raise_for_status()
    return resp.json()


def _hunter_verify(email: str) -> dict[str, Any]:
    """Verify email using Hunter.io API"""
    api_key = _required_env("HUNTER_API_KEY")
    url = f"https://api.hunter.io/v2/email-verifier?email={email}&api_key={api_key}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def run(debtor: dict[str, Any], dx: Any) -> dict[str, Any] | None:
    """
    Verify and clean up contacts for a debtor.

    This function:
    1. Verifies all phone numbers using Real Phone Validation (primary) and Twilio (fallback)
    2. Verifies all emails using Hunter.io (primary)
    3. Removes invalid contacts
    4. Selects best verified contacts
    5. Updates debtor with best contact references
    """
    log = get_logger()
    debtor_id = debtor.get("id")
    debtor_name = f"{debtor.get('first_name', '')} {debtor.get('last_name', '')}".strip()
    # address not used directly; verification relies on phone/email checks

    log.info(f"Verifying contacts for debtor {debtor_id}: {debtor_name}")

    # Get all phones and emails for this debtor
    phones = dx.list_related("phones", {"debtor_id": {"_eq": debtor_id}}, limit=100)
    emails = dx.list_related("emails", {"debtor_id": {"_eq": debtor_id}}, limit=100)

    log.info(f"Found {len(phones)} phones and {len(emails)} emails to verify")

    # Track verification results
    verified_phones = []
    verified_emails = []
    removed_phones = []
    removed_emails = []

    # Verify phones
    for ph in phones:
        phone_id = ph.get("id")
        e164 = ph.get("phone_e164")

        if not e164:
            log.warning(f"Phone {phone_id} has no E.164 number, removing")
            removed_phones.append(phone_id)
            continue

        # Skip if already verified
        if ph.get("is_verified"):
            verified_phones.append(ph)
            continue

        try:
            # Try Real Phone Validation first
            rpv = _rpv_lookup(e164)
            status = (rpv.get("status") or "").lower()
            # Map status to score
            if status.startswith("connected"):
                verification_score = 100 if status == "connected" else 75
                is_verified = True
            else:
                verification_score = 0
                is_verified = False
            line_type = (rpv.get("phone_type") or "").lower()
            carrier = rpv.get("carrier") or None

            dx.update_row(
                "phones",
                phone_id,
                {
                    "rpv_status": status,
                    "rpv_confidence": verification_score,
                    "line_type": line_type,
                    "carrier_name": carrier,
                    "is_verified": is_verified,
                    "verification_score": verification_score,
                    "raw_payload": json.dumps(rpv),
                },
            )

            if is_verified:
                verified_phones.append(
                    {**ph, "is_verified": True, "verification_score": verification_score}
                )
                log.info(f"Phone {e164} verified via RPV with score {verification_score}")
            else:
                log.info(f"Phone {e164} failed RPV verification: {status}")

        except Exception as e:
            log.warning(f"RPV unavailable/failed for phone {e164}: {e}")
            try:
                # Fallback to Twilio
                t = _twilio_lookup(e164)
                line_type = (t.get("carrier") or {}).get("type")
                carrier = (t.get("carrier") or {}).get("name")
                # Treat mobile/voip as stronger signals than landline
                if line_type in ("mobile", "voip"):
                    verification_score = 70
                elif line_type == "landline":
                    verification_score = 50
                else:
                    verification_score = 0
                is_verified = verification_score > 0

                dx.update_row(
                    "phones",
                    phone_id,
                    {
                        "twilio_status": line_type,
                        "line_type": line_type,
                        "carrier_name": carrier,
                        "is_verified": is_verified,
                        "verification_score": verification_score,
                        "raw_payload": json.dumps(t),
                    },
                )

                if is_verified:
                    verified_phones.append(
                        {**ph, "is_verified": True, "verification_score": verification_score}
                    )
                    log.info(f"Phone {e164} verified via Twilio fallback")
                else:
                    log.info(f"Phone {e164} failed Twilio verification")

            except Exception as twilio_error:
                log.error(f"Both RPV and Twilio failed for phone {e164}: {twilio_error}")
                # Mark as unverified
                dx.update_row(
                    "phones",
                    phone_id,
                    {
                        "is_verified": False,
                        "verification_score": 0,
                        "raw_payload": json.dumps({"error": str(twilio_error)}),
                    },
                )

    # Verify emails
    for em in emails:
        email_id = em.get("id")
        email = em.get("email")

        if not email:
            log.warning(f"Email {email_id} has no email address, removing")
            removed_emails.append(email_id)
            continue

        # Skip if already verified
        if em.get("is_verified"):
            verified_emails.append(em)
            continue

        try:
            # Try Hunter.io first
            hv = _hunter_verify(email)
            data = hv.get("data") or {}
            status = data.get("status")
            score = data.get("score")
            is_verified = status == "valid"
            verification_score = max(0, min(100, int(score or 0)))

            dx.update_row(
                "emails",
                email_id,
                {
                    "hunter_status": status,
                    "hunter_score": score,
                    "is_verified": is_verified,
                    "raw_payload": json.dumps(hv),
                },
            )

            if is_verified:
                verified_emails.append({**em, "is_verified": True, "hunter_score": score})
                log.info(f"Email {email} verified via Hunter.io with score {score}")
            else:
                log.info(f"Email {email} failed Hunter.io verification: {status}")

        except Exception as e:
            log.warning(f"Hunter.io verification failed for email {email}: {e}")
            try:
                # Fallback to Twilio (for email validation)
                # Note: Twilio doesn't do email validation, so we'll mark as unverified
                dx.update_row(
                    "emails",
                    email_id,
                    {
                        "is_verified": False,
                        "hunter_score": 0,
                        "raw_payload": json.dumps({"error": f"Hunter.io failed: {e!s}"}),
                    },
                )
                log.info(f"Email {email} marked as unverified due to verification failure")

            except Exception as update_error:
                log.error(f"Failed to update email {email}: {update_error}")

    # Remove invalid contacts discovered earlier
    for phone_id in removed_phones:
        try:
            dx.delete_row("phones", phone_id)
            log.info(f"Removed invalid phone {phone_id}")
        except Exception as e:
            log.error(f"Failed to remove phone {phone_id}: {e}")

    for email_id in removed_emails:
        try:
            dx.delete_row("emails", email_id)
            log.info(f"Removed invalid email {email_id}")
        except Exception as e:
            log.error(f"Failed to remove email {email_id}: {e}")

    # Enforce policy: only keep verified contacts that also had strong match from skiptrace
    # Strong match is defined as match_strength >= 80
    try:
        current_phones = dx.list_related("phones", {"debtor_id": {"_eq": debtor_id}}, limit=200)
        for ph in current_phones:
            ms = ph.get("match_strength") or 0
            # Ensure match_strength is numeric for comparison
            try:
                ms = int(ms) if ms is not None else 0
            except (ValueError, TypeError):
                ms = 0
            if not ph.get("is_verified") or ms < 80:
                try:
                    dx.delete_row("phones", ph.get("id"))
                    log.info(
                        f"Removed phone {ph.get('phone_e164')} (verified={ph.get('is_verified')}, match_strength={ms})"
                    )
                except Exception as e:
                    log.error(f"Failed to remove phone {ph.get('id')}: {e}")
        current_emails = dx.list_related("emails", {"debtor_id": {"_eq": debtor_id}}, limit=200)
        for em in current_emails:
            ms = em.get("match_strength") or 0
            # Ensure match_strength is numeric for comparison
            try:
                ms = int(ms) if ms is not None else 0
            except (ValueError, TypeError):
                ms = 0
            if not em.get("is_verified") or ms < 80:
                try:
                    dx.delete_row("emails", em.get("id"))
                    log.info(
                        f"Removed email {em.get('email')} (verified={em.get('is_verified')}, match_strength={ms})"
                    )
                except Exception as e:
                    log.error(f"Failed to remove email {em.get('id')}: {e}")
    except Exception as e:
        log.error(f"Failed during cleanup policy enforcement: {e}")

    # Choose best phone/email based on verification scores
    best_phone_id: int | None = None
    best_email_id: int | None = None

    if verified_phones:
        # Sort by verification score, then by last_seen date
        # Ensure verification_score is numeric for sorting
        def phone_sort_key(p: dict[str, Any]) -> tuple[int, str]:
            score = p.get("verification_score", 0)
            try:
                score = int(score) if score is not None else 0
            except (ValueError, TypeError):
                score = 0
            return (score, p.get("last_seen") or "1900-01-01")
        
        verified_phones.sort(key=phone_sort_key, reverse=True)
        best_phone_id = verified_phones[0].get("id")
        log.info(
            f"Best phone selected: {verified_phones[0].get('phone_e164')} (score: {verified_phones[0].get('verification_score')})"
        )

    if verified_emails:
        # Sort by Hunter score - ensure it's numeric
        def email_sort_key(e: dict[str, Any]) -> int:
            score = e.get("hunter_score", 0)
            try:
                score = int(score) if score is not None else 0
            except (ValueError, TypeError):
                score = 0
            return score
        
        verified_emails.sort(key=email_sort_key, reverse=True)
        best_email_id = verified_emails[0].get("id")
        log.info(
            f"Best email selected: {verified_emails[0].get('email')} (score: {verified_emails[0].get('hunter_score')})"
        )

    # Update debtor with best contact references
    if best_phone_id or best_email_id:
        update_data = {}
        if best_phone_id:
            update_data["best_phone_id"] = best_phone_id
        if best_email_id:
            update_data["best_email_id"] = best_email_id

        try:
            dx.update_row("debtors", debtor_id, update_data)
            log.info(f"Updated debtor {debtor_id} with best contacts: {update_data}")
        except Exception as e:
            log.error(f"Failed to update debtor {debtor_id} with best contacts: {e}")

    # Summary
    log.info(
        f"Verification complete for debtor {debtor_id}: "
        f"{len(verified_phones)} verified phones, {len(verified_emails)} verified emails, "
        f"{len(removed_phones)} phones removed, {len(removed_emails)} emails removed"
    )

    return {
        "best_phone_id": best_phone_id,
        "best_email_id": best_email_id,
        "verified_phones": len(verified_phones),
        "verified_emails": len(verified_emails),
        "removed_phones": len(removed_phones),
        "removed_emails": len(removed_emails),
    }
