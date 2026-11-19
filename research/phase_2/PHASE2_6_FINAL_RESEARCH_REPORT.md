# Phase 2.6 — Radial Velocity Pilot: Final Research Report

**Project:** ExoAnalytica  
**Research Phase:** 2.6 — HARPS Radial Velocity Validation  
**Target:** Pi Mensae (HD 39091)  
**Status:** Completed as a Conditional Validation Pilot  
**Date:** 2026-11-20

---

## 1. Executive Summary

Phase 2.6 investigated the feasibility of using public HARPS radial-velocity observations to establish an RV analysis and validation workflow for ExoAnalytica.

Pi Mensae was selected as the pilot target because it has a published multi-planet system and a long HARPS observational baseline.

The research covered data extraction, quality inspection, instrumental epoch separation, Keplerian modelling, residual analysis, activity-indicator diagnostics, correlated-noise modelling, and parametric bootstrap testing.

The final Gaussian Process (GP) comparison tested a model containing the published-period Pi Mensae c component against a GP noise-only alternative.

The observed likelihood improvement was:

- Observed 2ΔNLL: 43.3419
- Successful bootstrap simulations: 200/200
- Bootstrap exceedances: 0/200
- Empirical bootstrap p-value: 0.004975

This provides strong conditional evidence for an additional fixed-period component under the tested GP noise model.

However, the period was specified in advance using the published Pi Mensae c period. Therefore, this is a known-signal validation pilot, not a blind discovery or independent confirmation.

The next phase must investigate whether ExoAnalytica can identify unknown RV signals without being supplied with their periods.

---

## 2. Research Objectives

The objectives were:

1. Identify a suitable HARPS target for an RV pilot.
2. Retrieve and inspect target-level RV observations.
3. Investigate data-quality issues and suspicious measurements.
4. Evaluate pre- and post-instrument-upgrade observational epochs.
5. Reproduce the dominant published planetary RV signal.
6. Test for an additional known-period RV component.
7. Investigate residual periodicity and stellar activity indicators.
8. Compare independent-noise and correlated-noise models.
9. Evaluate the readiness of the workflow for broader RV benchmarking.

---

## 3. Data Source and Target Selection

### 3.1 Data source

The observations were obtained from the ESO HARPS Radial Velocity Catalogue.

- Catalogue: HARPS RV Catalogue DR1
- ESO TAP table: `safcat.HARPS_RVCAT_V1`
- Catalogue reference: https://www.eso.org/qi/catalog/show/416
- ESO release: https://www.eso.org/cms/eso-archive-news/first-data-release-of-harps-radial-velocity-catalog.html
- DOI: https://doi.org/10.18727/archive/33

The catalogue contains approximately 289,843 RV measurements across 6,488 objects.

### 3.2 Selected target

- Target: Pi Mensae
- Identifier: HD 39091
- SIMBAD identifier: `* pi. Men`
- Original extracted observations: 557
- First observation BJD: 2453001.82961663
- Last observation BJD: 2459185.7148769097
- Observational baseline: 6183.885 days
- Approximate baseline: 16.93 years
- Mean RV uncertainty: 0.442 m/s
- Median RV uncertainty: 0.3383 m/s

The HARPS DRS radial velocities were converted from km/s to m/s where required.

---

## 4. Data Quality Investigation

The initial dataset contained suspicious measurements that required investigation before orbital modelling.

### 4.1 SNR-zero observations

Two observations dated 2019-12-05 had:

- SNR = 0
- Abnormal CCF FWHM values
- Extremely anomalous RV measurements relative to normal observations

These two observations were excluded from the diagnostic working dataset.

### 4.2 Additional rejection window

Seven observations within the 2018-11-27 to 2018-11-28 window were excluded according to the adopted rejection criteria.

The original publication and its exact rejection rationale should remain part of the data-provenance verification.

### 4.3 Final working dataset

| Description | Count |
|---|---:|
| Original observations | 557 |
| Excluded observations | 9 |
| Retained observations | 548 |

The original extracted CSV was preserved. The corrected dataset was generated separately.

### 4.4 Secular acceleration correction

An approximate secular-acceleration correction of 0.48 m/s/year was applied relative to the first retained observation.

This correction remains provisional. Its sign, reference epoch, and exact implementation must be verified against the published treatment before the corrected velocities are considered publication-grade.

---

## 5. Instrument-Epoch Investigation

The observations were divided into two epochs:

- HARPS_PRE: before 2015-06-03
- HARPS_POST: from 2015-06-03 onward

After exclusions:

| Epoch | Observations |
|---|---:|
| HARPS_PRE | 129 |
| HARPS_POST | 419 |
| Total | 548 |

A shared-offset model was compared with a separate PRE/POST offset and jitter model.

### 5.1 Model comparison

| Metric | Shared model | Separate-epoch model |
|---|---:|---:|
| AIC | 3675.274 | 2646.898 |
| BIC | 3692.499 | 2672.736 |

The separate-epoch model was strongly preferred within the tested model comparison.

The fitted POST-minus-PRE offset was approximately +17.54 m/s in the corresponding fit.

This is a phenomenological result. It does not establish the physical cause of the offset. Instrumental calibration, data reduction, and unmodelled effects remain possible contributors.

---

## 6. Pi Mensae b Orbital Baseline

The adopted published orbital parameters were:

| Parameter | Adopted value |
|---|---:|
| Period | 2088.33 days |
| Eccentricity | 0.6396 |
| Argument of periastron | 331.03 degrees |
| Published RV semi-amplitude | approximately 192.99 m/s |

The period, eccentricity, and argument of periastron were held fixed for the baseline validation.

The fitted parameters included RV semi-amplitude, mean anomaly, PRE and POST systemic offsets, and separate epoch jitter values.

### 6.1 Reproduced baseline result

| Parameter | Fitted result |
|---|---:|
| RV semi-amplitude | 192.9348 m/s |
| Mean anomaly | 2.640344 rad |
| PRE offset | -58.1862 m/s |
| POST offset | -40.6429 m/s |
| PRE jitter | 3.1716 m/s |
| POST jitter | 2.4915 m/s |
| Residual RMS | 2.7214 m/s |
| Reduced chi-square | 1.01499 |

The fitted semi-amplitude differs from the adopted published value by approximately -0.0286%.

The baseline result was reproduced in a repeated run.

This demonstrates numerical reproducibility under the adopted fixed orbital parameters. It is not a complete independent orbital re-analysis.

---

## 7. Additional Signal at the Pi Mensae c Period

The published period adopted for Pi Mensae c was:

**P = 6.267852 days**

A weighted sinusoidal component at this fixed period was evaluated against the Pi Mensae b baseline.

### 7.1 Epoch consistency

Using baseline residuals and a common global time reference:

| Epoch | Observations | Fitted amplitude |
|---|---:|---:|
| PRE | 129 | 2.2119 ± 0.4038 m/s |
| POST | 419 | 1.1029 ± 0.1737 m/s |

The signal was present in both epochs under this conditional model.

However, the fitted amplitudes differed. These results do not independently establish the physical nature of the component.

### 7.2 Three-model comparison

The following models were compared:

- Model A: Pi Mensae b only
- Model B: Pi Mensae b plus a shared Pi Mensae c sinusoid
- Model C: Pi Mensae b plus separate PRE and POST sinusoidal coefficients

| Model | AICc | BIC |
|---|---:|---:|
| A | 2647.053 | 2672.736 |
| B | 2587.356 | 2621.539 |
| C | 2578.475 | 2621.128 |

Models B and C were both substantially better than Model A under these criteria.

The BIC difference between Models B and C was approximately 0.41, which does not meaningfully distinguish the two models.

The AICc comparison favoured Model C, but this alone does not prove that the PRE and POST amplitudes are physically different.

---

## 8. Correlated Noise and Activity Indicators

Residual diagnostics showed substantial time-dependent correlation.

Short-time-separation residual pairs exhibited high correlation in both observational epochs.

This indicates that independent Gaussian noise assumptions do not adequately describe all residual behaviour.

BIS, CCF FWHM, and CCF contrast were also investigated.

Some activity-indicator relationships varied between PRE and POST epochs. The available tests did not consistently identify the source of the additional periodic component.

A correlated-noise model was therefore introduced for a more cautious signal comparison.

---

## 9. Gaussian Process Model Comparison

An exponential Ornstein-Uhlenbeck covariance model was fitted separately to PRE and POST observations.

Two models were evaluated:

- GP Model A: Pi Mensae b baseline plus correlated noise
- GP Model B: Pi Mensae b baseline plus a fixed-period 6.267852-day component and correlated noise

The principal Pi Mensae b orbital baseline was held fixed during this conditional comparison.

### 9.1 GP results

| Metric | GP Model A | GP Model B |
|---|---:|---:|
| Negative log likelihood | 1228.4227 | 1206.7517 |
| AIC | 2464.8454 | 2425.5035 |
| BIC | 2482.0705 | 2451.3411 |

The likelihood improvement was:

**2ΔNLL = 43.3419**

The fitted sinusoidal amplitude in Model B was approximately:

**1.1916 m/s**

### 9.2 GP hyperparameters

| Epoch | Model A amplitude | Model A timescale | Model B amplitude | Model B timescale |
|---|---:|---:|---:|---:|
| PRE | 2.4401 m/s | 6.5364 days | 2.1667 m/s | 7.8727 days |
| POST | 1.5921 m/s | 19.1119 days | 1.4627 m/s | 30.5473 days |

All four optimizer starts for each observed model converged to consistent solutions.

The GP comparison favoured the model containing the fixed-period component under the adopted covariance assumptions.

---

## 10. GP Parametric Bootstrap

A parametric bootstrap was performed under GP Model A.

### 10.1 Procedure

- Bootstrap simulations: 200
- Random seed: 20261120
- Null model: fitted GP Model A
- PRE and POST correlated-noise processes simulated independently
- Measurement uncertainties and fixed epoch jitter preserved
- Both Model A and Model B refitted for every simulation
- GP hyperparameters re-optimized during simulated fits

### 10.2 Results

| Metric | Result |
|---|---:|
| Successful simulations | 200 / 200 |
| Failed simulations | 0 |
| Simulations exceeding observed improvement | 0 |
| Observed 2ΔNLL | 43.3419 |
| Bootstrap median | 1.3927 |
| Bootstrap 90th percentile | 4.4365 |
| Bootstrap 95th percentile | 5.1853 |
| Bootstrap 99th percentile | 7.3542 |
| Empirical bootstrap p-value | 0.004975 |

The finite-simulation estimate is:

**p = (0 + 1) / (200 + 1) = 0.004975**

Zero exceedances do not mean that the true probability is zero. The estimate is limited by the number of bootstrap simulations.

### 10.3 Interpretation

The observed likelihood improvement was substantially larger than the improvements generated in the 200 simulations under the fitted GP noise-only null model.

This provides strong conditional evidence for a fixed-period sinusoidal component under the tested model.

It does not establish a definitive planet detection because:

- The 6.267852-day period was specified in advance.
- A blind period search and its trial factors were not included.
- The Pi Mensae b orbital baseline was fixed.
- Uncertainty in the adopted orbital solution was not fully propagated.
- The GP covariance model is only one possible correlated-noise description.
- Stellar activity indicators were not jointly modelled.
- The bootstrap used a finite number of simulations and limited optimizer initialization.

---

## 11. Scientific Limitations

The following limitations must remain attached to the results:

1. The analysis uses one principal target system.
2. The dominant planetary orbital elements were fixed for the principal conditional tests.
3. The additional signal was tested at a published, predetermined period.
4. A blind search across a broad period range was not validated.
5. The approximate secular-acceleration correction requires verification.
6. Instrumental epoch offsets have not been assigned a definitive physical explanation.
7. Stellar activity and correlated noise may not be fully represented by the adopted GP model.
8. The bootstrap does not include period-search trial factors.
9. Generalization to other stars and instruments has not yet been demonstrated.
10. No RV CNN model has been trained or validated in this phase.

The results must not be described as a new independent discovery of Pi Mensae c.

---

## 12. Phase 2.6 Deliverables

Research artifacts generated during this phase include:

- HARPS extraction script and original target time series
- Instrument audit script and output
- Corrected working dataset and preparation report
- PRE/POST Keplerian fit script and results
- Model comparison residuals and periodogram outputs
- Three-model comparison results
- Pi Mensae c incremental and epoch validation outputs
- Parametric bootstrap scripts and reports
- Correlated-noise bootstrap outputs
- Time-correlation and activity-indicator diagnostics
- GP comparison and GP bootstrap outputs

The exact filenames and presence of each artifact should be checked against the local research directory before cleanup or relocation.

---

## 13. Final Assessment

### Phase 2.6 status: COMPLETED AS A PILOT

Phase 2.6 established a reproducible HARPS RV extraction and conditional modelling workflow for Pi Mensae.

The research demonstrated:

- Target-level HARPS data extraction.
- Data-quality diagnostics and explicit exclusions.
- Instrument-epoch separation.
- Reproduction of the dominant published RV semi-amplitude under fixed orbital elements.
- Conditional evaluation of an additional known-period signal.
- Model comparison using correlated-noise Gaussian Processes.
- Parametric bootstrap testing under the adopted GP null model.

The results justify progressing to a broader RV detection and validation benchmark.

They do not yet demonstrate a general-purpose blind exoplanet discovery capability.

---

## 14. Next Phase — Phase 2.7

Phase 2.7 will focus on developing and benchmarking an RV detection methodology without supplying the target planet's period in advance.

Planned work:

1. Build a reproducible RV data preparation and quality-control workflow.
2. Benchmark generalized Lomb-Scargle periodograms.
3. Evaluate periodogram peak significance and false-alarm probability.
4. Investigate alias detection and sampling-window effects.
5. Fit Keplerian models to candidate signals.
6. Evaluate correlated-noise alternatives.
7. Perform injection-and-recovery experiments across different amplitudes, periods, cadences, and noise levels.
8. Test multiple published RV systems.
9. Measure completeness, precision, recall, and false-positive rates.
10. Establish a validated RV benchmark before considering CNN training.

The RV research pipeline should remain separate from the existing Transit production pipeline during this stage.

No existing application UI, API, database, worker, or Transit scientific algorithm should be modified without explicit approval.

---

**End of Phase 2.6 Final Research Report**
