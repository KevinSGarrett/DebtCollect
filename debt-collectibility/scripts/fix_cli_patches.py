import re
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(p):
    return p.read_text(encoding="utf-8", errors="ignore")


def write(p, s):
    p.write_text(s, encoding="utf-8")


# A) logger.py â€” drop unused `# type: ignore`
p = ROOT / "src" / "utils" / "logger.py"
if p.exists():
    txt = read(p)
    new = re.sub(r"\s*#\s*type:\s*ignore\b.*$", "", txt, flags=re.M)
    if new != txt:
        write(p, new)

# B) matching.py â€” import Any; use dict[str, Any] in hints
p = ROOT / "src" / "utils" / "matching.py"
if p.exists():
    txt = read(p)
    if "from typing import Any" not in txt:
        if "from __future__ import annotations" in txt:
            txt = txt.replace(
                "from __future__ import annotations",
                "from __future__ import annotations\nfrom typing import Any",
            )
        else:
            txt = "from typing import Any\n" + txt

    def fix_line(line: str) -> str:
        head = line.lstrip()
        if (
            head.startswith("def ")
            or ("->" in line)
            or (":" in line and "(" in line and ")" in line)
        ):
            line = re.sub(r"(?<!\w)dict(?!\s*\[)", "dict[str, Any]", line)
        return line

    new = "\n".join(fix_line(line) for line in txt.splitlines())
    if new != txt:
        write(p, new)

# C) adapter.py â€” Optional[str] for `= None`; avoid duplicate typ/provider
p = ROOT / "src" / "stages" / "skiptrace_apify" / "adapter.py"
if p.exists():
    txt = read(p)
    # ensure Optional imported
    if "from typing import" in txt and "Optional" not in txt:
        txt = re.sub(
            r"from typing import ([^\n]+)",
            lambda m: (
                "from typing import " + (m.group(1) + ", Optional").replace(", ,", ", ")
            ),
            txt,
            count=1,
        )
    elif "Optional" not in txt:
        txt = "from typing import Optional\n" + txt
    # change `name: str = None` â†’ `name: Optional[str] = None`
    txt = re.sub(r"(\b\w+\b)\s*:\s*str\s*=\s*None\b", r"\1: Optional[str] = None", txt)
    # rename 2nd+ assignment of typ/provider to avoid redefinition
    lines = txt.splitlines()
    seen_typ = seen_provider = 0
    for i, line in enumerate(lines):
        if re.match(r"^\s*typ\s*=", line):
            seen_typ += 1
            if seen_typ > 1:
                lines[i] = re.sub(r"^\s*typ", "    ptype", line)
        if re.match(r"^\s*provider\s*=", line):
            seen_provider += 1
            if seen_provider > 1:
                lines[i] = re.sub(r"^\s*provider", "    pvendor", line)
    new = "\n".join(lines)
    if new != read(p):
        write(p, new)

# D) skiptrace_apify.py â€” ensure list[...] returned
p = ROOT / "src" / "stages" / "skiptrace_apify.py"
if p.exists():
    txt = read(p)
    # add cast import if missing (harmless)
    if "from typing import cast" not in txt and "from typing import" in txt:
        txt = txt.replace("from typing import", "from typing import cast,")

    # within any def ... -> list[dict[str, Any]]: wrap `return NAME` to `return list(NAME)`
    def patch_func(body: str) -> str:
        out = []
        for line in body.splitlines():
            m = re.match(r"(\s*)return\s+([A-Za-z_]\w*)\s*$", line)
            if m and ("list(" not in line):
                out.append(f"{m.group(1)}return list({m.group(2)})")
            else:
                out.append(line)
        return "\n".join(out)

    def repl(m):
        return m.group(1) + patch_func(m.group(2))

    pat = re.compile(
        r"(def\s+\w+\s*\([^)]*\)\s*->\s*list\[dict\[str,\s*Any\]\]\s*:\s*\n)((?:\s+.*\n)+)",
        re.M,
    )
    new = re.sub(pat, repl, txt)
    if new != txt:
        write(p, new)

print("Patch complete.")
