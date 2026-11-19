from paths import DATA_DIR, RESULTS_DIR, REPORTS_DIR
import numpy as np
import pandas as pd

P_C = 6.267852

FILE = RESULTS_DIR / "phase2_6_pi_men_c_incremental_residuals.csv"

df = pd.read_csv(FILE)

required = [
    "bjd",
    "instrument_epoch",
    "c_model_residual_ms",
    "rv_error_ms"
]

df = df.dropna(subset=required).copy()

print("\n===== PI MEN C PRE/POST CONSISTENCY =====")

for epoch in ["HARPS_PRE", "HARPS_POST"]:

    sub = df[df["instrument_epoch"] == epoch].copy()

    t = sub["bjd"].to_numpy(float)
    t = t - t.min()

    y = sub["c_model_residual_ms"].to_numpy(float)
    dy = sub["rv_error_ms"].to_numpy(float)

    angle = 2 * np.pi * t / P_C

    X = np.column_stack([
        np.sin(angle),
        np.cos(angle),
        np.ones(len(t))
    ])

    weights = 1.0 / dy**2

    XtW = X.T * weights
    covariance = np.linalg.inv(XtW @ X)

    beta = covariance @ XtW @ y

    residual = y - X @ beta

    a, b, offset = beta

    amplitude = np.sqrt(a*a + b*b)
    phase = np.arctan2(b, a)

    print(f"\n{epoch}")
    print("Observations:", len(sub))
    print("Baseline days:", round(np.ptp(t), 3))
    print("Sine coefficient:", round(a, 6))
    print("Cosine coefficient:", round(b, 6))
    print("Amplitude:", round(amplitude, 6), "m/s")
    print("Phase:", round(phase, 6), "rad")
    print("Constant offset:", round(offset, 6), "m/s")
    print("Residual RMS:", round(np.sqrt(np.mean(residual**2)), 6))

print("\n===== END =====")
print("Exploratory weighted sinusoidal fits.")
print("These are not independent planet detections.")
