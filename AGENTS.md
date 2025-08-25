# AGENTS.md - Development Guide

## Build/Test/Lint Commands
- `make setup` - Setup Python venv and install dependencies  
- `make run` - Run main pipeline.py script
- `make test` - Run all tests with pytest
- `make lint` - Run ruff linting
- `make diagnose` - Run diagnostic API tests
- **Single test**: `pytest tests/test_scoring.py -v` or `pytest tests/test_matching.py::test_specific_function`

## Architecture  
- **Main**: `debt-collectibility/` Python project for debt enrichment pipeline
- **Entry point**: `pipeline.py` - orchestrates staged enrichment via Directus API
- **Core modules**: `src/directus_client.py` (Directus API), `src/stages/` (enrichment stages), `src/utils/` (utilities)
- **Database**: Directus headless CMS storing debtor data with enrichment audit trails
- **APIs**: USPS, Skiptrace/Apify, bankruptcy lookups, property values, business data

## Code Style
- **Imports**: `from __future__ import annotations` at top, then stdlib, then 3rd party, then local
- **Types**: Use type hints with `typing` module, Dict/List for older Python compat  
- **Error handling**: Custom exceptions (e.g., `DirectusError`), tenacity for retries with exponential backoff
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Environment**: Use python-dotenv, prefix required env vars with `_required_env()` helper
