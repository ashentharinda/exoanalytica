import ast
from pathlib import Path

folder = Path("research/phase_2/pi_men/scripts")

class Audit(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename

    def visit_Call(self, node):
        name = ast.unparse(node.func)

        if name in ("pd.read_csv", "pd.DataFrame.to_csv"):
            for arg in node.args[:1]:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    print(f"{self.filename}: READ  {arg.value}")

        elif name in ("open", "Path"):
            for arg in node.args[:1]:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if arg.value.startswith("phase2_6_pi_men_"):
                        print(f"{self.filename}: PATH  {arg.value}")

        self.generic_visit(node)

for file in sorted(folder.glob("phase2_6_pi_men_*.py")):
    tree = ast.parse(file.read_text(encoding="utf-8-sig"))
    Audit(file.name).visit(tree)
