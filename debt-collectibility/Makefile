.PHONY: setup run test lint

setup:
	python -m venv .venv && .\.venv\Scripts\pip install -r requirements.txt

run:
	.\.venv\Scripts\python pipeline.py

test:
	.\.venv\Scripts\pytest -q

lint:
	.\.venv\Scripts\ruff .

.PHONY: diagnose
diagnose:
	.\.venv\Scripts\python scripts\diagnose_apis.py
	.\.venv\Scripts\python scripts\verify_directus_io.py

