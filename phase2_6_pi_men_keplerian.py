import numpy as np
import pandas as pd

from scipy.optimize import differential_evolution, least_squares
from astropy.timeseries import LombScargle
from scipy.signal import find_peaks

FILE = "phase2_6_pi_men_harps_timeseries.csv"

def kepler_rv(params, t):
    P, K, e, omega, M0, gamma = params

    M = 2.0 * np.pi * (t - t[0]) / P + M0
    M = (M + np.pi) % (2.0 * np.pi) - np.pi

    E = M.copy()

    for _ in range(100):
        delta = (
            E - e * np.sin(E) - M
        ) / (1.0 - e * np.cos(E))

        E -= delta

        if np.max(np.abs(delta)) < 1e-11:
            break

    nu = 2.0 * np.arctan2(
        np.sqrt(1 + e) * np.sin(E / 2),
        np.sqrt(1 - e) * np.cos(E / 2)
    )

    return gamma + K * (
        np.cos(nu + omega) + e * np.cos(omega)
    )

print("===== PI MEN B KEPLERIAN FIT =====")

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

    # Center time to improve numerical stability.
    t = t - t[0]

    bounds = [
        (1500, 2600),
        (50, 300),
        (0.0, 0.85),
        (-np.pi, np.pi),
        (-np.pi, np.pi),
        (-100, 100)
    ]

    def objective(params):
        model = kepler_rv(params, t)
        residual = (rv - model) / err
        return np.sum(residual ** 2)

    print("Optimizing eccentric Keplerian orbit...")
    print("Period search range: 1500-2600 days")

    result = differential_evolution(
        objective,
        bounds,
        seed=42,
        maxiter=250,
        popsize=10,
        tol=1e-7,
        polish=True,
        workers=1
    )

    fitted = result.x

    # Local refinement
    refined = least_squares(
        lambda p: (
            rv - kepler_rv(p, t)
        ) / err,
        fitted,
        bounds=(
            [b[0] for b in bounds],
            [b[1] for b in bounds]
        ),
        max_nfev=5000
    )

    fitted = refined.x

    model = kepler_rv(fitted, t)
    residual = rv - model

    print("\n===== FITTED PARAMETERS =====")
    names = ["Period (days)", "K (m/s)", "Eccentricity",
             "Omega (rad)", "M0 (rad)", "Gamma (m/s)"]

    for name, value in zip(names, fitted):
        print(f"{name}: {value:.8f}")

    print("\nChi-square:", round(objective(fitted), 4))
    print("Residual RMS (m/s):",
          round(float(np.std(residual)), 5))

    # Residual periodogram
    ls = LombScargle(
        t, residual, dy=err,
        fit_mean=True,
        center_data=True
    )

    frequency = ls.autofrequency(
        minimum_frequency=1 / 300,
        maximum_frequency=1 / 2,
        samples_per_peak=10
    )

    power = ls.power(frequency)
    periods = 1 / frequency

    peaks, _ = find_peaks(power)
    ranked = peaks[np.argsort(power[peaks])[::-1]]

    print("\n===== TOP 15 KEPLERIAN RESIDUAL PERIODS =====")

    for i, idx in enumerate(ranked[:15], 1):
        print(
            f"{i:02d}. Period: {periods[idx]:.5f}"
            f" days | Power: {power[idx]:.6f}"
        )

    for name, expected in {
        "Pi Men c": 6.267852,
        "Pi Men d": 124.64
    }.items():
        print(
            f"{name} power at reference period:",
            round(float(ls.power(1 / expected)), 6)
        )

    pd.DataFrame({
        "time_days_from_start": t,
        "original_rv_relative_ms": rv,
        "keplerian_b_model_ms": model,
        "residual_rv_ms": residual,
        "rv_error_ms": err
    }).to_csv(
        "phase2_6_pi_men_keplerian_residuals.csv",
        index=False
    )

    print("\nResidual CSV saved.")

except Exception as exc:
    print("ERROR:", type(exc).__name__, str(exc))
