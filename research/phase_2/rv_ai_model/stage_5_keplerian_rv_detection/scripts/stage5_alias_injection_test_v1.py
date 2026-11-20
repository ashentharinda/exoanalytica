from pathlib import Path
import numpy as np
import pandas as pd
from astropy.timeseries import LombScargle

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/input/harps_rv_observations_18_targets.csv"
GLS_FILE = ROOT / "experiments/HD115617_gls_v1/periodogram.csv"
OUT = ROOT / "experiments/HD115617_alias_injection_v1"

P0 = 38.05111474761596
CANDIDATES = {
    "central_38.051d": P0,
    "observed_34.423d": 34.423416264370736,
    "observed_42.533d": 42.53349025958792,
}

def main():
    if not RAW.exists() or not GLS_FILE.exists():
        raise FileNotFoundError("Required Stage 5 input is missing.")
    if OUT.exists():
        raise FileExistsError(f"Refusing to overwrite {OUT}")

    raw = pd.read_csv(RAW)
    gls = pd.read_csv(GLS_FILE)

    d = raw[raw["tel_object"].astype(str) == "HD115617"].copy()
    for col in ["drs_bjd", "drs_dvrms"]:
        d[col] = pd.to_numeric(d[col], errors="coerce")

    d = d.dropna(subset=["drs_bjd", "drs_dvrms"])
    d = d[(d["drs_dvrms"] > 0)].sort_values("drs_bjd")

    t = d["drs_bjd"].to_numpy(float)
    dy = d["drs_dvrms"].to_numpy(float)

    frequency_col = "frequency" if "frequency" in gls.columns else None
    if frequency_col is None:
        possible = [c for c in gls.columns if "freq" in c.lower()]
        if not possible:
            raise ValueError(f"Frequency column not found: {list(gls.columns)}")
        frequency_col = possible[0]

    frequencies = pd.to_numeric(
        gls[frequency_col], errors="coerce"
    ).dropna().to_numpy(float)
    frequencies = np.unique(frequencies[frequencies > 0])

    t0 = t.min()
    results = []

    # Test two phases to avoid relying on one arbitrary phase.
    for phase_deg in [0, 90]:
        phase = np.deg2rad(phase_deg)
        synthetic_rv = np.sin(
            2 * np.pi * (t - t0) / P0 + phase
        )

        model = LombScargle(
            t, synthetic_rv, dy=dy,
            fit_mean=True, center_data=True, nterms=1
        )
        power = model.power(
            frequencies, method="fast", normalization="standard"
        )

        for label, period in CANDIDATES.items():
            f = 1.0 / period
            idx = int(np.argmin(np.abs(frequencies - f)))
            results.append({
                "phase_degrees": phase_deg,
                "signal": label,
                "requested_period_days": period,
                "nearest_grid_period_days": 1.0 / frequencies[idx],
                "frequency_grid_offset": frequencies[idx] - f,
                "synthetic_gls_power": float(power[idx]),
            })

        # Save the complete synthetic periodogram for this phase.
        phase_df = pd.DataFrame({
            "frequency_per_day": frequencies,
            "period_days": 1.0 / frequencies,
            "synthetic_gls_power": power,
        })
        OUT.mkdir(parents=True, exist_ok=True)
        phase_df.to_csv(
            OUT / f"synthetic_periodogram_phase_{phase_deg}.csv",
            index=False
        )

    result_df = pd.DataFrame(results)
    result_df.to_csv(OUT / "alias_injection_summary.csv", index=False)

    print("\n===== SYNTHETIC ALIAS INJECTION TEST =====")
    print(f"Target: HD115617")
    print(f"Original timestamps: {len(t)}")
    print(f"Injected period: {P0:.8f} days")
    print(f"GLS frequency samples: {len(frequencies)}")
    print("\n===== RESULTS =====")
    print(result_df.to_string(
        index=False, float_format=lambda x: f"{x:.10g}"
    ))
    print(f"\nOutput: {OUT}")
    print("Synthetic test only; original RV data was not modified.")

if __name__ == "__main__":
    main()
