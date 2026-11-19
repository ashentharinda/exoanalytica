from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution

INPUT = Path("phase2_6_pi_men_corrected_dataset.csv")
OUTPUT_CSV = Path("phase2_6_pi_men_three_model_comparison.csv")
OUTPUT_REPORT = Path("phase2_6_pi_men_three_model_comparison.txt")

P_B = 2088.33
ECC = 0.6396
OMEGA = np.deg2rad(331.03)
P_C = 6.267852

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

# Common global time reference for every model and epoch.
t = df["bjd"].to_numpy(dtype=float).copy()
t -= t.min()

y = df["rv_corrected_ms"].to_numpy(dtype=float)
dy = df["rv_error_ms"].to_numpy(dtype=float)

is_pre = df["instrument_epoch"].eq("HARPS_PRE").to_numpy()
is_post = ~is_pre

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
    K, M0, gamma_pre, gamma_post = params[:4]

    M = 2*np.pi*t/P_B + M0
    E = kepler_anomaly(M, ECC)

    nu = 2*np.arctan2(
        np.sqrt(1+ECC)*np.sin(E/2),
        np.sqrt(1-ECC)*np.cos(E/2)
    )

    orbital = K * (
        np.cos(nu + OMEGA) + ECC*np.cos(OMEGA)
    )

    gamma = np.where(is_pre, gamma_pre, gamma_post)

    return orbital + gamma

def predict(params, model):
    result = baseline_model(params)

    angle = 2*np.pi*t/P_C
    sine = np.sin(angle)
    cosine = np.cos(angle)

    if model == "A":
        return result

    if model == "B":
        a, b = params[6:8]
        result += a*sine + b*cosine
        return result

    if model == "C":
        a_pre, b_pre, a_post, b_post = params[6:10]

        result[is_pre] += (
            a_pre*sine[is_pre] +
            b_pre*cosine[is_pre]
        )

        result[is_post] += (
            a_post*sine[is_post] +
            b_post*cosine[is_post]
        )

        return result

    raise ValueError(f"Unknown model: {model}")

def objective(params, model):
    prediction = predict(params, model)

    jitter_pre = params[4]
    jitter_post = params[5]

    jitter = np.where(is_pre, jitter_pre, jitter_post)
    variance = dy**2 + jitter**2

    residual = y - prediction

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

bounds = {
    "A": base_bounds,
    "B": base_bounds + [
        (-20, 20), (-20, 20)
    ],
    "C": base_bounds + [
        (-20, 20), (-20, 20),
        (-20, 20), (-20, 20)
    ]
}

def fit_model(model):
    print(f"\n===== FITTING MODEL {model} =====", flush=True)

    result = differential_evolution(
        objective,
        bounds[model],
        args=(model,),
        seed=42,
        maxiter=900,
        popsize=15,
        tol=1e-8,
        polish=True,
        workers=1,
        updating="immediate"
    )

    prediction = predict(result.x, model)
    residual = y - prediction

    jitter = np.where(
        is_pre,
        result.x[4],
        result.x[5]
    )

    variance = dy**2 + jitter**2
    chi_square = np.sum(residual**2/variance)

    k = len(result.x)
    nll = float(result.fun)

    aic = 2*k + 2*nll
    aicc = aic + (2*k*(k+1))/(N-k-1)
    bic = 2*nll + k*np.log(N)

    return {
        "result": result,
        "prediction": prediction,
        "residual": residual,
        "chi2": chi_square,
        "reduced_chi2": chi_square/(N-k),
        "rms": np.sqrt(np.mean(residual**2)),
        "nll": nll,
        "k": k,
        "aic": aic,
        "aicc": aicc,
        "bic": bic
    }

models = {}

for name in ["A", "B", "C"]:
    models[name] = fit_model(name)

# Build a comparison table.
rows = []

for name, fit in models.items():
    rows.append({
        "model": name,
        "parameters": fit["k"],
        "success": fit["result"].success,
        "nll": fit["nll"],
        "chi2": fit["chi2"],
        "reduced_chi2": fit["reduced_chi2"],
        "rms_ms": fit["rms"],
        "AIC": fit["aic"],
        "AICc": fit["aicc"],
        "BIC": fit["bic"],
        "delta_AICc": 0.0,
        "delta_BIC": 0.0
    })

best_aicc = min(r["AICc"] for r in rows)
best_bic = min(r["BIC"] for r in rows)

for r in rows:
    r["delta_AICc"] = r["AICc"] - best_aicc
    r["delta_BIC"] = r["BIC"] - best_bic

comparison = pd.DataFrame(rows)
comparison.to_csv(OUTPUT_CSV, index=False)

# Report.
lines = [
    "PI MEN - THREE MODEL JOINT COMPARISON",
    "="*72,
    f"Input: {INPUT}",
    f"Observations: {N}",
    f"HARPS_PRE: {int(is_pre.sum())}",
    f"HARPS_POST: {int(is_post.sum())}",
    f"Fixed b period: {P_B} days",
    f"Fixed b eccentricity: {ECC}",
    f"Fixed b omega: {np.rad2deg(OMEGA)} degrees",
    f"Fixed c period: {P_C} days",
    "Common global time reference used.",
    "Same Gaussian likelihood and observations for all models.",
    "",
    "MODEL DEFINITIONS:",
    "A: b Keplerian only.",
    "B: b Keplerian + shared c sine/cosine coefficients.",
    "C: b Keplerian + separate PRE and POST c coefficients.",
    "",
    "MODEL COMPARISON:",
    comparison.to_string(index=False),
    ""
]

for name, fit in models.items():
    p = fit["result"].x

    lines += [
        "-"*72,
        f"MODEL {name}",
        f"Optimizer success: {fit['result'].success}",
        f"Optimizer message: {fit['result'].message}",
        f"NLL: {fit['nll']:.8f}",
        f"Chi-square: {fit['chi2']:.8f}",
        f"Reduced chi-square: {fit['reduced_chi2']:.8f}",
        f"RMS: {fit['rms']:.8f} m/s",
        f"K_b: {p[0]:.8f} m/s",
        f"M0_b: {p[1]:.8f} rad",
        f"Gamma PRE: {p[2]:.8f} m/s",
        f"Gamma POST: {p[3]:.8f} m/s",
        f"Jitter PRE: {p[4]:.8f} m/s",
        f"Jitter POST: {p[5]:.8f} m/s",
        f"AICc: {fit['aicc']:.8f}",
        f"BIC: {fit['bic']:.8f}",
    ]

    if name == "B":
        a, b = p[6:8]
        amplitude = np.hypot(a, b)
        phase = np.arctan2(b, a)

        lines += [
            f"Shared c sine coefficient: {a:.8f}",
            f"Shared c cosine coefficient: {b:.8f}",
            f"Shared c amplitude: {amplitude:.8f} m/s",
            f"Shared c global phase: {phase:.8f} rad",
        ]

    if name == "C":
        a_pre, b_pre, a_post, b_post = p[6:10]

        amp_pre = np.hypot(a_pre, b_pre)
        amp_post = np.hypot(a_post, b_post)

        phase_pre = np.arctan2(b_pre, a_pre)
        phase_post = np.arctan2(b_post, a_post)

        lines += [
            f"PRE c sine: {a_pre:.8f}",
            f"PRE c cosine: {b_pre:.8f}",
            f"PRE c amplitude: {amp_pre:.8f} m/s",
            f"PRE c global phase: {phase_pre:.8f} rad",
            f"POST c sine: {a_post:.8f}",
            f"POST c cosine: {b_post:.8f}",
            f"POST c amplitude: {amp_post:.8f} m/s",
            f"POST c global phase: {phase_post:.8f} rad",
        ]

    lines.append("")

# Save per-observation predictions and residuals.
output = df.copy()
output["time_relative_days"] = t

for name, fit in models.items():
    output[f"model_{name}_prediction_ms"] = fit["prediction"]
    output[f"model_{name}_residual_ms"] = fit["residual"]

output.to_csv(
    "phase2_6_pi_men_three_model_residuals.csv",
    index=False
)

lines += [
    "="*72,
    "SCIENTIFIC CAVEATS:",
    "- b period, eccentricity and omega are fixed, not refitted.",
    "- The PRE/POST gamma and jitter parameters are independently fitted.",
    "- Model C has two additional c parameters compared with Model B.",
    "- AICc/BIC compare these specified models, not planet existence.",
    "- Optimizer success and parameter bounds must be inspected.",
    "- Correlated noise, activity and orbital-parameter uncertainty",
    "  are not fully represented.",
    "- This comparison alone cannot confirm an independent planet."
]

OUTPUT_REPORT.write_text("\n".join(lines), encoding="utf-8")

print("\n".join(lines))
print(f"\nComparison CSV: {OUTPUT_CSV.resolve()}")
print(f"Residual CSV: {Path('phase2_6_pi_men_three_model_residuals.csv').resolve()}")
print(f"Report saved: {OUTPUT_REPORT.resolve()}")
