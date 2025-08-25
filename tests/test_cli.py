from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch

from workflows.collectibility_workflow import cli


def test_cli_smoke(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    inp = tmp_path / "in.csv"
    inp.write_text(
        "first_name,last_name,possible_address,amount_owed\nJane,Doe,123 Main,42\n",
        encoding="utf-8",
    )
    outp = tmp_path / "out.csv"

    # Keep output clean
    monkeypatch.setenv("PYTHONWARNINGS", "ignore")
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")

    # Simulate argv: --csv <in> --out <out>
    import sys

    old = sys.argv[:]
    try:
        sys.argv = ["prog", "--csv", str(inp), "--out", str(outp)]
        cli()
        assert outp.exists()
    finally:
        sys.argv = old
