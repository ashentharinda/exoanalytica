# HD115617 (61 Virginis)
# Stage 5 — Final Scientific Assessment v1.0

**Project:** ExoAnalytica
**Research Area:** Radial Velocity (RV) Exoplanet Detection and Validation
**Target:** HD115617 (61 Virginis)
**Instrument / Data Source:** HARPS
**Assessment Version:** 1.0
**Status:** Exploratory scientific assessment completed
**Planet Confirmation Status:** Not confirmed by this investigation

---

## 1. Executive Summary

This report documents the Stage 5 investigation of HARPS radial-velocity observations of HD115617 (61 Virginis).

The investigation evaluated candidate periodic signals, conditional Keplerian model residuals, activity indicators, observing-window effects, injection and recovery performance, false-alarm behaviour, correlated noise, OU innovation diagnostics, night-level effects, and time-dependent instrumental/activity indicators.

The target dataset contains:

- 1,213 HARPS observations.
- 223 observing nights in the earlier observing-night bootstrap analysis.
- 229 UTC calendar observing nights in the subsequent night-level investigations.
- An observational baseline of approximately 4,946.645 days.
- Multiple RV and cross-correlation function (CCF) diagnostic indicators.

Two periodic regions received particular attention:

- Approximately 11.58 days.
- Approximately 16.44 days.

The 11.58-day signal showed relatively stronger local robustness than the 16.44-day signal in several exploratory tests. However, the global false-alarm probability remained above 5% in the block-based null experiments.

The 16.44-day signal showed greater sensitivity to block length and observing-window structure.

A major finding was that the residuals exhibit substantial temporal correlation. An irregular-time Ornstein–Uhlenbeck (OU) noise model was strongly preferred over a diagonal white-noise model in a conditional residual comparison.

Further investigations showed that the OU model reduced short-timescale residual correlation, but some night-to-night and long-term temporal structure remained.

A clear long-term increase in HARPS CCF FWHM was observed. The cause cannot be determined from the available dataset alone. Instrumental evolution, stellar activity, observing conditions, or changes in data selection remain possible explanations.

**Overall conclusion:** Stage 5 identified scientifically interesting periodic structures and significant correlated-noise behaviour. The present evidence is insufficient to classify either investigated periodic signal as a confirmed planetary detection. Independent validation and further scientific modelling are required.

---

## 2. Research Objectives

The primary objectives were:

1. Investigate candidate periodic signals in HD115617 HARPS RV observations.
2. Evaluate conditional Keplerian model performance.
3. Examine residual periodograms after model fitting.
4. Investigate possible relationships between RV residuals and activity indicators.
5. Examine the observing-window structure around candidate periods.
6. Evaluate candidate signal recovery through synthetic injection experiments.
7. Estimate false-alarm behaviour under alternative exploratory null models.
8. Investigate sensitivity to observing-night block length.
9. Quantify correlated residual noise using an irregular-time OU model.
10. Evaluate OU innovation diagnostics and remaining temporal structure.
11. Investigate night-level anomalies and influential observations.
12. Examine long-term changes in instrumental/activity indicators.
13. Establish the limitations and readiness of the current RV analysis for independent benchmarking.

---

## 3. Dataset and Data Integrity

### 3.1 Main dataset

The research dataset was:

`research/phase_2/rv_ai_model/stage_5_keplerian_rv_detection/data/input/harps_rv_observations_18_targets.csv`

Dataset characteristics:

| Property | Value |
|---|---:|
| Total dataset rows | 37,442 |
| Number of targets | 18 |
| HD115617 observations | 1,213 |
| HD115617 observational baseline | 4,946.644917 days |
| HD115617 UTC observing nights | 229 |
| Earlier bootstrap unique observing nights | 223 |

The difference between 223 and 229 reflects the observing-night definitions and source subsets used in the separate analyses. These counts should not be treated as interchangeable without checking the exact grouping procedure.

### 3.2 Relevant raw columns

The investigation used available HARPS fields including:

- `tel_object`
- `date_obs`
- `mjd_obs`
- `drs_bjd`
- `drs_snr`
- `drs_berv`
- `drs_ccf_rvc`
- `drs_ccf_rv`
- `drs_dvrms`
- `drs_bis_rv`
- `drs_ccf_fwhm`
- `drs_ccf_contrast`
- `drs_ccf_noise`
- `drs_bis_span`
- `rv_mps`
- `bjd_day`

### 3.3 Residual matching

The residual dataset was generated from the conditional Keplerian validation experiment.

Exact BJD matching between the raw HD115617 observations and residual diagnostics was achieved:

- Raw observations: 1,213
- Residual observations: 1,213
- Exact BJD matches: 1,213 / 1,213

The later time-dependent investigation retained all matched observations.

No observations were removed as part of the reported anomaly investigations.

---

## 4. Conditional Keplerian Model Investigation

The conditional Keplerian comparison investigated four fixed candidate periods:

| Candidate | Period |
|---|---:|
| P1 | 4.21421445 days |
| P2 | 38.0511147476 days |
| P3 | 123.666123 days |
| P4 | 184.576303 days |

The modelling approach used:

- Eccentric Keplerian components.
- SciPy optimization with L-BFGS-B.
- Three deterministic optimization starts.
- Quadrature combination of measurement uncertainty and fitted jitter.
- A BIS-related coefficient.
- Fixed candidate periods during the comparison.

The optimizer reported successful convergence for the investigated fits.

The `PLUS_BOTH` model produced:

| Metric | Value |
|---|---:|
| Residual RMS | 1.91843 m/s |
| Fitted jitter | 1.80297 m/s |

### Important interpretation

The candidate periods were fixed and selected using the same observational dataset.

Therefore, this comparison is conditional model evaluation, not blind independent detection validation.

The fitted residual RMS is not sufficient evidence that all planetary, stellar, and instrumental signals have been correctly separated.

The model comparison does not establish that all periodic components are planetary in origin.

---

## 5. Residual Periodogram Investigation

After conditional Keplerian modelling, the residual GLS periodogram contained several notable periodic peaks.

The strongest reported residual peaks included:

| Period (days) | GLS Power |
|---:|---:|
| 11.579225 | 0.06751 |
| 11.576515 | 0.06725 |
| 11.581936 | 0.06562 |
| 11.573807 | 0.06490 |
| 11.584649 | 0.06166 |
| 11.571099 | 0.06069 |
| 16.439498 | 0.05996 |
| 11.224518 | 0.05963 |
| 11.227065 | 0.05936 |
| 16.434036 | 0.05876 |

The strongest peak was near 11.58 days.

The two principal candidate regions selected for additional investigation were:

- 11.579225 days.
- 16.439498 days.

These are candidate periodic structures in the conditional residuals. They are not independently confirmed planets.

---

## 6. Activity Indicator Investigation

The residual signals were compared with available HARPS diagnostic indicators.

The investigation considered:

- BIS span.
- CCF FWHM.
- CCF contrast.
- CCF noise.

### 6.1 BIS span

The strongest BIS periodogram feature was approximately 183.47 days, with power around 0.1479.

Power near the candidate regions included:

| Period region | BIS GLS Power |
|---|---:|
| 11.579 days | 0.04751 |
| 16.439 days | 0.05589 |
| 11.224 days | 0.05412 |
| 16.434 days | 0.05202 |

The residual correlation diagnostics were:

- Spearman correlation: -0.3213
- Pearson correlation: +0.0243

The difference between Pearson and Spearman indicates that the relationship is not adequately described by a simple linear association.

### 6.2 CCF FWHM

The strongest FWHM periodogram feature was approximately 394.32 days.

Candidate-region powers were:

| Period region | FWHM GLS Power |
|---|---:|
| 11.579 days | 0.01004 |
| 16.439 days | 0.000634 |
| 11.224 days | 0.00625 |
| 16.434 days | 0.000262 |

Residual correlation diagnostics:

- Spearman: +0.3391
- Pearson: -0.0191

### 6.3 CCF contrast

The strongest contrast periodogram feature was approximately 3.589 days, with power around 0.01645.

Candidate-period powers were comparatively weak.

Residual correlations:

- Spearman: -0.3489
- Pearson: -0.2567

### 6.4 CCF noise

The strongest CCF-noise periodogram feature was approximately 363.3 days, with power around 0.02089.

Candidate-region powers were comparatively weak.

Residual correlations:

- Spearman: +0.053
- Pearson: -0.276

### Interpretation

The activity indicators do not provide a single consistent explanation for the investigated residual peaks.

However, their behaviour demonstrates that activity and CCF-profile diagnostics cannot be ignored.

The absence of a strong matching periodogram peak in an individual indicator does not prove that a candidate RV signal is planetary.

---

## 7. Observing-Window and Alias Investigation

The observing-window periodogram was examined around the principal candidate regions.

Selected window powers were:

| Candidate region | Central | Annual + | Annual - | Daily + |
|---|---:|---:|---:|---:|
| 11.579 days | 0.0023365 | 0.001745 | 0.006298 | 0.00282 |
| 16.439 days | 0.001365 | 0.0051728 | 0.0214823 | 0.0173714 |
| 11.2245 days | 0.002043 | 0.010297 | 0.003093 | 0.003683 |
| 16.434 days | 0.000808 | 0.006448 | 0.021230 | 0.016506 |

### Interpretation

The 16.439-day region shows notable annual and daily sideband window structure.

This raises an alias and sampling-related concern for the 16.44-day candidate.

The central window power near 11.579 days is relatively low. This means the central observing window alone does not strongly explain that peak.

However, low central window power does not eliminate other alias mechanisms, correlated noise, or stellar activity.

The window investigation is diagnostic rather than definitive.

---

## 8. Residual Injection and Recovery Experiment

### 8.1 Experiment configuration

Experiment:

`HD115617_residual_injection_recovery_v1`

The experiment used the `PLUS_BOTH` residual dataset:

- 1,213 observations.
- Exact BJD timestamps.
- Residual RV values.
- Total uncertainty values.
- Lomb–Scargle weighted periodogram analysis.
- Period search range: 2–100 days.
- 12,120 frequency samples.
- Frequency range: 0.01–0.5 cycles/day.

Circular sinusoidal signals were injected at:

- 11.579225 days.
- 16.439498 days.

Injected amplitudes:

- 1 m/s.
- 2 m/s.
- 3 m/s.

Injected phases:

- 0 degrees.
- 90 degrees.
- 180 degrees.
- 270 degrees.

There were 72 total injection trials.

### 8.2 Results

Baseline strongest GLS peak:

- Period: 11.577424 days.

Local recovery results:

| Injection configuration | Local recovery |
|---|---:|
| Both signals, 1 m/s, P11 | 87.5% |
| Both signals, 1 m/s, P16 | 93.75% |
| Both signals, 2 m/s | 100% for both |
| Both signals, 3 m/s | 100% for both |
| P11 only, 1 m/s | 75% |
| P11 only, 2–3 m/s | 100% |
| P16 only, 1 m/s | 100% |
| P16 only, 2–3 m/s | 100% |

Global detection results:

- Both-signal configuration: approximately 50% at the investigated amplitudes.
- Single-signal configuration: approximately 75% at 1 m/s and 100% at 2–3 m/s.

### 8.3 Interpretation and limitations

The local recovery results demonstrate that synthetic periodic signals can be recovered near the investigated periods under the selected experimental conditions.

However:

1. The injected signals were circular sinusoids, not complete eccentric Keplerian models.
2. The experiment was performed on residuals from an already fitted model.
3. The periods were selected using the same observational dataset.
4. Correlated noise and activity may influence recovery.
5. Local recovery does not mean that a signal is the strongest peak globally.
6. Recovery of a synthetic signal does not establish the existence of a real planet.

This experiment is an exploratory detectability assessment, not a planet confirmation test.

---

## 9. False-Alarm and Alias Validation

Experiment:

`HD115617_false_alarm_alias_validation_v1`

The experiment used 500 simulations per null method.

Dataset characteristics:

- Valid residual observations: 1,213
- Unique observing nights in this experiment: 223
- Observed global GLS maximum power: 0.0676520418920242
- Observed global maximum period: 11.578032307677613 days

### 9.1 Nightly block sign-flip null

The experiment used consecutive observing-night groups with random sign flips.

The reported configuration used three-night blocks, with 75 blocks.

Results:

| Statistic | Estimated FAP |
|---|---:|
| Global maximum | 0.0958 |
| P11 local maximum | 0.003992 |
| P16 local maximum | 0.021956 |

### 9.2 Random standardized residual permutation

Results:

| Statistic | Estimated FAP |
|---|---:|
| Global maximum | 0.001996 |
| P11 local maximum | 0.001996 |
| P16 local maximum | 0.001996 |

No simulated permutation maximum exceeded the observed statistic in the 500 simulations.

The finite Monte Carlo resolution is approximately:

1 / 501 = 0.001996

### 9.3 Interpretation

The P11 local statistic is unusual relative to the selected three-night sign-flip null.

However, the global FAP is approximately 9.58%, which is above the conventional 5% threshold.

Therefore, the global residual peak is not statistically significant at the 5% level under this particular null experiment.

The P16 local statistic is less compelling than P11 under the same comparison.

The random permutation null destroys temporal dependence. Its very small estimated FAP should not be interpreted as reliable evidence against correlated-noise explanations.

These tests are conditional on the `PLUS_BOTH` residuals and on candidate periods selected from the same dataset.

They do not provide blind independent validation.

---

## 10. Block-Length Sensitivity Investigation

Experiment:

`HD115617_block_length_sensitivity_v1`

The analysis evaluated consecutive non-overlapping observing-night groups of:

- 1 night.
- 3 nights.
- 5 nights.
- 10 nights.

Each configuration used 500 simulations.

### 10.1 Global false-alarm estimates

| Block length | Global FAP |
|---|---:|
| 1 night | 0.107784 |
| 3 nights | 0.129741 |
| 5 nights | 0.163673 |
| 10 nights | 0.175649 |

### 10.2 P11 local false-alarm estimates

| Block length | P11 local FAP |
|---|---:|
| 1 night | 0.003992 |
| 3 nights | 0.011976 |
| 5 nights | 0.025948 |
| 10 nights | 0.017964 |

### 10.3 P16 local false-alarm estimates

| Block length | P16 local FAP |
|---|---:|
| 1 night | 0.005988 |
| 3 nights | 0.017964 |
| 5 nights | 0.075848 |
| 10 nights | 0.143713 |

### 10.4 Interpretation

The P11 local statistic remains comparatively unusual across the investigated block lengths.

Nevertheless, global FAP remains approximately 10.8–17.6%.

The P16 local FAP increases substantially as the block length increases, indicating sensitivity to the assumed temporal grouping.

This is a robustness concern for the 16.44-day candidate.

### Methodological limitation

This procedure is not a conventional moving-block bootstrap.

It assigns random positive or negative signs to consecutive non-overlapping observing-night groups and assumes approximate sign symmetry.

It is an exploratory sensitivity experiment and should not be described as a fully validated correlated-noise bootstrap.

The 500 simulations also provide limited Monte Carlo resolution.

---

## 11. Correlated Noise Validation

Experiment:

`HD115617_correlated_noise_validation_v1`

The residuals were evaluated under:

1. A diagonal white Gaussian noise model.
2. An irregular-time OU / continuous-time AR(1) correlated-noise model.

The OU likelihood was evaluated using an exact irregular-time Kalman approach.

### 11.1 White-noise baseline

| Metric | Value |
|---|---:|
| Log likelihood | -2456.99492027 |
| Mean | 0.00000231 m/s |
| AIC | 4915.989841 |
| BIC | 4921.090692 |

### 11.2 OU correlated-noise model

| Metric | Value |
|---|---:|
| Optimizer success | True |
| Log likelihood | -2293.15665780 |
| Mean | 0.19434709 m/s |
| Correlated amplitude | 1.43423075 m/s |
| Timescale | 3.93278319 days |
| AIC | 4592.313316 |
| BIC | 4607.615871 |

### 11.3 Model comparison

Delta BIC:

OU BIC - White BIC = -313.474821

This is a very strong preference for the OU model within this conditional residual comparison.

### 11.4 Dense exponential GP cross-check

A dense exponential-kernel Gaussian Process calculation was performed at the OU optimum.

Results:

- GP log likelihood: -2293.15665780
- Absolute OU versus GP log-likelihood difference: approximately 4.55e-13

The agreement is at numerical precision.

The dense GP and OU model use mathematically equivalent exponential covariance structures. Therefore, this is an implementation cross-check, not an independent competing noise hypothesis.

### 11.5 Interpretation

The residuals contain substantial temporal correlation that is not adequately represented by the diagonal white-noise model.

This is a major scientific result.

However, the comparison is conditional on the previously fitted Keplerian residuals. The Keplerian parameters were not jointly re-fitted with the OU process in this experiment.

The result does not identify the physical cause of the correlated noise.

Possible contributors include stellar variability, instrumental behaviour, observing conditions, and model misspecification.

A strong OU preference does not prove that a candidate signal is false, nor does it establish that any remaining signal is planetary.

---

## 12. OU Innovation Diagnostics

The OU innovation diagnostics were evaluated using 1,213 observations.

### 12.1 Standardized innovation summary

| Metric | Value |
|---|---:|
| Count | 1,213 |
| Mean | -0.0101143 |
| Standard deviation | 0.7165145 |
| Minimum | -3.04865 |
| Maximum | +3.88679 |
| Observation-order lag-1 correlation | +0.16608 |
| Observation-order lag-2 correlation | +0.17872 |

Observation-order lags do not correspond to fixed elapsed times because the observations are irregularly sampled.

### 12.2 Exact time-lag pairwise correlations

| Time separation | Pair count | Pearson |
|---|---:|---:|
| 0–1 days | 5,580 | +0.06562 |
| 1–3 days | 4,874 | -0.00567 |
| 3–7 days | 5,361 | -0.01871 |
| 7–14 days | 4,212 | +0.02317 |
| 14–30 days | 8,194 | +0.02222 |
| 30–60 days | 17,863 | +0.01907 |
| 60–120 days | 27,536 | +0.00707 |
| 120–365 days | 93,801 | +0.02096 |

### 12.3 Adjacent UTC-night behaviour

The nightly analysis found:

- 229 UTC nights.
- Median BJD gap between adjacent nights: 3.0386619 days.
- Mean innovation per night: -0.0086094 m/s.
- Standard deviation of nightly mean innovations: 0.57544 m/s.
- Adjacent-night mean innovation Pearson correlation: +0.231031.
- Adjacent-night mean innovation Spearman correlation: +0.094078.

### 12.4 Interpretation

The OU model substantially reduces short-lag residual correlation.

For example, the original residual correlation at 0–1 days was approximately +0.3293, while the standardized OU innovation correlation was approximately +0.06562.

However, weak short-lag correlation and adjacent-night structure remain.

The standardized innovation standard deviation of approximately 0.7165 is below the idealized value of 1 expected under perfectly calibrated predictive uncertainties.

This may indicate conservative predictive uncertainties, model calibration issues, or implementation details that require further examination.

It should not be interpreted as proof that the OU model has completely explained the residual structure.

---

## 13. Night-Level Correlated Noise Investigation

Experiment:

`HD115617_night_level_correlated_noise_v1`

The investigation aggregated OU innovations and activity indicators by UTC observing night.

### 13.1 Observing-night structure

| Metric | Value |
|---|---:|
| Observations | 1,213 |
| UTC nights | 229 |
| Median observations per night | 5 |
| Maximum observations per night | 48 |

### 13.2 Within-night and adjacent-night relationships

Within-night standardized innovation pairwise correlations:

- Pearson: +0.0968702
- Spearman: +0.0859682
- Pair count: 4,746

Adjacent UTC-night mean innovation correlations:

- Pearson: +0.2310310
- Spearman: +0.0940783
- Pair count: 228

Adjacent median innovation correlations:

- Pearson: +0.1862936
- Spearman: +0.0647428

### 13.3 Activity associations

Selected nightly associations:

| Association | Pearson | Spearman |
|---|---:|---:|
| BIS mean vs mean innovation | +0.419238 | -0.102526 |
| BIS median vs median innovation | +0.380641 | -0.125213 |
| FWHM mean vs mean innovation | -0.190932 | +0.294220 |
| FWHM median vs median innovation | -0.213641 | +0.268040 |

The large differences between Pearson and Spearman indicate sensitivity to distribution shape, extreme observations, or non-linear relationships.

### 13.4 Block-length descriptive sensitivity

| Group length | Pearson | Spearman |
|---|---:|---:|
| 1 night | +0.2310 | +0.0941 |
| 3 nights | +0.2442 | +0.2792 |
| 5 nights | +0.5251 | +0.5088 |
| 10 nights | +0.5766 | +0.3935 |

These are descriptive group-level results. Larger blocks contain fewer groups, so they should not be interpreted as independent statistical evidence.

### Interpretation

The OU model reduces short-timescale correlation, but night-to-night structure remains.

The BIS and FWHM relationships are not stable enough to justify a simple linear correction based on the current evidence.

No observations were removed and no model was refitted in this investigation.

---

## 14. Night-Level Influence and Robustness Audit

Experiment:

`HD115617_night_level_influence_robustness_v1`

The analysis examined robust outlier flags and leave-one-night-out influence.

### 14.1 Full-sample associations

| Association | Pearson | Spearman | Theil-Sen slope |
|---|---:|---:|---:|
| BIS mean vs mean innovation | +0.419238 | -0.102526 | -45.508535 |
| BIS median vs median innovation | +0.380641 | -0.125213 | -61.632208 |
| FWHM mean vs mean innovation | -0.190932 | +0.294220 | +12.792191 |
| FWHM median vs median innovation | -0.213641 | +0.268040 | +13.935831 |

### 14.2 Extreme-night flags

A robust MAD z-score threshold greater than 3.5 was used to flag unusual nights across selected nightly metrics.

The audit reported 16 flagged entries. Some dates can appear more than once because multiple flag types can be associated with the same night.

The flags are descriptive indicators of unusual values.

They do not automatically identify bad measurements.

### 14.3 Influential nights

For BIS mean association, influential nights included:

- 2017-08-08
- 2009-08-11
- 2017-02-26
- 2013-06-09

The largest reported Pearson change from removing one night was approximately -0.07545 for 2017-08-08.

For FWHM mean association, 2013-06-09 was particularly influential.

Removing that night changed the Pearson association by approximately +0.37123, reversing the sign from -0.19093 to approximately +0.18030.

The corresponding Spearman change was much smaller.

### Interpretation

The BIS Pearson association is not robustly supported by its rank correlation or Theil-Sen slope.

The FWHM Pearson association is highly sensitive to a single influential night.

These results demonstrate that simple correlation coefficients can be misleading when the data contain influential observations.

No observations were removed.

---

## 15. Time-Dependent Instrumental and Activity Investigation

Experiment:

`HD115617_time_dependent_instrumental_activity_v1`

The analysis examined long-term trends, chronological bins, unusual nights, and raw observation diagnostics.

### 15.1 Long-term trends

The analysis used 229 UTC observing nights.

| Metric | Pearson | Spearman | Theil-Sen slope per year |
|---|---:|---:|---:|
| Mean FWHM | +0.160124 | +0.848379 | +0.003218 |
| Median FWHM | +0.147961 | +0.852033 | +0.003214 |
| Mean BIS span | +0.219643 | -0.139582 | -0.000053 |
| Median BIS span | +0.225627 | -0.123175 | -0.000045 |
| Mean raw OU innovation | +0.323393 | +0.403843 | +0.139577 m/s |
| Median raw OU innovation | +0.306868 | +0.365955 | +0.138803 m/s |
| Mean standardized innovation | +0.433764 | +0.398423 | +0.064966 |

### 15.2 FWHM trend

The FWHM time trend is particularly notable.

Spearman correlations are approximately +0.85 for both mean and median FWHM.

This indicates a strong monotonic long-term increase in the nightly FWHM measurements.

The available CSV does not include sufficient instrument configuration, calibration-event, or maintenance metadata to identify the cause.

Potential explanations include:

- Instrumental evolution.
- Changes in instrumental configuration.
- Calibration or reduction changes.
- Stellar activity or line-profile changes.
- Observing-condition differences.
- Changes in observation selection.

These possibilities remain hypotheses.

### 15.3 Innovation trend

Both raw OU innovations and standardized innovations show positive long-term trends.

This suggests that the OU innovations retain time-dependent structure.

The trend does not establish a physical cause.

It may reflect an unmodelled systematic component, long-term stellar variability, instrumental behaviour, or another source of model misspecification.

### 15.4 Chronological bins

The observations were divided into five chronological groups.

| Bin | Nights | Observations | Median FWHM | Mean FWHM | Median raw innovation (m/s) | Mean raw innovation (m/s) |
|---|---:|---:|---:|---:|---:|---:|
| T1 | 18 | 111 | 6.840225 | 6.840203 | -0.716446 | -0.803623 |
| T2 | 66 | 417 | 6.847426 | 6.847082 | -0.143461 | -0.299489 |
| T3 | 60 | 320 | 6.855056 | 6.853649 | -0.061419 | -0.407253 |
| T4 | 73 | 279 | 6.862449 | 6.852379 | +0.140603 | +0.232961 |
| T5 | 12 | 86 | 6.870630 | 6.869742 | +1.152959 | +2.142758 |

The fifth bin contains only 12 nights and is therefore less robust than the larger middle bins.

The median SNR also changes between chronological groups. This may indicate changes in observing selection or data quality and should be investigated before attributing the trends to a single cause.

### 15.5 Unusual-night raw observation inspection

Selected nights were inspected using their original HARPS rows.

#### 2009-08-11

- Observation count: 1
- SNR: 5.3
- FWHM: 6.858082
- BIS: -0.051706
- CCF contrast: 51.0951
- CCF noise: 0.0212606
- RV: -7784.6198 m/s
- Residual: -20.5232 m/s
- Raw OU innovation: -19.9592 m/s
- Standardized innovation: -2.8418

This observation has a very low SNR and represents a strong data-quality concern.

It should be reviewed against the original archive and reduction metadata before any exclusion decision.

#### 2013-06-09

- Observation count: 1
- SNR: 601.05
- FWHM: 6.408824
- BIS: -0.044488
- CCF contrast: 44.4317
- CCF noise: 0.00011538
- RV: -7752.6951 m/s
- Residual: +6.3573 m/s
- Raw OU innovation: +6.1583 m/s
- Standardized innovation: +2.6699

This observation has very high SNR but an unusually low FWHM compared with the surrounding long-term distribution.

It is a significant CCF-profile anomaly and was highly influential in the previous FWHM correlation analysis.

High SNR alone does not guarantee that the CCF profile is normal.

#### 2013-06-15

Two observations were recorded.

The FWHM values were approximately 6.71827 and 6.73924.

The residuals were positive, approximately +2.98 and +2.23 m/s.

This provides additional context for the FWHM behaviour following the 2013-06-09 anomaly.

#### 2016-03-17

Five observations were recorded.

FWHM values were approximately 6.8777–6.8799.

Residuals were consistently positive, approximately +6.48 to +8.18 m/s.

The raw OU innovations were also positive.

This indicates within-night consistency in the residual direction, but does not identify the cause.

#### 2017-08-08

Three observations were recorded.

FWHM values were approximately 6.8803–6.8809.

Residuals were approximately +8.18 to +9.52 m/s.

The raw OU innovations were positive.

This is another night showing repeated positive residual behaviour.

### 15.6 Overall time-dependent interpretation

The time-dependent investigation identified two major descriptive features:

1. A strong long-term increase in FWHM.
2. A positive long-term trend in OU innovations.

The two features occur in the same observational timeline, but the available analysis does not establish causation.

Instrumental and stellar explanations remain unresolved.

No observations were removed and no Keplerian model was refitted during this investigation.

---

## 16. Scientific Limitations

The following limitations are important when interpreting this report.

### 16.1 Candidate selection

The candidate periods were identified using the same dataset used in the subsequent investigations.

This introduces selection effects and prevents the results from being treated as blind independent validation.

### 16.2 Conditional residual analysis

Several tests were performed on residuals from the existing `PLUS_BOTH` Keplerian model.

The Keplerian parameters were not jointly refitted with every alternative noise model.

Therefore, conclusions apply to the conditional residual analysis rather than a complete joint planetary and noise inference.

### 16.3 Correlated noise

The OU model substantially improves the conditional likelihood relative to white noise.

However, a single OU process may not describe all physical sources of variability.

More flexible and physically motivated noise models should be evaluated.

### 16.4 Activity diagnostics

BIS, FWHM, contrast, and CCF noise show complex relationships with residuals.

The correlations are sensitive to the statistic used and, in some cases, to individual nights.

A simple linear correction is not justified by the current results.

### 16.5 Instrument metadata

The supplied dataset does not contain enough instrument configuration, calibration, maintenance, or reduction-history metadata to determine the cause of the long-term FWHM trend.

### 16.6 Statistical limitations

The null experiments used 500 simulations per configuration.

This gives limited Monte Carlo resolution.

The nightly sign-flip method is exploratory and is not a conventional moving-block bootstrap.

The random permutation null destroys temporal dependence and is not a reliable representation of correlated noise.

### 16.7 Injection assumptions

The injection experiment used circular sinusoidal signals.

It did not perform a complete eccentric Keplerian injection-and-recovery analysis with simultaneous refitting of all model parameters.

### 16.8 Planet confirmation

None of the investigations in this report independently confirms the planetary nature of the candidate residual signals.

No claim of a new planet discovery should be made from these results alone.

---

## 17. Overall Scientific Assessment

### 17.1 11.58-day candidate

Evidence supporting further investigation:

- Strong residual GLS peak near 11.58 days.
- Comparatively low local FAP in several block-length experiments.
- High local recovery in the synthetic injection experiment.
- Low central observing-window power relative to the 16.44-day candidate.

Concerns:

- Global FAP remains above 5%.
- The residuals contain substantial correlated noise.
- Activity and long-term instrumental behaviour remain unresolved.
- The candidate period was selected using the same dataset.

**Assessment:** Scientifically interesting candidate periodicity requiring further independent validation. Not confirmed as a planet.

### 17.2 16.44-day candidate

Evidence supporting further investigation:

- Detectable local residual periodogram structure.
- Synthetic signals can be recovered in the selected injection experiment.

Concerns:

- Strong annual and daily sideband window structure.
- Local FAP is sensitive to block length.
- Correlated noise remains significant.
- Candidate selection was performed on the same dataset.

**Assessment:** More substantial alias and robustness concerns than the 11.58-day candidate. Not confirmed as a planet.

### 17.3 Correlated noise

The OU model provides a major improvement over the diagonal white-noise model in the conditional residual comparison.

However, the remaining innovation trends and night-level structure show that the noise model requires additional evaluation.

**Assessment:** Correlated noise is a central feature of this dataset and must be addressed before reliable candidate significance claims.

### 17.4 Long-term FWHM evolution

The strong monotonic FWHM trend is a notable observational feature.

The current metadata cannot establish whether this is instrumental, stellar, or related to observational selection.

**Assessment:** A high-priority issue for independent instrumental and activity investigation.

---

## 18. Recommended Stage 6 Work

The next research stage should focus on independent benchmarking and validation.

Recommended activities:

1. Obtain independent published RV information for HD115617 and compare the candidate periods against established literature.
2. Verify the exact target identity and the provenance of the HARPS observations.
3. Investigate instrument configuration, calibration, and reduction-history metadata.
4. Evaluate the long-term FWHM trend using independent diagnostic data where available.
5. Review the 2009-08-11 and 2013-06-09 observations against original archive products.
6. Investigate alternative correlated-noise models and their predictive performance.
7. Perform joint Keplerian and correlated-noise inference rather than relying only on conditional residuals.
8. Use simulation designs that preserve realistic irregular sampling and temporal correlation.
9. Conduct injection and recovery with eccentric Keplerian signals and full model refitting.
10. Apply independent target-level validation and avoid using the same observations for candidate selection and final significance estimation.
11. Compare results with independent RV instruments or published measurements where available.
12. Document all model assumptions, software versions, data provenance, and random seeds.

No AI training should begin using unvalidated candidate labels from this analysis.

The results should first pass independent scientific quality control.

---

## 19. ExoAnalytica Research Readiness

The Stage 5 investigation provides useful scientific and engineering foundations for the RV component of ExoAnalytica.

Completed investigation capabilities include:

- HARPS target data preparation.
- Conditional Keplerian modelling.
- Residual periodogram analysis.
- Activity-indicator diagnostics.
- Observing-window and alias investigation.
- Synthetic residual injection and recovery.
- Exploratory false-alarm analysis.
- Block-length sensitivity analysis.
- Irregular-time OU correlated-noise modelling.
- Dense exponential GP implementation cross-check.
- OU innovation diagnostics.
- Night-level aggregation and influence analysis.
- Time-dependent instrumental/activity investigation.
- Raw observation inspection for selected anomalies.

These capabilities represent research progress, not a validated automated planet-discovery system.

The RV AI dataset should not treat the investigated residual peaks as confirmed planetary labels.

Before AI training, the project requires:

- Independent target-level labels.
- Verified positive and negative examples.
- Data provenance and quality-control metadata.
- Target-level train/validation/test separation.
- Selection-bias and class-imbalance assessment.
- Injection-and-recovery-based detectability characterization.
- Uncertainty calibration.
- Independent benchmark evaluation.

---

## 20. Final Conclusion

The Stage 5 investigation of HD115617 demonstrates that the HARPS RV residuals contain interesting periodic structures and substantial correlated-noise behaviour.

The approximately 11.58-day candidate is comparatively more robust than the approximately 16.44-day candidate in several exploratory local tests. Nevertheless, the global false-alarm results do not establish a statistically significant global detection at the conventional 5% level under the tested block-based null models.

The 16.44-day candidate has additional observing-window and block-length sensitivity concerns.

The OU correlated-noise analysis reveals that a white-noise assumption is inadequate for the conditional residuals. Further temporal structure remains after OU modelling.

The long-term FWHM trend is a significant unresolved diagnostic feature. Its physical origin cannot be determined from the available observations and metadata alone.

Consequently:

**Neither the 11.58-day nor the 16.44-day residual signal is confirmed as a planet by this investigation.**

The appropriate scientific outcome is to preserve both as candidates for further independent investigation, with greater caution applied to the 16.44-day signal.

Stage 5 is considered complete as an exploratory investigation and diagnostic assessment. Independent benchmarking and stronger joint modelling are required before making a planet-detection claim or using these signals as confirmed AI training labels.

---

## 21. Reproducibility and Experiment References

The following experiment directories contain the associated scripts, outputs, and diagnostic records.

| Investigation | Experiment directory |
|---|---|
| Conditional Keplerian validation | `experiments/HD115617_keplerian_validation_v1` |
| Residual injection and recovery | `experiments/HD115617_residual_injection_recovery_v1` |
| False-alarm and alias validation | `experiments/HD115617_false_alarm_alias_validation_v1` |
| Block-length sensitivity | `experiments/HD115617_block_length_sensitivity_v1` |
| Correlated-noise validation | `experiments/HD115617_correlated_noise_validation_v1` |
| Night-level correlated noise | `experiments/HD115617_night_level_correlated_noise_v1` |
| Night-level influence and robustness | `experiments/HD115617_night_level_influence_robustness_v1` |
| Time-dependent instrumental/activity | `experiments/HD115617_time_dependent_instrumental_activity_v1` |

### Computational environment

Reported analysis environment:

- Python 3.11.9
- NumPy 1.26.4
- SciPy 1.13.1
- Pandas 2.2.3
- Astropy 6.1.4

The correlated-noise implementation used SciPy-based methods because `celerite2` and `george` were not installed in the reported environment.

Exact package versions and experiment metadata should be preserved with the individual experiment outputs.

---

## 22. Research Status

**Stage:** Phase 2 — RV Research
**Stage 5:** Keplerian RV Detection and Validation
**Assessment:** Exploratory investigation completed
**Scientific conclusion:** Candidate signals remain unconfirmed
**Next stage:** Stage 6 — Independent Benchmarking
**AI training readiness:** Not yet approved

---

*End of Stage 5 Final Scientific Assessment v1.0*