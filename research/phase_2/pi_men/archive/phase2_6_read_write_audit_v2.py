import ast
from pathlib import Path

folder = Path("research/phase_2/pi_men/scripts")

for file in sorted(folder.glob("phase2_6_pi_men_*.py")):
    tree = ast.parse(file.read_text(encoding="utf-8-sig"))

    print(f"\n===== {file.name} =====")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func = ast.unparse(node.func)

        if func.endswith("read_csv"):
            action = "READ"
        elif func.endswith("to_csv"):
            action = "WRITE"
        elif func.endswith("write_text"):
            action = "WRITE REPORT"
        elif func == "open":
            action = "OPEN FILE"
        else:
            continue

        args = ", ".join(ast.unparse(a) for a in node.args[:2])
        print(f"Line {node.lineno}: {action}: {func}({args})")
