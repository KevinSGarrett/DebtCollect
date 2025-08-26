from __future__ import annotations

from typing import Any


class MockDX:
    def __init__(self) -> None:
        self._store: dict[str, list[dict[str, Any]]] = {}
        self._id_counter = 1

    def _next_id(self) -> int:
        val = self._id_counter
        self._id_counter += 1
        return val

    def create_row(self, collection: str, data: dict[str, Any]) -> dict[str, Any]:
        row = {"id": self._next_id(), **data}
        self._store.setdefault(collection, []).append(row)
        return row

    def update_row(
        self, collection: str, id: Any, data: dict[str, Any]
    ) -> dict[str, Any]:
        for row in self._store.get(collection, []):
            if row.get("id") == id:
                row.update(data)
                return row
        return {}

    def delete_row(self, collection: str, id: Any) -> None:
        rows = self._store.get(collection, [])
        self._store[collection] = [r for r in rows if r.get("id") != id]

    def list_related(
        self, collection: str, filters: dict[str, Any], limit: int = 100
    ) -> list[dict[str, Any]]:
        rows = self._store.get(collection, [])

        # Extremely simple filter: only support equality on top-level fields for tests
        def matches(row: dict[str, Any]) -> bool:
            filt = filters or {}
            for key, cond in filt.items():
                if not isinstance(cond, dict) or "_eq" not in cond:
                    continue
                if row.get(key) != cond.get("_eq"):
                    return False
            return True

        return [r for r in rows if matches(r)][:limit]


def _make_debtor() -> dict[str, Any]:
    return {
        "id": 1,
        "first_name": "Kevin",
        "last_name": "Garrett",
        "address_line1": "1212 N Loop 336 W",
        "city": "Conroe",
        "state": "TX",
        "zip": "77301",
    }


def test_usps_simulate(monkeypatch):
    from src.stages import usps

    monkeypatch.setenv("SIMULATE", "1")
    dx = MockDX()
    debtor = _make_debtor()
    patch = usps.run(debtor, dx)
    assert patch and patch.get("usps_standardized") is True
    addrs = dx.list_related(
        "addresses",
        {"debtor_id": {"_eq": debtor["id"]}, "zip5": {"_eq": debtor["zip"][:5]}},
        limit=5,
    )
    assert addrs, "address should be created in simulate mode"


def test_skiptrace_simulate(monkeypatch):
    from src.stages import skiptrace_apify

    monkeypatch.setenv("SIMULATE", "1")
    dx = MockDX()
    debtor = _make_debtor()
    res = skiptrace_apify.run(debtor, dx)
    assert res is None
    phones = dx.list_related("phones", {"debtor_id": {"_eq": debtor["id"]}}, limit=50)
    emails = dx.list_related("emails", {"debtor_id": {"_eq": debtor["id"]}}, limit=50)
    assert phones or emails, "simulate should create some contacts"


def test_property_value_simulate(monkeypatch):
    from src.stages import property_value

    monkeypatch.setenv("SIMULATE", "1")
    dx = MockDX()
    debtor = _make_debtor()
    res = property_value.run(debtor, dx)
    assert res is None
    props = dx.list_related(
        "properties", {"debtor_id": {"_eq": debtor["id"]}}, limit=10
    )
    assert props and props[0].get("market_value") is not None


def test_verify_contacts_with_mocks(monkeypatch):
    from src.stages import verify_contacts

    dx = MockDX()
    debtor = _make_debtor()
    # Seed phone/email
    ph = dx.create_row(
        "phones",
        {"debtor_id": debtor["id"], "phone_e164": "+12146093136", "match_strength": 90},
    )
    em = dx.create_row(
        "emails",
        {"debtor_id": debtor["id"], "email": "test@example.com", "match_strength": 90},
    )

    # Monkeypatch external lookups to avoid network
    def fake_rpv_lookup(phone_e164: str) -> dict[str, Any]:
        return {"status": "connected", "phone_type": "mobile", "carrier": "TestCarrier"}

    def fake_hunter_verify(email: str) -> dict[str, Any]:
        return {"data": {"status": "valid", "score": 90}}

    monkeypatch.setenv("REALPHONEVALIDATION_ENABLED", "1")
    monkeypatch.setenv("HUNTER_API_KEY", "dummy")
    monkeypatch.setattr(verify_contacts, "_rpv_lookup", fake_rpv_lookup)
    monkeypatch.setattr(verify_contacts, "_hunter_verify", fake_hunter_verify)

    out = verify_contacts.run(debtor, dx)
    assert out is not None
    assert out.get("best_phone_id") == ph["id"]
    assert out.get("best_email_id") == em["id"]


def test_bankruptcy_run_with_mock(monkeypatch):
    from src.stages import bankruptcy

    dx = MockDX()
    debtor = _make_debtor()

    def fake_search(
        full_name: str, city: str, state: str, zip5: str
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": "X1",
                "case_number": "22-12345",
                "court": state,
                "chapter": "7",
                "filed_date": "2023-05-01",
                "status": "open",
                "discharge_date": None,
                "docket_url": "https://example.com",
                "match_strength": 95,
                "raw": {},
            }
        ]

    monkeypatch.setattr(bankruptcy, "_courtlistener_search", fake_search)
    res = bankruptcy.run(debtor, dx)
    assert res is None
    cases = dx.list_related(
        "bankruptcy_cases", {"debtor_id": {"_eq": debtor["id"]}}, limit=10
    )
    assert cases and cases[0].get("case_number") == "22-12345"


def test_business_lookup_with_mock(monkeypatch):
    from src.stages import business_lookup

    dx = MockDX()
    debtor = _make_debtor()

    def fake_places(query: str, lat: float | None, lng: float | None) -> dict[str, Any]:
        return {
            "results": [
                {"name": "KG Plumbing", "website": "https://kg.example", "url": ""}
            ]
        }

    monkeypatch.setattr(business_lookup, "_google_places_search", fake_places)
    out = business_lookup.run(debtor, dx)
    assert out is not None and out.get("business_confidence", 0) >= 50
    links = dx.list_related(
        "debtor_businesses", {"debtor_id": {"_eq": debtor["id"]}}, limit=10
    )
    assert links, "should link debtor to a business when result exists"
