# ExoAnalytica
# Phase 1 – Final Validation Report

**Validation Date:** 19 November 2026  
**Project:** ExoAnalytica  
**Branch:** main  
**Primary Validation Target:** Kepler-63 (KIC 11554435)  
**Validation Scope:** Regression, cache integrity, transit detection, injection recovery, masking and depth preservation.

---

## 1. Executive Summary

Phase 1 validation was conducted to evaluate the reliability of the existing ExoAnalytica transit-analysis pipeline.

The validation covered:

- Regression and preprocessing checks.
- FITS cache integrity and recovery.
- Baseline BLS period detection.
- Injection recovery at multiple transit depths.
- Period accuracy.
- Existing planetary signal interference.
- Transit masking validation.
- Injected signal preservation.
- Transit depth preservation after detrending.

The tests demonstrate that the pipeline can recover strong transit signals in the selected Kepler-63 dataset. However, recovery performance decreases for weaker injected signals, and measurable depth attenuation occurs during detrending.

**Overall conclusion:** Phase 1 validation activities are complete. The findings do not yet justify changing the scientific algorithms. Further investigation across multiple targets is recommended before modifying detection or detrending parameters.

---

## 2. Phase 1.2 – Regression Validation

**Status: Completed**

Regression validation was conducted following preprocessing-related work.

The validation included:

- Reviewing preprocessing changes.
- Running regression checks.
- Checking the existing analysis workflow.
- Confirming that the project remained operational.

A backup of the preprocessing implementation was maintained during the validation work.

No additional scientific algorithm changes are authorized by this report.

---

## 3. Phase 1.3 – Cache Integrity Validation

**Status: Completed**

Cache validation examined the local Lightkurve/Mission FITS cache and recovery behavior.

The validation included:

- FITS cache inspection.
- Detection of invalid or incomplete FITS data.
- Quarantine of a corrupted FITS file.
- Recovery and re-download verification.
- FITS integrity checks after recovery.
- Cache report generation.

The diagnostic recovery test successfully restored a usable FITS file and confirmed that the recovered file could be validated.

The cache validation report was generated separately as:

`phase1_3_cache_report.txt`

---

## 4. Phase 1.4 – Scientific Validation

**Status: Tests A–H Completed**

### 4.1 Target Dataset

Primary target:

- Target: Kepler-63
- KIC ID: 11554435
- FITS files: 4
- Prepared observations: 10,297
- Observation baseline: approximately 228.96 days

### 4.2 Test A – Injection Recovery

Twenty-four injection trials were performed across four injected transit depths.

| Injected depth | Recovered | Recovery rate |
|---|---:|---:|
| 500 ppm | 0/6 | 0% |
| 1,000 ppm | 0/6 | 0% |
| 2,000 ppm | 3/6 | 50% |
| 4,000 ppm | 6/6 | 100% |
| **Total** | **9/24** | **37.5%** |

The results show stronger recovery performance at higher injected transit depths.

### 4.3 Test B – Period Accuracy

Period accuracy was evaluated using the same 24 injection trials.

| Injected depth | Period accuracy passes |
|---|---:|
| 500 ppm | 0/6 |
| 1,000 ppm | 0/6 |
| 2,000 ppm | 3/6 |
| 4,000 ppm | 6/6 |
| **Total** | **9/24** |

The median period errors were:

- 500 ppm: 140.381%
- 1,000 ppm: 341.236%
- 2,000 ppm: 7.072%
- 4,000 ppm: 0.016%

The dominant existing Kepler-63 b signal appears to influence period selection, particularly for weaker injected signals.

### 4.4 Test C – Baseline BLS Validation

The baseline BLS search returned:

- Detected period: 9.4312678112 days
- Reference Kepler-63 b period: 9.4341505 days
- Relative difference: 0.03056%

The detected period closely matches the reference planetary period.

This confirms that the dominant Kepler-63 b signal is detectable in the selected dataset.

### 4.5 Test D – Existing Planet Signal Interference

The existing Kepler-63 b transit windows were masked before repeating injection recovery.

| Depth | Original recovery | Masked recovery |
|---|---:|---:|
| 500 ppm | 0/6 | 0/6 |
| 1,000 ppm | 0/6 | 5/6 |
| 2,000 ppm | 3/6 | 6/6 |
| 4,000 ppm | 6/6 | 6/6 |
| **Total** | **9/24** | **17/24** |

The masked experiment showed improved recovery, particularly at 1,000 and 2,000 ppm.

This indicates that an existing dominant signal can interfere with recovery of additional injected signals in this dataset.

### 4.6 Test E – Masking Validation

Three random seeds were evaluated, producing 48 trials per masking condition.

| Mask factor | Recovery | Recovery rate | Removed points |
|---|---:|---:|---:|
| 1.0x | 29/48 | 60.4% | 314 |
| 1.5x | 29/48 | 60.4% | 314 |
| 2.0x | 34/48 | 70.8% | 423 |

Depth-specific results:

| Depth | 1.0x | 1.5x | 2.0x |
|---|---:|---:|---:|
| 500 ppm | 0/12 | 0/12 | 0/12 |
| 1,000 ppm | 5/12 | 5/12 | 10/12 |
| 2,000 ppm | 12/12 | 12/12 | 12/12 |
| 4,000 ppm | 12/12 | 12/12 | 12/12 |

The 2.0x mask improved recovery in this experiment but removed more observations.

These results are insufficient to establish a universally optimal masking factor.

### 4.7 Test F – Injected Signal Preservation Diagnostic

The experiment evaluated the fraction of injected transit observations retained after masking.

| Mask factor | Point coverage | Retained points | Removed points |
|---|---:|---:|---:|
| 1.0x | 98.75% | 24,795 | 314 |
| 1.5x | 98.75% | 24,795 | 314 |
| 2.0x | 98.32% | 24,686 | 423 |

Across all conditions:

- Total injected transit points: 75,327
- Retained injected transit points: 74,276
- Removed injected transit points: 1,051
- Overall point coverage: 98.61%

Point coverage alone does not establish that the original transit depth is preserved.

### 4.8 Test G – Signal Depth Preservation

Forty-eight injections were evaluated under four conditions.

| Condition | Matched signals | Median depth ratio | Median depth bias |
|---|---:|---:|---:|
| Original | 15 | 0.6782 | -32.18% |
| Mask 1.0x | 29 | 0.6065 | -39.35% |
| Mask 1.5x | 29 | 0.6065 | -39.35% |
| Mask 2.0x | 34 | 0.5854 | -41.46% |

Additional observations:

- No 500 ppm signals were recovered.
- The 1,000 ppm recovery improved under masking.
- The 2,000 ppm and 4,000 ppm signals showed higher recovery rates.
- Only 2 of 34 matched signals under the 2.0x condition were within 20% depth error.

The experiment demonstrates that improved detection counts do not necessarily imply accurate transit-depth recovery.

### 4.9 Test H – Direct Transit Depth Validation

The initial Test H implementation was invalid because the original transit mask was applied to shorter detrended arrays.

The test was corrected by aligning baseline and injected detrended outputs using their common timestamps.

Results:

| Measurement | Result |
|---|---:|
| Input injected depth | 2,000 ppm |
| Raw median injected depth | 2,000 ppm |
| Baseline detrended points | 9,853 |
| Injected detrended points | 8,477 |
| Common timestamps | 8,477 |
| Common transit points | 620 |
| Detrended median depth | 1,579.5 ppm |
| Depth preservation ratio | 0.7897 |
| Depth bias | -21.03% |
| Outside-transit median difference | 0 ppm |

**Interpretation:**

The raw injected signal preserved the intended 2,000 ppm depth.

After detrending, the median measured depth was approximately 1,579.5 ppm, corresponding to a 21.03% negative depth bias.

This demonstrates measurable depth attenuation for this particular target and injection configuration.

The result does not establish that all targets or transit depths experience the same attenuation.

---

## 5. Overall Scientific Findings

The Phase 1 validation produced the following findings:

1. The baseline BLS search successfully identified the dominant Kepler-63 b signal.
2. Stronger injected signals were recovered more reliably than weaker signals.
3. Existing planetary signals can interfere with the recovery of additional signals.
4. Masking improved recovery in the selected experiment.
5. Increasing the masking factor removed more observations.
6. Higher recovery counts did not guarantee accurate recovered transit depths.
7. Direct detrending validation demonstrated measurable depth attenuation.
8. Further multi-target validation is necessary before selecting new scientific parameters.

---

## 6. Known Limitations

The following limitations must be considered:

- Most Phase 1.4 experiments used one primary target: Kepler-63.
- Injection results depend on the selected injection configuration and random seeds.
- Weak injected signals were not reliably recovered in these experiments.
- Transit depth attenuation requires further investigation.
- Point coverage is not equivalent to photometric depth preservation.
- A single target cannot establish general pipeline performance across Kepler or TESS datasets.
- This validation does not establish independent confirmation of newly discovered exoplanets.

---

## 7. Recommended Next Steps

The recommended priorities after Phase 1 are:

1. Preserve the current validated implementation.
2. Investigate depth attenuation without immediately modifying the production algorithm.
3. Validate the findings using additional targets with different transit depths and signal characteristics.
4. Compare detected signals against authoritative mission catalogues.
5. Evaluate the pipeline's false-positive behavior.
6. Expand scientific validation before approving algorithm changes.

Future extensions involving Radial Velocity and Gravitational Microlensing require their own data pipelines and independent validation.

---

## 8. Final Phase 1 Assessment

**Phase 1 validation activities: COMPLETED**

**Scientific findings: DOCUMENTED**

**Algorithm modification: NOT APPROVED BY THIS VALIDATION**

**Next milestone: Phase 1 Final Review and Phase 2 Planning**

Phase 1 establishes a documented validation baseline for the existing ExoAnalytica transit-analysis pipeline.

The results identify both successful detection behavior and areas requiring further scientific investigation.

No claim of universal detection accuracy or confirmed exoplanet discovery performance is made based solely on these experiments.

---

**End of Report**

Project: ExoAnalytica  
Validation date: 19 November 2026
