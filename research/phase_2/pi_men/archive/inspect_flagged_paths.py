from pathlib import Path

folder = Path("research/phase_2/pi_men/scripts")

targets = {
    "phase2_6_pi_men_AB_bootstrap.py": [296],
    "phase2_6_pi_men_activity_indicator_validation.py": [161],
    "phase2_6_pi_men_c_epoch_baseline_validation.py": [124],
    "phase2_6_pi_men_c_incremental.py": [282],
    "phase2_6_pi_men_comprehensive_validation.py": [330, 359],
    "phase2_6_pi_men_corrected_alias_analysis.py": [18, 395],
    "phase2_6_pi_men_correlated_noise.py": [400],
    "phase2_6_pi_men_detrended_activity_validation.py": [177],
    "phase2_6_pi_men_epoch_alias_analysis.py": [137],
    "phase2_6_pi_men_instrument_audit.py": [226],
    "phase2_6_pi_men_joint_fit.py": [403],
    "phase2_6_pi_men_model_comparison.py": [325],
    "phase2_6_pi_men_parametric_bootstrap.py": [307],
    "phase2_6_pi_men_pre_post_fit.py": [169],
    "phase2_6_pi_men_prepare_corrected_data.py": [102],
    "phase2_6_pi_men_published_period_validation.py": [200],
    "phase2_6_pi_men_published_validation.py": [174],
    "phase2_6_pi_men_residual_verification.py": [288],
    "phase2_6_pi_men_three_model_comparison.py": [339],
}

for filename, line_numbers in targets.items():
    path = folder / filename
    lines = path.read_text(encoding="utf-8-sig").splitlines()

    print(f"\n===== {filename} =====")

    for number in line_numbers:
        start = max(1, number - 5)
        end = min(len(lines), number + 3)

        print(f"\n--- Lines {start}-{end} ---")
        for index in range(start, end + 1):
            print(f"{index:4}: {lines[index - 1]}")
