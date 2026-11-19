from paths import DATA_DIR, RESULTS_DIR, REPORTS_DIR
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution

INPUT = DATA_DIR / "phase2_6_pi_men_corrected_dataset.csv"

OUTPUT_CSV = RESULTS_DIR / "phase2_6_pi_men_c_incremental_residuals.csv"
OUTPUT_REPORT = REPORTS_DIR / "phase2_6_pi_men_c_incremental_report.txt"

P_B = 2088.33
ECC = 0.6396
OMEGA = np.deg2rad(331.03)

P_C = 6.267852
K_PUBLISHED = 192.99

df = pd.read_csv(INPUT)

required = [
    "bjd", "rv_corrected_ms",
    "rv_error_ms", "instrument_epoch"
]

missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns: {missing}")

df = df[
    np.isfinite(df["bjd"]) &
    np.isfinite(df["rv_corrected_ms"]) &
    np.isfinite(df["rv_error_ms"]) &
    (df["rv_error_ms"] > 0) &
    df["instrument_epoch"].isin(["HARPS_PRE", "HARPS_POST"])
].copy()

df = df.sort_values("bjd").reset_index(drop=True)

t = df["bjd"].to_numpy(dtype=float)
t -= t.min()

y = df["rv_corrected_ms"].to_numpy(dtype=float)
dy = df["rv_error_ms"].to_numpy(dtype=float)

is_pre = df["instrument_epoch"].eq("HARPS_PRE").to_numpy()

N = len(df)

def kepler_anomaly(M, e):
    M = (M + np.pi) % (2*np.pi) - np.pi
    E = M.copy()

    for _ in range(100):
        delta = (E - e*np.sin(E) - M) / (1 - e*np.cos(E))
        E -= delta

        if np.max(np.abs(delta)) < 1e-11:
            break

    return E

def baseline_model(params):
    K, M0, gamma_pre, gamma_post, jitter_pre, jitter_post = params

    M = 2*np.pi*t/P_B + M0
    E = kepler_anomaly(M, ECC)

    nu = 2*np.arctan2(
        np.sqrt(1+ECC)*np.sin(E/2),
        np.sqrt(1-ECC)*np.cos(E/2)
    )

    orbital = K*(np.cos(nu+OMEGA) + ECC*np.cos(OMEGA))

    gamma = np.where(is_pre, gamma_pre, gamma_post)

    return orbital + gamma

def calculate_model(params, include_c=False):
    base_params = params[:6]
    prediction = baseline_model(base_params)

    if include_c:
        a_c, b_c = params[6:8]

        angle = 2*np.pi*t/P_C

        prediction += (
            a_c*np.sin(angle) +
            b_c*np.cos(angle)
        )

    return prediction

def objective(params, include_c=False):
    if include_c:
        jitter_pre, jitter_post = params[4], params[5]
    else:
        jitter_pre, jitter_post = params[4], params[5]

    prediction = calculate_model(params, include_c)

    residual = y - prediction

    jitter = np.where(is_pre, jitter_pre, jitter_post)
    variance = dy**2 + jitter**2

    return 0.5*np.sum(
        np.log(2*np.pi*variance) +
        residual**2/variance
    )

base_bounds = [
    (1, 300),
    (-np.pi, np.pi),
    (-500, 500),
    (-500, 500),
    (0.1, 100),
    (0.1, 100)
]

c_bounds = base_bounds + [
    (-20, 20),
    (-20, 20)
]

def fit_model(include_c):
    bounds = c_bounds if include_c else base_bounds

    result = differential_evolution(
        objective,
        bounds,
        args=(include_c,),
        seed=42,
        maxiter=900,
        popsize=15,
        tol=1e-8,
        polish=True,
        workers=1
    )

    prediction = calculate_model(result.x, include_c)
    residual = y - prediction

    jitter = np.where(
        is_pre,
        result.x[4],
        result.x[5]
    )

    variance = dy**2 + jitter**2

    chi2 = np.sum(residual**2 / variance)

    k = len(result.x)

    nll = float(result.fun)
    aic = 2*k + 2*nll
    aicc = aic + (2*k*(k+1))/(N-k-1)
    bic = 2*nll + k*np.log(N)

    return {
        "result": result,
        "prediction": prediction,
        "residual": residual,
        "chi2": chi2,
        "reduced_chi2": chi2/(N-k),
        "rms": np.sqrt(np.mean(residual**2)),
        "nll": nll,
        "k": k,
        "aic": aic,
        "aicc": aicc,
        "bic": bic
    }

print("\n===== PI MEN C INCREMENTAL VALIDATION =====")
print("Observations:", N)
print("HARPS PRE:", int(is_pre.sum()))
print("HARPS POST:", int((~is_pre).sum()))
print("Published b period:", P_B)
print("Published c period:", P_C)

print("\nFitting Model A: baseline b only...")
model_a = fit_model(False)

print("Fitting Model B: baseline b + c sinusoid...")
model_b = fit_model(True)

results = [
    ("BASE_B_ONLY", model_a),
    ("BASE_B_PLUS_C", model_b)
]

print("\n===== MODEL COMPARISON =====")

for name, fit in results:
    print(f"\n{name}")
    print("Optimizer success:", fit["result"].success)
    print("Optimizer message:", fit["result"].message)
    print(f"NLL: {fit['nll']:.6f}")
    print(f"Chi-square: {fit['chi2']:.6f}")
    print(f"Reduced chi-square: {fit['reduced_chi2']:.6f}")
    print(f"Residual RMS: {fit['rms']:.6f} m/s")
    print(f"AICc: {fit['aicc']:.6f}")
    print(f"BIC: {fit['bic']:.6f}")

delta_aicc = model_b["aicc"] - model_a["aicc"]
delta_bic = model_b["bic"] - model_a["bic"]

a_c, b_c = model_b["result"].x[6:8]

amplitude_c = np.sqrt(a_c**2 + b_c**2)
phase_c = np.arctan2(b_c, a_c)

print("\n===== C SIGNAL PARAMETERS =====")
print(f"Sine coefficient: {a_c:.6f} m/s")
print(f"Cosine coefficient: {b_c:.6f} m/s")
print(f"Fitted semi-amplitude: {amplitude_c:.6f} m/s")
print(f"Phase parameter: {phase_c:.6f} rad")

print("\n===== MODEL SELECTION =====")
print(f"Delta AICc (B - A): {delta_aicc:.6f}")
print(f"Delta BIC (B - A): {delta_bic:.6f}")

print("\n===== BASELINE PARAMETER RECOVERY =====")
print("Model A K:", model_a["result"].x[0])
print("Model B K:", model_b["result"].x[0])
print("Published K:", K_PUBLISHED)

df["baseline_residual_ms"] = model_a["residual"]
df["c_model_residual_ms"] = model_b["residual"]
df["baseline_prediction_ms"] = model_a["prediction"]
df["c_model_prediction_ms"] = model_b["prediction"]

df.to_csv(OUTPUT_CSV, index=False)

report = [
    "PI MEN C INCREMENTAL VALIDATION",
    "="*65,
    f"Observations: {N}",
    f"HARPS PRE: {int(is_pre.sum())}",
    f"HARPS POST: {int((~is_pre).sum())}",
    "",
    "MODEL A: B ONLY",
    f"Optimizer success: {model_a['result'].success}",
    f"Optimizer message: {model_a['result'].message}",
    f"K b: {model_a['result'].x[0]:.8f}",
    f"NLL: {model_a['nll']:.8f}",
    f"Chi-square: {model_a['chi2']:.8f}",
    f"Reduced chi-square: {model_a['reduced_chi2']:.8f}",
    f"RMS: {model_a['rms']:.8f}",
    f"AICc: {model_a['aicc']:.8f}",
    f"BIC: {model_a['bic']:.8f}",
    "",
    "MODEL B: B + C",
    f"Optimizer success: {model_b['result'].success}",
    f"Optimizer message: {model_b['result'].message}",
    f"K b: {model_b['result'].x[0]:.8f}",
    f"NLL: {model_b['nll']:.8f}",
    f"Chi-square: {model_b['chi2']:.8f}",
    f"Reduced chi-square: {model_b['reduced_chi2']:.8f}",
    f"RMS: {model_b['rms']:.8f}",
    f"AICc: {model_b['aicc']:.8f}",
    f"BIC: {model_b['bic']:.8f}",
    "",
    "C SIGNAL",
    f"Sine coefficient: {a_c:.8f}",
    f"Cosine coefficient: {b_c:.8f}",
    f"Amplitude: {amplitude_c:.8f}",
    f"Phase: {phase_c:.8f}",
    "",
    f"Delta AICc (B-A): {delta_aicc:.8f}",
    f"Delta BIC (B-A): {delta_bic:.8f}",
    "",
    "Exploratory fixed-period sinusoidal comparison.",
    "Not a confirmed independent planet detection.",
    "No false-alarm probability or amplitude uncertainty calculated.",
    "Both models use the same observations and Gaussian jitter likelihood."
]

OUTPUT_REPORT.write_text("\n".join(report), encoding="utf-8")

print("\nCSV saved:", OUTPUT_CSV.resolve())
print("Report saved:", OUTPUT_REPORT.resolve())
print("\n===== C INCREMENTAL TEST COMPLETE =====")
