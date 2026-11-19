from paths import DATA_DIR, RESULTS_DIR, REPORTS_DIR
import numpy as np
import pandas as pd

from astropy.timeseries import LombScargle
from scipy.signal import find_peaks

FILE = DATA_DIR / "phase2_6_pi_men_harps_timeseries.csv"

KNOWN_PERIODS = {
    "Pi Men c": 6.267852,
    "Pi Men d": 124.64,
    "Pi Men b": 2088.33,
}

print("===== PI MEN LOMB-SCARGLE PERIOD ANALYSIS =====")

try:
    df = pd.read_csv(FILE)

    time = df["bjd"].to_numpy(dtype=float)
    rv = df["rv_relative_ms"].to_numpy(dtype=float)
    error = df["rv_error_ms"].to_numpy(dtype=float)

    valid = (
        np.isfinite(time)
        & np.isfinite(rv)
        & np.isfinite(error)
        & (error > 0)
    )

    time = time[valid]
    rv = rv[valid]
    error = error[valid]

    order = np.argsort(time)
    time = time[order]
    rv = rv[order]
    error = error[order]

    print("Valid observations:", len(time))
    print("Time baseline (days):",
          round(float(time.max() - time.min()), 3))

    print("\nCalculating Lomb-Scargle periodogram...")

    ls = LombScargle(
        time,
        rv,
        dy=error,
        fit_mean=True,
        center_data=True
    )

    frequency, power = ls.autofrequency(
        minimum_frequency=1.0 / 3000.0,
        maximum_frequency=1.0 / 2.0,
        samples_per_peak=10,
        return_freq_limits=False
    ), None

    power = ls.power(frequency)

    periods = 1.0 / frequency

    peaks, _ = find_peaks(power)

    ranked = peaks[np.argsort(power[peaks])[::-1]]

    print("\n===== TOP 15 PERIODIC SIGNALS =====")

    for i, index in enumerate(ranked[:15], 1):
        print(
            f"{i:02d}. Period: {periods[index]:.5f} days"
            f" | Power: {power[index]:.6f}"
        )

    print("\n===== PUBLISHED PERIOD CHECK =====")

    for name, expected in KNOWN_PERIODS.items():

        expected_frequency = 1.0 / expected
        expected_power = float(
            ls.power(expected_frequency)
        )

        nearby = (
            (periods >= expected * 0.95)
            & (periods <= expected * 1.05)
        )

        if nearby.any():
            indices = np.where(nearby)[0]
            best = indices[np.argmax(power[indices])]

            print("\n", name)
            print("Reference period:", expected)
            print("Power at reference:", round(expected_power, 6))
            print("Best nearby period:",
                  round(float(periods[best]), 5))
            print("Nearby peak power:",
                  round(float(power[best]), 6))
        else:
            print(name, "- No nearby frequency found.")

    print("\nNOTE: This is an exploratory raw-RV periodogram.")
    print("No multi-planet subtraction or FAP validation performed.")

except Exception as exc:
    print("ERROR:", type(exc).__name__, str(exc))
