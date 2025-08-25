# Debt Collectibility Workflow — SPEC

## Goal
Automate evaluation of debtor collectibility from minimal inputs to a scored, reasoned verdict.

## Input
CSV rows with columns:
first_name, last_name, possible_address, amount_owed

## High-Level Stages
1) Verifier Agent
   - USPS-style normalization, address confidence (0–1).
2) Bankruptcy Agent
   - CourtListener (and optionally PACER) lookups: chapter, status, filed/discharge dates.
3) Phone Agent
   - Enrich phones (PDL/one-api). Validate with RealPhoneValidation (RPV).
4) Email Agent
   - Enrich emails (Hunter). Verify deliverability.
5) Property Agent
   - Property presence signal (owner-occupied? inferred stability).
6) Scoring Agent
   - Combine features into 0–10 Collectibility Score + short explanation string.

## Output
- Write a normalized CSV at ./data/output/enriched_results.csv
- Columns include: input fields + verified_address + address_confidence + bankruptcy flags
  + phones_valid + emails_valid + property_signals + collectibility_score + reason

## Non-Goals (for now)
- No DB writes; local CSV/JSON only.
- No UI.

## Constraints
- All stages callable from workflows/collectibility_workflow.py via CLI.
- Must pass tests in tests/.
- Must satisfy Acceptance Criteria doc.
