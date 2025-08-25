from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.stages.skiptrace_apify import _apify_skiptrace, _rapidapi_skiptrace


def test_skiptrace_functions():
    """Test the skiptrace functions directly without Directus"""

    # Load environment variables
    load_dotenv()

    print("🧪 Testing Skiptrace Functions\n")

    # Test data
    test_address = {"city": "Conroe", "state": "TX", "zip": "77301"}

    print("=== Testing RapidAPI Function ===")
    try:
        candidates, meta = _rapidapi_skiptrace("Kevin", "Garrett", test_address)
        print("✅ RapidAPI function executed successfully")
        print(f"   Found {len(candidates)} candidates")
        print(f"   Source: {meta.get('source')}")

        if candidates:
            print("   First candidate details:")
            candidate = candidates[0]
            print(f"     Name: {candidate.get('First Name')} {candidate.get('Last Name')}")
            print(f"     Address: {candidate.get('Street Address')}")
            print(f"     City: {candidate.get('Address Locality')}")
            print(f"     State: {candidate.get('Address Region')}")
            print(f"     Zip: {candidate.get('Postal Code')}")

            # Check for phones and emails
            phone_count = 0
            email_count = 0
            for i in range(1, 10):
                if candidate.get(f"Phone-{i}"):
                    phone_count += 1
                    print(f"     Phone {i}: {candidate.get(f'Phone-{i}')}")
                if candidate.get(f"Email-{i}"):
                    email_count += 1
                    print(f"     Email {i}: {candidate.get(f'Email-{i}')}")

            print(f"   Total phones: {phone_count}")
            print(f"   Total emails: {email_count}")

            # Check if address matches what we expect
            if (
                candidate.get("Address Locality") == "Conroe"
                and candidate.get("Address Region") == "TX"
            ):
                print("   ✅ Address matches expected location")
            else:
                print(
                    f"   ⚠️  Address mismatch: Expected Conroe, TX but got {candidate.get('Address Locality')}, {candidate.get('Address Region')}"
                )
        else:
            print("   No candidates found")

    except Exception as e:
        print(f"❌ RapidAPI function failed: {e}")
        import traceback

        traceback.print_exc()

    print("\n=== Testing Apify Function ===")
    try:
        candidates, meta = _apify_skiptrace("Kevin", "Garrett", test_address)
        print("✅ Apify function executed successfully")
        print(f"   Found {len(candidates)} candidates")
        print(f"   Source: {meta.get('source')}")

        if candidates:
            print("   First candidate details:")
            candidate = candidates[0]
            print(f"     Name: {candidate.get('First Name')} {candidate.get('Last Name')}")
            print(f"     Address: {candidate.get('Street Address')}")
            print(f"     City: {candidate.get('Address Locality')}")
            print(f"     State: {candidate.get('Address Region')}")
            print(f"     Zip: {candidate.get('Postal Code')}")

            # Check for phones and emails
            phone_count = 0
            email_count = 0
            for i in range(1, 10):
                if candidate.get(f"Phone-{i}"):
                    phone_count += 1
                    print(f"     Phone {i}: {candidate.get(f'Phone-{i}')}")
                if candidate.get(f"Email-{i}"):
                    email_count += 1
                    print(f"     Email {i}: {candidate.get(f'Email-{i}')}")

            print(f"   Total phones: {phone_count}")
            print(f"   Total emails: {email_count}")
        else:
            print("   No candidates found")

    except Exception as e:
        print(f"❌ Apify function failed: {e}")
        import traceback

        traceback.print_exc()

    print("\n🎯 Skiptrace testing completed!")


if __name__ == "__main__":
    test_skiptrace_functions()
