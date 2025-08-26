import re
import pathlib

p = pathlib.Path(
    r"""C:\\DebtCollect\\debt-collectibility\\src\\stages\\skiptrace_apify.py"""
)
txt = p.read_text(encoding="utf-8")


def undo_in_dict_return_funcs(text: str) -> str:
    # Match defs with -> dict[...] | None  OR -> Optional[dict[...]]
    pat = re.compile(
        r"(?ms)"
        r"(def\s+\w+\s*\([^)]*\)\s*->\s*(?:Optional\s*\[\s*dict\[.*?\]\s*\]|dict\[.*?\]\s*\|\s*None)\s*:\s*\n)"
        r"((?:\s+.*\n?)*)"
    )

    def fix_body(body: str) -> str:
        out = []
        for line in body.splitlines():
            m = re.match(r"(\s*)return\s+list\((.+)\)\s*$", line)
            if m:
                indent, expr = m.groups()
                line = f"{indent}return {expr}"
            out.append(line)
        return "\n".join(out) + ("\n" if body.endswith("\n") else "")

    def repl(m: re.Match) -> str:
        return m.group(1) + fix_body(m.group(2))

    return pat.sub(repl, text)


new = undo_in_dict_return_funcs(txt)
if new != txt:
    p.write_text(new, encoding="utf-8")
    print("Fixed dict-return functions that were returning list(...).")
else:
    print("No dict-return functions needed fixes.")
