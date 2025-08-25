## Debt Collectibility Enrichment Pipeline

This project enriches and verifies contact, legal, property, and business signals for debtors stored in Directus, then computes a standardized 1–100 collectability score. It is idempotent, retriable, and logs a complete audit trail via `enrichment_runs`.

### Features
- Deterministic staged enrichment with provenance and raw payload storage
- Idempotent inserts (find-or-create) and safe reruns
- Tenacity-backed retries with backoff/jitter for 429/5xx
- Centralized logging with request IDs
- Scoring snapshots with concise reason text

### Repository Layout
```
debt-collectibility/
├─ README.md
├─ .env.example
├─ requirements.txt
├─ Makefile
├─ pipeline.py
├─ src/
│  ├─ directus_client.py
│  ├─ utils/
│  │  ├─ normalize.py
│  │  ├─ matching.py
│  │  ├─ rate_limit.py
│  │  └─ logger.py
│  └─ stages/
│     ├─ usps.py
│     ├─ skiptrace_apify.py
│     ├─ verify_contacts.py
│     ├─ bankruptcy.py
│     ├─ property_value.py
│     ├─ business_lookup.py
│     └─ scoring.py
└─ tests/
   ├─ test_matching.py
   └─ test_scoring.py
```

### Setup
1. Copy `.env.example` to `.env` and fill in production keys.
2. Run:
```
make setup
```

### Run
```
make run
```

### Test and Lint
```
make test
make lint
```

### Environment variables
All secrets are loaded from `.env`. The pipeline will fail fast with helpful errors if required variables are missing.

### Compliance
FDCPA/TCPA, Hunter.io ToS, CourtListener/PACER ToS — this tool performs read-only discovery; it does not initiate contact.

### Notes
- External API modules are isolated under `src/stages/` for easy swapping.
- Where provider data is ambiguous, we prefer deterministic matching using `rapidfuzz`.
- Phones are normalized to E.164; emails are stored as-is (lowercased) with verification metadata.


