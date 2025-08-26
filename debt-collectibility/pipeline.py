from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from typing import Any

from dotenv import load_dotenv
from src.directus_client import DirectusClient
from src.stages import (
    bankruptcy,
    business_lookup,
    property_value,
    scoring,
    skiptrace_apify,
    usps,
    verify_contacts,
)
from src.utils.logger import get_logger


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def main() -> None:
    load_dotenv()
    log = get_logger()
    batch_limit = int(os.getenv("BATCH_LIMIT", "25"))
    dx = DirectusClient.from_env()

    debtors = dx.get_debtors_to_enrich(limit=batch_limit)
    log.info(f"Found {len(debtors)} debtors to enrich")

    for debtor in debtors:
        debtor_id = debtor.get("id")
        run_id = None
        try:
            run = dx.create_row(
                "enrichment_runs",
                {
                    "debtor_id": debtor_id,
                    "status": "running",
                    "started_at": _now_iso(),
                    "stage_results": json.dumps([]),
                },
            )
            run_id = run.get("id") if run else None
        except Exception as e:
            log.warning(f"Unable to create enrichment_run for debtor {debtor_id}: {e}")
        stage_results: list[dict[str, Any]] = []
        try:
            dx.update_row("debtors", debtor_id, {"enrichment_status": "running"})

            stages = [
                ("usps", usps.run),
                ("skiptrace_apify", skiptrace_apify.run),
                ("verify_contacts", verify_contacts.run),
                ("bankruptcy", bankruptcy.run),
                ("property_value", property_value.run),
                ("business_lookup", business_lookup.run),
                ("scoring", scoring.run),
            ]

            for stage_name, stage_fn in stages:
                t0 = time.perf_counter()
                try:
                    patch = stage_fn(debtor, dx)
                    elapsed = time.perf_counter() - t0
                    if patch:
                        dx.update_row("debtors", debtor_id, patch)
                    stage_results.append(
                        {
                            stage_name: {
                                "ok": True,
                                "seconds": round(elapsed, 3),
                            }
                        }
                    )
                    log.info(
                        f"Debtor {debtor_id} stage={stage_name} seconds={elapsed:.2f}"
                    )
                except Exception as se:
                    elapsed = time.perf_counter() - t0
                    stage_results.append(
                        {
                            stage_name: {
                                "ok": False,
                                "seconds": round(elapsed, 3),
                                "error": str(se),
                            }
                        }
                    )
                    log.exception(
                        f"Stage {stage_name} failed for debtor {debtor_id}: {se}"
                    )
                    # Continue to next stage

            dx.update_row(
                "debtors",
                debtor_id,
                {"enrichment_status": "complete", "last_enriched_at": _now_iso()},
            )
            if run_id:
                try:
                    dx.update_row(
                        "enrichment_runs",
                        run_id,
                        {
                            "status": "complete",
                            "finished_at": _now_iso(),
                            "stage_results": json.dumps(stage_results),
                        },
                    )
                except Exception as e:
                    log.warning(f"Unable to update enrichment_run {run_id}: {e}")
        except Exception as e:
            log.exception(f"Debtor {debtor_id} enrichment error: {e}")
            dx.update_row("debtors", debtor_id, {"enrichment_status": "error"})
            if run_id:
                try:
                    dx.update_row(
                        "enrichment_runs",
                        run_id,
                        {
                            "status": "error",
                            "finished_at": _now_iso(),
                            "errors": json.dumps({"message": str(e)}),
                            "stage_results": json.dumps(stage_results),
                        },
                    )
                except Exception as e2:
                    log.warning(
                        f"Unable to write error to enrichment_run {run_id}: {e2}"
                    )


if __name__ == "__main__":
    main()
