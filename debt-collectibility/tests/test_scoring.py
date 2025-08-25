class FakeDX:
    def __init__(self, phones=None, emails=None, cases=None, properties=None):
        self._phones = phones or []
        self._emails = emails or []
        self._cases = cases or []
        self._properties = properties or []
        self.snapshots = []

    def list_related(self, collection, filters, limit=100):
        if collection == "phones":
            return self._phones
        if collection == "emails":
            return self._emails
        if collection == "bankruptcy_cases":
            return self._cases
        if collection == "properties":
            return self._properties
        return []

    def create_row(self, collection, data):
        if collection == "scoring_snapshots":
            self.snapshots.append(data)
        return data


def test_scoring_bounds_and_penalties():
    from src.stages.scoring import run

    debtor = {"id": 1, "usps_standardized": True, "debt_owed": 1000, "business_confidence": 70}
    dx = FakeDX(
        phones=[{"is_verified": True, "line_type": "mobile", "last_seen": "2024-02-01"}],
        emails=[{"is_verified": True, "hunter_score": 95}],
        cases=[{"chapter": "7", "discharged_date": "2023-01-01"}],
        properties=[{"market_value": 200000, "owner_occupied": True}],
    )
    patch = run(debtor, dx)
    assert 1 <= patch["collectibility_score"] <= 100
    assert "reason" not in patch  # reason stored in snapshots
    assert len(dx.snapshots) == 1


def test_scoring_clamps_low():
    from src.stages.scoring import run

    debtor = {"id": 1, "usps_standardized": False, "debt_owed": 1000000, "business_confidence": 0}
    dx = FakeDX(
        phones=[{"is_verified": False}],
        emails=[{"is_verified": False}],
        cases=[{"chapter": "7", "discharged_date": "2024-01-01"}],
        properties=[],
    )
    patch = run(debtor, dx)
    assert 1 <= patch["collectibility_score"] <= 100
