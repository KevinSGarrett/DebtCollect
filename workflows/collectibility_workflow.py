from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from debt_collectibility.agents import (
    check_bankruptcy,
    enrich_emails,
    enrich_phones,
    property_signal,
    score_collectibility,
    verify_address,
)


def run(csv_path: str, out_path: str = "data/output/enriched_results.csv") -> str:
    in_file = Path(csv_path)
    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    with in_file.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            first = (row.get("first_name") or "").strip()
            last = (row.get("last_name") or "").strip()
            addr = (row.get("possible_address") or "").strip()
            amount = row.get("amount_owed")

            vaddr = verify_address(addr)
            bk = check_bankruptcy(first, last)
            ph = enrich_phones(first, last)
            em = enrich_emails(first, last)
            prop = property_signal(addr)

            feats = {
                "address_confidence": vaddr.confidence,
                "has_bankruptcy": bk["has_bankruptcy"],
                "phones_valid": ph["phones_valid"],
                "emails_valid": em["emails_valid"],
                "property_present": prop["property_present"],
            }
            score, reason = score_collectibility(feats)

            rows.append(
                {
                    "first_name": first,
                    "last_name": last,
                    "possible_address": addr or None,
                    "amount_owed": amount,
                    "verified_address": vaddr.normalized,
                    "address_confidence": vaddr.confidence,
                    "has_bankruptcy": bk["has_bankruptcy"],
                    "phones_valid": ph["phones_valid"],
                    "emails_valid": em["emails_valid"],
                    "property_present": prop["property_present"],
                    "owner_occupied_likelihood": prop["owner_occupied_likelihood"],
                    "collectibility_score": score,
                    "reason": reason,
                }
            )

    fieldnames = list(rows[0].keys()) if rows else []
    with out_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return str(out_file)


def cli() -> None:
    parser = argparse.ArgumentParser(description="Debt Collectibility Workflow")
    parser.add_argument(
        "--csv",
        type=str,
        default="data/sample_input.csv",
        help="Path to input CSV",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="data/output/enriched_results.csv",
        help="Path to output CSV",
    )
    args = parser.parse_args()
    path = run(args.csv, args.out)
    print(f"Wrote: {path}")  # pragma: no cover


if __name__ == "__main__":
    cli()
