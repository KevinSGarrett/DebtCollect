import re
import pathlib

p = pathlib.Path(
    r"""C:\\DebtCollect\\debt-collectibility\\src\\stages\\skiptrace_apify.py"""
)
txt = p.read_text(encoding="utf-8")


def patch_body(body: str) -> str:
    out = []
    for line in body.splitlines():
        m = re.match(r"(\s*)return\s+(.+)\s*$", line)
        if m:
            indent, expr = m.groups()
            # leave alone if it's clearly already a list or list(...)
            if not (
                expr.startswith("list(")
                or expr.startswith("[")
                or expr.startswith("cast(")
            ):
                line = f"{indent}return list({expr})"
        out.append(line)
    return "\n".join(out) + ("\n" if body.endswith("\n") else "")


def repl(m: re.Match) -> str:
    header, body = m.group(1), m.group(2)
    return header + patch_body(body)


pat = re.compile(
    r"(def\s+\w+\s*\([^)]*\)\s*->\s*list\[dict\[str,\s*Any\]\]\s*:\s*\n)((?:\s+.*\n?)*)",
    re.M,
)
new = re.sub(pat, repl, txt)

if new != txt:
    p.write_text(new, encoding="utf-8")
    print("skiptrace_apify.py: patched returns in list[...] functions.")
else:
    print("skiptrace_apify.py: no changes needed.")
