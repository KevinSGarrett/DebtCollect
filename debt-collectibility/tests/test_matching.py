from src.utils.matching import match_name_address, name_similarity, street_similarity


def test_name_similarity_basic():
    assert name_similarity("John Doe", "John Doe") == 100
    assert name_similarity("John A Doe", "John Doe") >= 80


def test_street_similarity_threshold():
    assert street_similarity("123 Main Street", "123 Main St") >= 90


def test_match_name_address_thresholds():
    debtor = {
        "first_name": "Jane",
        "last_name": "Smith",
        "address_line1": "500 Park Avenue",
        "state": "NY",
        "zip": "10022",
    }
    candidate_good = {
        "name": "Jane Smith",
        "street": "500 Park Ave",
        "state": "NY",
        "zip": "10022",
    }
    candidate_bad_zip = {**candidate_good, "zip": "90210"}
    assert match_name_address(debtor, candidate_good) >= 85
    assert match_name_address(debtor, candidate_bad_zip) == 0
