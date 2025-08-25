from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.directus_client import DirectusClient
from src.stages.skiptrace_apify import run as skiptrace_run
from src.stages.verify_contacts import run as verify_contacts_run


def test_pipeline_stages():
    """Test both skiptrace_apify and verify_contacts stages working together"""

    # Load environment variables
    load_dotenv()

    # Initialize Directus client
    try:
        dx = DirectusClient.from_env()
        print("[OK] Directus client initialized successfully")
    except Exception as e:
        print(f"[ERROR] Failed to initialize Directus client: {e}")
        return

    # Test debtor data (Garrett family)
    test_debtors = [
        {
            "first_name": "Kevin",
            "last_name": "Garrett",
            "address_line1": "1212 N Loop 336 W",
            "city": "Conroe",
            "state": "TX",
            "zip": "77301",
        },
        {
            "first_name": "Dana",
            "last_name": "Garrett",
            "address_line1": "1212 N Loop 336 W",
            "city": "Conroe",
            "state": "TX",
            "zip": "77301",
        },
        {
            "first_name": "Linda",
            "last_name": "Garrett",
            "address_line1": "1212 N Loop 336 W",
            "city": "Conroe",
            "state": "TX",
            "zip": "77301",
        },
    ]

    print("\n=== Testing Pipeline Stages ===\n")

    for i, debtor_data in enumerate(test_debtors, 1):
        print(f"--- Testing Debtor {i}: {debtor_data['first_name']} {debtor_data['last_name']} ---")

        # Step 1: Create test debtor in Directus
        try:
            debtor = dx.create_row("debtors", debtor_data)
            debtor_id = debtor.get("id")
            print(f"[OK] Created debtor with ID: {debtor_id}")
        except Exception as e:
            print(f"❌ Failed to create debtor: {e}")
            continue

        # Step 2: Run skiptrace_apify stage
        print("\n2. Running skiptrace_apify stage...")
        try:
            skiptrace_result = skiptrace_run(debtor, dx)
            if skiptrace_result:
                print(f"[OK] Skiptrace completed: {skiptrace_result}")
            else:
                print("[OK] Skiptrace completed (no updates)")
        except Exception as e:
            print(f"❌ Skiptrace failed: {e}")
            continue

        # Step 3: Check what was created
        try:
            phones = dx.list_related("phones", {"debtor_id": {"_eq": debtor_id}}, limit=100)
            emails = dx.list_related("emails", {"debtor_id": {"_eq": debtor_id}}, limit=100)
            print(f"[INFO] Found {len(phones)} phones and {len(emails)} emails after skiptrace")

            if phones:
                print("   Phones:")
                for ph in phones[:3]:  # Show first 3
                    print(
                        f"     - {ph.get('phone_e164')} (match: {ph.get('match_strength')}, source: {ph.get('provenance')})"
                    )

            if emails:
                print("   Emails:")
                for em in emails[:3]:  # Show first 3
                    print(
                        f"     - {em.get('email')} (match: {em.get('match_strength')}, source: {em.get('provenance')})"
                    )

        except Exception as e:
            print(f"❌ Failed to check created contacts: {e}")

        # Step 4: Run verify_contacts stage
        print("\n3. Running verify_contacts stage...")
        try:
            verify_result = verify_contacts_run(debtor, dx)
            if verify_result:
                print(f"[OK] Verification completed: {verify_result}")
            else:
                print("[OK] Verification completed (no updates)")
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            continue

        # Step 5: Check final state
        try:
            final_phones = dx.list_related("phones", {"debtor_id": {"_eq": debtor_id}}, limit=100)
            final_emails = dx.list_related("emails", {"debtor_id": {"_eq": debtor_id}}, limit=100)

            verified_phones = [p for p in final_phones if p.get("is_verified")]
            verified_emails = [e for e in final_emails if e.get("is_verified")]

            print(
                f"[INFO] Final state: {len(final_phones)} total phones, {len(verified_phones)} verified"
            )
            print(
                f"[INFO] Final state: {len(final_emails)} total emails, {len(verified_emails)} verified"
            )

            if verified_phones:
                print("   Verified phones:")
                for ph in verified_phones:
                    print(
                        f"     - {ph.get('phone_e164')} (score: {ph.get('verification_score')}, carrier: {ph.get('carrier_name')})"
                    )

            if verified_emails:
                print("   Verified emails:")
                for em in verified_emails:
                    print(f"     - {em.get('email')} (score: {em.get('hunter_score')})")

        except Exception as e:
            print(f"❌ Failed to check final state: {e}")

        # Clean up test debtor (delete by ids to satisfy Directus filter requirements)
        try:
            for ph in dx.list_related("phones", {"debtor_id": {"_eq": debtor_id}}, limit=200):
                try:
                    dx.delete_row("phones", ph.get("id"))
                except Exception as de:
                    print(f"⚠️  Could not delete phone {ph.get('id')}: {de}")
            for em in dx.list_related("emails", {"debtor_id": {"_eq": debtor_id}}, limit=200):
                try:
                    dx.delete_row("emails", em.get("id"))
                except Exception as de:
                    print(f"⚠️  Could not delete email {em.get('id')}: {de}")
            dx.delete_row("debtors", debtor_id)
            print(f"[CLEANUP] Cleaned up test debtor {debtor_id}")
        except Exception as e:
            print(f"[WARN] Failed to clean up test debtor {debtor_id}: {e}")

        print("\n" + "=" * 60 + "\n")

    print("[DONE] Pipeline testing completed!")


if __name__ == "__main__":
    test_pipeline_stages()
