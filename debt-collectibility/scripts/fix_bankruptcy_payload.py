import ast
import pathlib

p = pathlib.Path(r"C:\\DebtCollect\\debt-collectibility\\src\\stages\\bankruptcy.py")
src = p.read_text(encoding="utf-8")

tree = ast.parse(src)
lines = src.splitlines(keepends=True)


def insert_after_def_and_doc(fn: ast.FunctionDef):
    # find where function suite starts
    # after the docstring if present; otherwise after the def line
    # If first stmt is a string literal (docstring), insert after it
    insert_line = fn.lineno + 1
    if (
        fn.body
        and isinstance(fn.body[0], ast.Expr)
        and isinstance(getattr(fn.body[0], "value", None), ast.Str)
    ):
        insert_line = fn.body[0].end_lineno or fn.body[0].lineno
    indent = " " * (fn.col_offset + 4)
    init = (
        f"{indent}from typing import Any, Optional\n"
        f"{indent}payload: Optional[dict[str, Any]] = None\n"
    )
    # Don’t duplicate if already initialized
    body_text = "".join(
        lines[fn.lineno - 1 : (fn.body[-1].end_lineno if fn.body else fn.lineno)]
    )
    if (
        "payload: Optional[dict[str, Any]] = None" in body_text
        or "payload = None" in body_text
    ):
        return
    # insert
    lines.insert(insert_line, init)


for node in tree.body:
    if isinstance(node, ast.FunctionDef):
        # Only touch functions that reference a name "payload"
        src_slice = "".join(
            lines[
                node.lineno
                - 1 : (node.body[-1].end_lineno if node.body else node.lineno)
            ]
        )
        if "payload" in src_slice:
            insert_after_def_and_doc(node)

new = "".join(lines)
if new != src:
    p.write_text(new, encoding="utf-8")
    print("bankruptcy.py patched.")
else:
    print("bankruptcy.py unchanged.")
