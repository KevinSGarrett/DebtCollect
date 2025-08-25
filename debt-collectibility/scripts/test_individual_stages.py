from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.stages.skiptrace_apify import _rapidapi_skiptrace
from src.stages.verify_contacts import _hunter_verify, _rpv_lookup


def test_rapidapi_function():
    """Test RapidAPI function directly"""
    print("=== Testing RapidAPI Function ===")

    address = {"city": "Conroe", "state": "TX", "zip": "77301"}

    try:
        candidates, meta = _rapidapi_skiptrace("Kevin", "Garrett", address)
        print("✅ RapidAPI function executed successfully")
        print(f"   Found {len(candidates)} candidates")
        print(f"   Source: {meta.get('source')}")

        if candidates:
            print("   First candidate:")
            for key, value in list(candidates[0].items())[:10]:  # Show first 10 fields
                print(f"     {key}: {value}")
        else:
            print("   No candidates found")

    except Exception as e:
        print(f"❌ RapidAPI function failed: {e}")
        import traceback

        traceback.print_exc()


def test_hunter_function():
    """Test Hunter.io function directly"""
    print("\n=== Testing Hunter.io Function ===")

    # Test with a sample email
    test_email = "test@example.com"

    try:
        result = _hunter_verify(test_email)
        print("✅ Hunter.io function executed successfully")
        print(f"   Response: {result}")

        if "data" in result:
            data = result["data"]
            print(f"   Status: {data.get('status')}")
            print(f"   Score: {data.get('score')}")

    except Exception as e:
        print(f"❌ Hunter.io function failed: {e}")
        import traceback

        traceback.print_exc()


def test_rpv_function():
    """Test Real Phone Validation function directly"""
    print("\n=== Testing Real Phone Validation Function ===")

    # Test with a sample phone number
    test_phone = "+15551234567"

    try:
        result = _rpv_lookup(test_phone)
        print("✅ RPV function executed successfully")
        print(f"   Response: {result}")

        if "status" in result:
            print(f"   Status: {result.get('status')}")
            print(f"   Confidence: {result.get('confidence')}")

    except Exception as e:
        print(f"❌ RPV function failed: {e}")
        import traceback

        traceback.print_exc()


def main():
    """Run all tests"""
    print("🧪 Testing Individual Pipeline Functions\n")

    # Load environment variables
    load_dotenv()

    # Check required environment variables
    required_vars = ["RAPIDAPI_KEY", "HUNTER_API_KEY", "REALPHONEVALIDATION_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"⚠️  Missing environment variables: {missing_vars}")
        print("   Some tests may fail")

    # Run tests
    test_rapidapi_function()
    test_hunter_function()
    test_rpv_function()

    print("\n🎯 Individual function testing completed!")


if __name__ == "__main__":
    main()
