import numpy as np
import pandas as pd

from astropy.timeseries import LombScargle
from scipy.signal import find_peaks

FILE = "phase2_6_pi_men_harps_timeseries.csv"

P_B = 2088.33

print("===== PI MEN B PRE-WHITENING TEST =====")

try:
    df = pd.read_csv(FILE)

    t = df["bjd"].to_numpy(float)
    rv = df["rv_relative_ms"].to_numpy(float)
    err = df["rv_error_ms"].to_numpy(float)

    valid = (
        np.isfinite(t)
        & np.isfinite(rv)
        & np.isfinite(err)
        & (err > 0)
    )

    t, rv, err = t[valid], rv[valid], err[valid]

    order = np.argsort(t)
    t, rv, err = t[order], rv[order], err[order]

    # Fit the published long-period signal.
    ls_b = LombScargle(
        t, rv, dy=err,
        fit_mean=True,
        center_data=True
    )

    model_b = ls_b.model(t, 1.0 / P_B)
    residual = rv - model_b

    print("Observations:", len(t))
    print("Fixed period (days):", P_B)
    print("Original RV standard deviation:",
          round(float(np.std(rv)), 5), "m/s")
    print("Residual standard deviation:",
          round(float(np.std(residual)), 5), "m/s")

    # Search shorter periods in the residuals.
    ls_res = LombScargle(
        t, residual, dy=err,
        fit_mean=True,
        center_data=True
    )

    frequency = ls_res.autofrequency(
        minimum_frequency=1.0 / 300.0,
        maximum_frequency=1.0 / 2.0,
        samples_per_peak=10
    )

    power = ls_res.power(frequency)
    periods = 1.0 / frequency

    peaks, _ = find_peaks(power)
    ranked = peaks[np.argsort(power[peaks])[::-1]]

    print("\n===== TOP 15 RESIDUAL PERIODS =====")

    for i, idx in enumerate(ranked[:15], 1):
        print(
            f"{i:02d}. Period: {periods[idx]:.5f} days"
            f" | Power: {power[idx]:.6f}"
        )

    print("\n===== PUBLISHED SHORT-PERIOD CHECK =====")

    for name, expected in {
        "Pi Men c": 6.267852,
        "Pi Men d": 124.64
    }.items():

        nearby = (
            (periods >= expected * 0.95)
            & (periods <= expected * 1.05)
        )

        print("\n", name)
        print("Reference:", expected)
        print("Power at reference:",
              round(float(ls_res.power(1.0 / expected)), 6))

        if nearby.any():
            indices = np.where(nearby)[0]
            best = indices[np.argmax(power[indices])]

            print("Best nearby period:",
                  round(float(periods[best]), 5))
            print("Nearby peak power:",
                  round(float(power[best]), 6))
        else:
            print("No nearby frequency found.")

    output = "phase2_6_pi_men_b_prewhitened.csv"

    pd.DataFrame({
        "bjd": t,
        "original_rv_relative_ms": rv,
        "b_planet_model_ms": model_b,
        "residual_rv_ms": residual,
        "rv_error_ms": err
    }).to_csv(output, index=False)

    print("\nResidual CSV saved:", output)
    print("\nNOTE: Fixed-period sinusoidal subtraction only.")
    print("Not a full eccentric Keplerian multi-planet fit.")

except Exception as exc:
    print("ERROR:", type(exc).__name__, str(exc))
