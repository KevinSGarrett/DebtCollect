from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.stages.skiptrace_apify import run as skiptrace_run


def test_skiptrace_with_manual_data():
    """Test the skiptrace function with manual data enabled"""

    # Load environment variables
    load_dotenv()

    # Set the manual apify directory
    manual_dir = os.path.join(ROOT, "manual_apify")
    os.environ["MANUAL_APIFY_DIR"] = manual_dir

    print("🧪 Testing Skiptrace with Manual Data\n")
    print(f"Manual directory set to: {manual_dir}")
    print(f"Directory exists: {os.path.exists(manual_dir)}")

    # List manual files
    if os.path.exists(manual_dir):
        files = os.listdir(manual_dir)
        print(f"Manual files found: {files}")

    # Test debtor data
    test_debtor = {
        "id": 999,  # Mock ID for testing
        "first_name": "Kevin",
        "last_name": "Garrett",
        "address_line1": "1212 N Loop 336 W",
        "city": "Conroe",
        "state": "TX",
        "zip": "77301",
    }

    print(f"\nTesting with debtor: {test_debtor['first_name']} {test_debtor['last_name']}")
    print(
        f"Address: {test_debtor['address_line1']}, {test_debtor['city']}, {test_debtor['state']} {test_debtor['zip']}"
    )

    # Mock Directus client for testing
    class MockDirectusClient:
        def list_related(self, collection, filters, limit=100):
            return []  # Return empty list for phones/emails

        def create_row(self, collection, data):
            print(f"   📝 Would create {collection}: {data}")
            return {"id": 123, **data}

    mock_dx = MockDirectusClient()

    try:
        print("\n=== Running Skiptrace Function ===")
        result = skiptrace_run(test_debtor, mock_dx)

        if result:
            print(f"✅ Skiptrace completed with result: {result}")
        else:
            print("✅ Skiptrace completed (no updates)")

    except Exception as e:
        print(f"❌ Skiptrace failed: {e}")
        import traceback

        traceback.print_exc()

    print("\n🎯 Manual data testing completed!")


if __name__ == "__main__":
    test_skiptrace_with_manual_data()
