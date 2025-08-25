# Auto Objective (paste into Cursor Auto Dev)

You are building a production-grade **Debt Collectibility Workflow** in Python that:
- Reads CSV `data/sample_input.csv` (or a provided `--csv` path),
- Runs the 6-stage pipeline (Verifier, Bankruptcy, Phone, Email, Property, Scoring),
- Writes `data/output/enriched_results.csv`,
- Satisfies `docs/ACCEPTANCE_CRITERIA.md`,
- Passes gates in `scripts/quality_gate.ps1`.

Work within the rules in `.cursorrules`, use structure in `docs/SPEC.md`, and make tests pass.
Do not change gate scripts or acceptance criteria; make code comply.
