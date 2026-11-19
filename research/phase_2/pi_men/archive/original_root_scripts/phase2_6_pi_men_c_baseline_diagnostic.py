import numpy as np
import pandas as pd

df = pd.read_csv("phase2_6_pi_men_corrected_dataset.csv")
df = df[
    np.isfinite(df["bjd"]) &
    np.isfinite(df["rv_corrected_ms"]) &
    np.isfinite(df["rv_error_ms"]) &
    (df["rv_error_ms"] > 0) &
    df["instrument_epoch"].isin(["HARPS_PRE", "HARPS_POST"])
].copy()

df = df.sort_values("bjd").reset_index(drop=True)

t = df["bjd"].to_numpy(dtype=float)
t = t - t.min()

y = df["rv_corrected_ms"].to_numpy(dtype=float)
dy = df["rv_error_ms"].to_numpy(dtype=float)
is_pre = df["instrument_epoch"].eq("HARPS_PRE").to_numpy()

P = 2088.33
ECC = 0.6396
OMEGA = np.deg2rad(331.03)

def kepler_anomaly(M, e):
    M = (M + np.pi) % (2*np.pi) - np.pi
    E = M.copy()
    for _ in range(100):
        delta = (E - e*np.sin(E) - M) / (1 - e*np.cos(E))
        E -= delta
        if np.max(np.abs(delta)) < 1e-11:
            break
    return E

def evaluate(params):
    K, M0, gamma_pre, gamma_post, jitter_pre, jitter_post = params

    M = 2*np.pi*t/P + M0
    E = kepler_anomaly(M, ECC)

    nu = 2*np.arctan2(
        np.sqrt(1+ECC)*np.sin(E/2),
        np.sqrt(1-ECC)*np.cos(E/2)
    )

    orbital = K*(np.cos(nu+OMEGA) + ECC*np.cos(OMEGA))
    gamma = np.where(is_pre, gamma_pre, gamma_post)
    prediction = orbital + gamma

    residual = y - prediction
    jitter = np.where(is_pre, jitter_pre, jitter_post)
    variance = dy**2 + jitter**2

    chi2 = np.sum(residual**2 / variance)
    nll = 0.5*np.sum(
        np.log(2*np.pi*variance) + residual**2/variance
    )

    return np.sqrt(np.mean(residual**2)), chi2, nll

known = [
    192.93477528,
    2.6403442442,
    -58.18621233,
    -40.64294510,
    3.17160032,
    2.49151128
]

print("\n===== KNOWN SUCCESSFUL BASELINE PARAMETERS =====")
print("RMS, Chi-square, NLL:", evaluate(known))

print("\n===== DATA CHECK =====")
print("Rows:", len(df))
print("Time baseline:", np.ptp(t))
print("RV median:", np.median(y))
print("RV standard deviation:", np.std(y))
print("Error median:", np.median(dy))
print("PRE rows:", is_pre.sum())
print("POST rows:", (~is_pre).sum())
