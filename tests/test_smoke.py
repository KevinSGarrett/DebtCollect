from __future__ import annotations

import csv
from pathlib import Path

from workflows.collectibility_workflow import run


def test_smoke_creates_output(tmp_path: Path) -> None:
    # Copy sample to temp
    inp = tmp_path / "sample.csv"
    inp.write_text(
        Path("data/sample_input.csv").read_text(encoding="utf-8"), encoding="utf-8"
    )
    outp = tmp_path / "out.csv"
    path = run(str(inp), str(outp))
    assert Path(path).exists()

    with Path(path).open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) >= 1
    for r in rows:
        assert "collectibility_score" in r and r["collectibility_score"] != ""
        assert "reason" in r and r["reason"]
