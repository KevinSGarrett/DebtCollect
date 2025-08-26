from __future__ import annotations
import argparse
import os
from dotenv import load_dotenv

from src.directus_client import DirectusClient
from src.stages import skiptrace_apify
from src.utils.logger import get_logger


def main() -> None:
    load_dotenv()
    log = get_logger()

    ap = argparse.ArgumentParser("skiptrace_apify CLI")
    ap.add_argument("--limit", type=int, default=5, help="How many debtors to process")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate phones/emails without hitting external APIs or writing",
    )
    args = ap.parse_args()

    # Use the stage's existing simulator when dry-running
    if args.dry_run:
        os.environ["SIMULATE"] = (
            "1"  # stage already supports this flag :contentReference[oaicite:3]{index=3}
        )

    dx = DirectusClient.from_env()
    debtors = dx.get_debtors_to_enrich(limit=args.limit)
    log.info(f"CLI: Found {len(debtors)} debtors to process")

    for d in debtors:
        try:
            patch = skiptrace_apify.run(d, dx)
            log.info(
                {"debtor_id": d.get("id"), "stage": "skiptrace_apify", "patch": patch}
            )
        except Exception as e:
            log.exception(f"skiptrace_apify failed for debtor {d.get('id')}: {e}")


if __name__ == "__main__":
    main()
