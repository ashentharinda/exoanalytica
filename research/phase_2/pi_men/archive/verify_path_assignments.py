import ast
from pathlib import Path

folder = Path("research/phase_2/pi_men/scripts")

targets = {
    "phase2_6_pi_men_AB_bootstrap.py": ["REPORT", "OUTPUT"],
    "phase2_6_pi_men_c_epoch_baseline_validation.py": ["OUTPUT"],
    "phase2_6_pi_men_c_incremental.py": ["OUTPUT_CSV", "OUTPUT_REPORT"],
    "phase2_6_pi_men_comprehensive_validation.py": ["OUTPUT_CSV", "OUTPUT_REPORT"],
    "phase2_6_pi_men_correlated_noise.py": ["REPORT", "OUTPUT"],
    "phase2_6_pi_men_instrument_audit.py": ["OUTPUT_CSV", "OUTPUT_REPORT"],
    "phase2_6_pi_men_joint_fit.py": ["OUTPUT", "REPORT"],
    "phase2_6_pi_men_model_comparison.py": ["report_file"],
    "phase2_6_pi_men_parametric_bootstrap.py": ["REPORT", "OUTPUT"],
    "phase2_6_pi_men_pre_post_fit.py": ["output", "report"],
    "phase2_6_pi_men_prepare_corrected_data.py": ["OUTPUT", "REPORT"],
    "phase2_6_pi_men_published_validation.py": ["OUTPUT", "REPORT"],
    "phase2_6_pi_men_residual_verification.py": ["report_file"],
    "phase2_6_pi_men_three_model_comparison.py": ["OUTPUT_CSV", "OUTPUT_REPORT"],
}

for filename, names in targets.items():
    path = folder / filename
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))

    print(f"\n===== {filename} =====")

    found = set()

    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            if value is None:
                continue

            assigned_names = []
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        assigned_names.append(target.id)
            elif isinstance(node.target, ast.Name):
                assigned_names.append(node.target.id)

            for name in names:
                if name in assigned_names:
                    print(f"{name} = {ast.unparse(value)}")
                    found.add(name)

    for name in names:
        if name not in found:
            print(f"NOT FOUND AT MODULE LEVEL: {name}")

print("\n===== END OF ASSIGNMENT REVIEW =====")
