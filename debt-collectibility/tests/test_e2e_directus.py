from __future__ import annotations

import os

import pytest

from src.directus_client import DirectusClient
from src.stages import (
    usps,
    skiptrace_apify,
    verify_contacts,
    bankruptcy,
    property_value,
    business_lookup,
    scoring,
)


pytestmark = pytest.mark.e2e


@pytest.mark.skipif(
    not os.getenv("DIRECTUS_URL") or not os.getenv("DIRECTUS_TOKEN"),
    reason="Directus not configured",
)
def test_full_pipeline_simulated_env(monkeypatch):
    # Use SIMULATE=1 to avoid external API calls but still exercise DB IO
    monkeypatch.setenv("SIMULATE", "1")
    dx = DirectusClient.from_env()

    debtor = dx.create_row(
        "debtors",
        {
            "first_name": "Kevin",
            "last_name": "Garrett",
            "address_line1": "1212 N Loop 336 W",
            "city": "Conroe",
            "state": "TX",
            "zip": "77301",
            "enrichment_status": "pending",
        },
    )
    debtor_id = debtor.get("id")

    try:
        # USPS
        patch = usps.run(debtor, dx)
        if patch:
            debtor = dx.update_row("debtors", debtor_id, patch)

        # Skiptrace (simulated inserts)
        _ = skiptrace_apify.run(debtor, dx)

        # Verify contacts (uses simulated phones/emails)
        _ = verify_contacts.run(debtor, dx)

        # Bankruptcy (no external in simulate mode; still should no-op gracefully)
        _ = bankruptcy.run(debtor, dx)

        # Property value (simulated census median)
        _ = property_value.run(debtor, dx)

        # Business lookup (no external in simulate, may return 0 confidence)
        _ = business_lookup.run(debtor, dx)

        # Scoring (creates snapshot)
        score_patch = scoring.run(debtor, dx)
        assert score_patch and 1 <= score_patch.get("collectibility_score", 0) <= 100

        # Validate artifacts
        addrs = dx.list_related("addresses", {"debtor_id": {"_eq": debtor_id}}, limit=5)
        phones = dx.list_related("phones", {"debtor_id": {"_eq": debtor_id}}, limit=50)
        emails = dx.list_related("emails", {"debtor_id": {"_eq": debtor_id}}, limit=50)
        props = dx.list_related(
            "properties", {"debtor_id": {"_eq": debtor_id}}, limit=10
        )
        snaps = dx.list_related(
            "scoring_snapshots", {"debtor_id": {"_eq": debtor_id}}, limit=5
        )

        assert addrs, "address row should exist"
        assert phones or emails, "contacts should be created in simulate"
        assert props, "property row should exist"
        assert snaps, "scoring snapshot should be created"

    finally:
        # Cleanup created artifacts
        for coll in (
            "phones",
            "emails",
            "properties",
            "addresses",
            "scoring_snapshots",
        ):
            for row in dx.list_related(
                coll, {"debtor_id": {"_eq": debtor_id}}, limit=200
            ):
                try:
                    dx.delete_row(coll, row.get("id"))
                except Exception:
                    pass
        dx.delete_row("debtors", debtor_id)
