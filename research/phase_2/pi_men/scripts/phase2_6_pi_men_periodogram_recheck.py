from paths import DATA_DIR, RESULTS_DIR, REPORTS_DIR
import numpy as np
import pandas as pd
from astropy.timeseries import LombScargle

path = DATA_DIR / "phase2_6_pi_men_harps_timeseries.csv"
df = pd.read_csv(path)

def analyse(label, data):
    data = data.copy()
    data = data[
        np.isfinite(data["bjd"]) &
        np.isfinite(data["rv_relative_ms"]) &
        np.isfinite(data["rv_error_ms"]) &
        (data["rv_error_ms"] > 0)
    ]

    t = data["bjd"].to_numpy()
    y = data["rv_relative_ms"].to_numpy()
    dy = data["rv_error_ms"].to_numpy()

    ls = LombScargle(t, y, dy, fit_mean=True, center_data=True)

    freq, power = ls.autopower(
        minimum_frequency=1/3000,
        maximum_frequency=1/2,
        samples_per_peak=10
    )

    periods = 1/freq
    order = np.argsort(power)[::-1]

    print(f"\n===== {label} =====")
    print("Observations:", len(data))
    print("RV standard deviation:", np.std(y))
    print("Top 10 periods:")

    for i in order[:10]:
        print(f"{periods[i]:.5f} days | Power: {power[i]:.6f}")

    for name, reference in [
        ("Pi Men c", 6.267852),
        ("Pi Men d", 124.64),
        ("Pi Men b", 2088.33)
    ]:
        ref_power = ls.power(1/reference)
        nearby = np.abs(periods/reference - 1) <= 0.05

        if nearby.any():
            best = np.argmax(power[nearby])
            nearby_periods = periods[nearby]
            nearby_power = power[nearby]
            best_period = nearby_periods[best]
            best_power = nearby_power[best]
        else:
            best_period = np.nan
            best_power = np.nan

        print(
            f"{name}: reference power={ref_power:.6f}, "
            f"best nearby period={best_period:.5f} d, "
            f"power={best_power:.6f}"
        )

analyse("ORIGINAL DATA", df)

filtered = df[df["drs_snr"] > 0].copy()
analyse("SNR > 0 DATA (DIAGNOSTIC ONLY)", filtered)

print("\n===== COMPARISON COMPLETE =====")
