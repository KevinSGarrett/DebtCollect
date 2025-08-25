from __future__ import annotations

import os
import pytest
import requests


pytestmark = pytest.mark.live


def _has(var: str) -> bool:
    return bool(os.getenv(var))


@pytest.mark.skipif(not _has("USPS_USER_ID"), reason="missing USPS_USER_ID")
def test_usps_env_present():
    assert os.getenv("USPS_USER_ID")


@pytest.mark.skipif(not _has("APIFY_TOKEN"), reason="missing APIFY_TOKEN")
def test_apify_whoami():
    r = requests.get(
        "https://api.apify.com/v2/me",
        headers={"Authorization": f"Bearer {os.getenv('APIFY_TOKEN')}"},
        timeout=20,
    )
    assert r.status_code in (200, 401, 403)


def test_census_reachable():
    r = requests.get("https://api.census.gov/data.html", timeout=20)
    assert r.ok


@pytest.mark.skipif(not _has("HUNTER_API_KEY"), reason="missing HUNTER_API_KEY")
def test_hunter_ping():
    r = requests.get(
        f"https://api.hunter.io/v2/domain-search?domain=example.com&api_key={os.getenv('HUNTER_API_KEY')}",
        timeout=20,
    )
    assert r.status_code in (200, 401, 403)


@pytest.mark.skipif(not _has("REALPHONEVALIDATION_API_KEY"), reason="missing RPV key")
def test_rpv_status_shape():
    # Not a real phone; expect either 200 with JSON or 4xx
    params = {"output": "json", "phone": "5555555555", "token": os.getenv("REALPHONEVALIDATION_API_KEY")}
    r = requests.get(
        os.getenv("REALPHONEVALIDATION_URL", os.getenv("REALVALIDATION_URL", "https://api.realvalidation.com/rpvWebService/TurboV3.php")),
        params=params,
        timeout=20,
    )
    assert r.status_code in (200, 400, 401, 403, 404)
    if r.ok:
        _ = r.json()


@pytest.mark.skipif(not _has("TWILIO_ACCOUNT_SID") or not _has("TWILIO_AUTH_TOKEN"), reason="missing Twilio creds")
def test_twilio_lookup_status():
    r = requests.get(
        "https://lookups.twilio.com/v1/PhoneNumbers/+15555555555?Type=carrier",
        auth=(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN")),
        timeout=20,
    )
    assert r.status_code in (200, 404, 429, 401)


@pytest.mark.skipif(not _has("GOOGLE_MAPS_API_KEY"), reason="missing Google key")
def test_google_places_status():
    r = requests.get(
        "https://maps.googleapis.com/maps/api/place/textsearch/json",
        params={"query": "test", "key": os.getenv("GOOGLE_MAPS_API_KEY")},
        timeout=20,
    )
    assert r.status_code in (200, 400, 403)


