.DEFAULT_GOAL := help

venv:
python -m venv .venv

deps:
.venv/Scripts/python.exe -m pip install -U pip
.venv/Scripts/pip.exe install -r requirements.txt

lint:
.venv/Scripts/python.exe -m ruff check . --fix
.venv/Scripts/python.exe -m ruff format .

typecheck:
.venv/Scripts/python.exe -m mypy .

test:
.venv/Scripts/python.exe -m pytest -q --maxfail=1 --disable-warnings

coverage:
.venv/Scripts/python.exe -m pytest --cov=. --cov-report=xml

gate:
powershell -ExecutionPolicy Bypass -File scripts/quality_gate.ps1

help:
@echo "Targets: venv deps lint typecheck test coverage gate"
