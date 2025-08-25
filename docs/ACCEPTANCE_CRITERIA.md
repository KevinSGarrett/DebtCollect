# Acceptance Criteria

1) CLI
- Running:  `.venv\Scripts\python.exe workflows\collectibility_workflow.py --csv data\sample_input.csv`
  creates: `data\output\enriched_results.csv` with at least the input columns + `collectibility_score` and `reason`.

2) Deterministic Offline Mode
- When no API keys present, use deterministic mock paths so tests pass consistently.

3) Scoring
- Returns integer 0–10 and non-empty human-readable reason for each row.

4) Gates
- `ruff check --fix .` exits 0
- `mypy .` exits 0
- `pytest -q` exits 0
- Coverage >= 85% (line)

5) Structure
- Code lives under `debt_collectibility/` and `workflows/`. No orphan scripts at root.

6) Logging
- Minimal run log to stdout + optional `./data/logs/run.log`.
