# Stage 6 â€” Independent Benchmarking
## Scientific Progress and Data Provenance Report

**Status:** In Progress
**Report type:** Interim scientific assessment
**Project:** ExoAnalytica
**Stage:** 6 â€” Independent Benchmarking

---

## 1. Executive Summary

The Stage 6 investigation has established strong archive-level provenance
and numerical consistency for the 18-target HARPS radial-velocity dataset.

A total of 37,442 observations were cross-matched against the ESO
HARPS RV catalogue (`safcat.HARPS_RVCAT_V1`).

All 37,442 local observations matched archive records using target
identifier and observation timestamp. No unmatched or duplicate
observation keys were detected.

The investigation also retrieved archive-level identifiers and
instrument metadata for every matched observation.

However, archive provenance verification does not establish independent
planet-detection validation. Publication overlap, reference-data
independence, and benchmark suitability remain under investigation.

No planet confirmation claims are made in this report.

---

## 2. HARPS Dataset Overview

Dataset:

`research/phase_2/rv_ai_model/data/interim/harps_rv_observations_18_targets.csv`

| Property | Result |
|---|---:|
| Total observations | 37,442 |
| Unique target stars | 18 |
| First observation | 2003-09-19 |
| Last observation | 2023-02-10 |
| Archive table | safcat.HARPS_RVCAT_V1 |
| Archive | ESO HARPS RV Catalogue |

### 2.1 Target Observation Counts

| Target | Observations |
|---|---:|
| HD10700 | 9,420 |
| HD039060 | 7,532 |
| HD20794 | 7,042 |
| HD160691 | 2,450 |
| HD17051 | 1,900 |
| HD192310 | 1,835 |
| HD19994 | 1,736 |
| HD115617 | 1,213 |
| HD136352 | 685 |
| HD69830 | 682 |
| HD39091 | 557 |
| HD40307 | 478 |
| HD215152 | 375 |
| HD96700 | 366 |
| HD10180 | 336 |
| HD134606 | 290 |
| HD39194 | 277 |
| HD31527 | 268 |

---

## 3. ESO Archive Provenance Verification

The ESO archive query returned exactly 37,442 observations for the
18 selected targets.

Matching used:

- `tel_object`
- `date_obs`

### 3.1 Observation Matching

| Check | Result |
|---|---:|
| Local observations | 37,442 |
| Archive observations | 37,442 |
| Matched unique observations | 37,442 |
| Local unmatched observations | 0 |
| Archive unmatched observations | 0 |
| Duplicate local keys | 0 |
| Duplicate archive keys | 0 |

**Observation matching result: 100%.**

### 3.2 Archive Metadata Availability

The following fields were populated for all 37,442 matched archive records:

| Field | Populated |
|---|---:|
| `adp_dpid` | 37,442 |
| `raw_dpid` | 37,442 |
| `progid` | 37,442 |
| `ins_mode` | 37,442 |

Each observation had a unique `adp_dpid` and `raw_dpid`.

There were 53 unique observing programme identifiers.

### 3.3 Instrument Mode Distribution

| Instrument mode | Observations |
|---|---:|
| HAM | 37,295 |
| EGGS | 147 |
| **Total** | **37,442** |

The dataset contains observations from two instrument modes.
Future statistical modelling and machine-learning work must account
for possible instrument-mode effects.

---

## 4. Scientific Value Consistency

Archive values were compared against the local dataset.

All 37,442 observations were matched for each numerical field.

| Field | Exact matches | Maximum absolute difference |
|---|---:|---:|
| `drs_bjd` | 36,390 | 4.656612873077393e-10 |
| `drs_ccf_rvc` | 36,068 | 4.547473508864641e-13 |
| `drs_dvrms` | 29,590 | 8.881784197001252e-16 |

The maximum numerical differences are extremely small and consistent
with floating-point representation differences.

These comparisons support numerical consistency between the local
observations and the ESO archive records.

---

## 5. NASA Exoplanet Archive Publication Metadata

A publication-level metadata query returned:

| Property | Result |
|---|---:|
| Publication-level records | 159 |
| Unique planet names | 56 |
| Unique host stars | 18 |
| Unique discovery-reference strings | 22 |

The publication metadata includes:

- `default_flag`
- `disc_refname`
- `disc_pubdate`
- `disc_year`
- `disc_facility`
- `disc_telescope`
- `disc_instrument`
- Planet orbital period and mass-related fields

All 159 records had populated discovery reference names and the
inspected publication metadata fields.

The `default_flag` distribution was:

- 56 records with `default_flag = 1`
- 103 records with `default_flag = 0`

Discovery references should be resolved to their ADS bibliographic
identifiers and publication records during the next provenance review.

Discovery references alone do not establish that the benchmark is
independent of the HARPS observations used by this project.

---

## 6. Planet Mass Reference Consistency

For 55 records, both `pl_msinie` and `pl_msinij` were available.

All 55 records agreed within a 2% tolerance after accounting for
the relevant mass units.

One exception was identified:

**bet Pic c**

The inspected NASA metadata record did not provide valid
`pl_msinie` and `pl_msinij` values. Generic mass fields were available.

The generic mass field must not automatically be treated as an
RV minimum-mass reference without checking its provenance.

For RV reference comparisons, `pl_msinie` is the preferred field
when available, with `pl_msinij` used as a unit-consistency check.

---

## 7. Controversial Planet Records

The previous catalogue audit identified five records flagged as
controversial:

- HD40307 g
- tau Cet f
- tau Cet g
- tau Cet h
- HD20794 e

These records must not be treated as confirmed positive training
labels without additional scientific review.

A controversial catalogue entry is not a reliable negative label either.
Such records should remain separately flagged until their status and
publication history have been reviewed.

---

## 8. Benchmark Independence Limitations

The current 18-target dataset is a known planet-host reference dataset.

It is not a balanced sample of confirmed planets and non-planet systems.

Important limitations:

1. NASA catalogue matching is not independent validation.
2. Some discovery publications may have used the same HARPS observations.
3. Publication-level provenance must be resolved and compared with
   the observation-level dataset.
4. The dataset does not currently provide a verified negative-control
   sample.
5. Controversial planet records require separate treatment.
6. HAM and EGGS observations may introduce instrument-mode effects.
7. Target-level data splitting is required to avoid stellar leakage
   in future machine-learning experiments.

Consequently, the current dataset must not yet be described as an
independent benchmark or used to claim general detection accuracy.

---

## 8.1 HD10180 â€” Observation-Level Publication Overlap Pilot

An observation-level comparison was performed between the 190 valid
BJD/RV rows in the published Lovis et al. (2011) HD 10180 radial-velocity
table and the 336 HD10180 observations in the local HARPS dataset.

Published BJD values were compared with the nearest local ESO HARPS
catalogue BJD. A match was accepted when the absolute BJD difference
was no greater than 2 seconds. The published table reports BJD to six
decimal places, so this tolerance accommodates its timestamp precision.

| Check | Result |
|---|---:|
| Valid published observations | 190 |
| Local HD10180 observations | 336 |
| Published observations matched | 156 |
| Published observations not matched within 2 seconds | 34 |
| Match fraction | 82.1% |
| Median absolute BJD difference | 0.0216 seconds |
| Maximum absolute BJD difference | 1.3686 seconds |
| Matched local observations (unique) | 156 |

All 156 matched RV values agreed within 1 m/s between the published
table and the local ESO catalogue values. The local-minus-published
RV difference had a mean of approximately -0.0034 m/s and a standard
deviation of approximately 0.0713 m/s.

The matched observations were associated with these ESO observing
programmes:

| ESO programme ID | Matched observations |
|---|---:|
| 072.C-0488(E) | 100 |
| 183.C-0972(A) | 56 |
| **Total** | **156** |

**Assessment:** The close BJD agreement, RV-value agreement, and
observation-level association with ESO programme identifiers provide
strong evidence that these 156 published measurements overlap with
the local HARPS dataset. HD10180 therefore cannot be treated as an
independent observation-level benchmark against the Lovis et al. (2011)
reference data.

The remaining 34 published observations were not matched within the
2-second tolerance in this pilot. Their provenance is unresolved; a
non-match in this comparison does not establish that they are absent
from the archive or independent.

This is a pilot result for HD10180 only. It must not be generalized
to the other 17 targets without equivalent observation-level checks.
The 156 overlapping observations must be grouped together for any
future data splitting or evaluation involving this publication, to
prevent observation-level leakage. No planet-confirmation or
AI-performance claim follows from this provenance comparison.

---

## 8.2 HD192310 â€” Six-Exposure CCF and Target-RV Prior Investigation

**Status:** Strong evidence of a target-RV-prior-associated CCF failure; causal attribution remains unconfirmed.

### Six-exposure comparison

The six archived HARPS DRS auxiliary products for the two three-exposure sequences were inspected.

| Exposure sequence | Target RV input (km/s) | CCF RV (km/s) | Drift-corrected CCF RV (km/s) | FWHM |
|---|---:|---:|---:|---:|
| 2004-12-02 00:06:48.081 | 0.0 | +0.719477 | +0.719363 | 4.9120 |
| 2004-12-02 00:11:49.290 | 0.0 | +0.703833 | +0.703634 | 4.8824 |
| 2004-12-02 00:16:50.760 | 0.0 | +0.765966 | +0.765877 | 4.8675 |
| 2004-12-04 00:11:15.049 | -54.4 | -54.224701 | -54.225011 | 6.0948 |
| 2004-12-04 00:16:15.918 | -54.4 | -54.224604 | -54.225019 | 6.0943 |
| 2004-12-04 00:21:18.778 | -54.4 | -54.224854 | -54.225136 | 6.0962 |

The December 2 CCF velocity grid starts at -20.0 km/s with a 0.25 km/s step and 161 bins, corresponding to a nominal range of -20.0 to +20.0 km/s. The December 4 grid starts at -74.4 km/s with the same step and 162 bins, corresponding to -74.4 to -34.15 km/s. In both sequences, the grid is centered on the supplied target-RV prior (approximately target RV Â±20 km/s).

### Interpretation

- All three December 2 exposures used the header value ESO TEL TARG RADVEL = 0.0 km/s and returned CCF RVs near +0.7 km/s.
- All three December 4 exposures used ESO TEL TARG RADVEL = -54.4 km/s and returned consistent CCF RVs near -54.225 km/s.
- The anomalous value is present in the archived DRS CCF products themselves; it is not merely a later CSV export or catalogue-join error.
- The sequence-level consistency and the different CCF search windows strongly support the hypothesis that the incorrect December 2 target-RV prior caused the DRS CCF search to operate in the wrong velocity region and return a false solution.
- The CCF contrast values differ substantially between the two sequences (approximately 0.41 versus 45.4). Their units/normalization have not been established here, so this difference is recorded but not interpreted as a quality metric.

### Limitation and required confirmation

This is strong diagnostic evidence, not a completed causal demonstration. The archived CCF products alone do not prove what the pipeline would return if the December 2 spectra were reprocessed with a correct target-RV prior or the documented iterative mode. A controlled DRS reprocessing or an independently validated wider-velocity CCF analysis is still required before assigning the root cause conclusively.

**Benchmarking consequence:** HD192310 must not be treated as an independent observation-level benchmark against the Pepe et al. (2011) publication. The previously established timing-overlap evidence remains: 50 unique ESO observations matched published epochs within 300 seconds, with 49 of those 50 RV differences within 10 m/s; one match is the identified grossly anomalous December 2 record. The remaining published epochs are not classified by this comparison.

**Data handling:** No observations were deleted or altered. The investigation used archived DRS CCF/BIS products and header metadata.


---


## 8.3 HD20794 — Nari et al. (2025) YARARA and ESPRESSO Cross-Pipeline Investigation

### HARPS YARARA overlap

The Nari et al. (2025) HARPS03 and HARPS15 YARARA datasets were compared against ESO HARPS archive observations for HD20794.

**HARPS03 YARARA**
- Published observations: 514
- Unique ESO matches within 10 seconds: 22
- Unique ESO matches within 60 seconds: 124
- Median RV offset at 60 seconds: +87,954.914 m/s
- Median absolute residual: 4.549 m/s
- 95th percentile residual: 7.586 m/s

**HARPS15 YARARA**
- Published observations: 232
- Unique ESO matches within 10 seconds: 10
- Unique ESO matches within 60 seconds: 33
- Median RV offset at 60 seconds: +87,979.687 m/s
- Median absolute residual: 0.955 m/s
- 95th percentile residual: 14.485 m/s
- One observation has a large residual of approximately 1,846 m/s and requires separate investigation.

These results provide evidence of temporal correspondence with ESO archive observations. They do not prove that every corresponding measurement is the exact same exposure.

### ESPRESSO SBART and DRS cross-pipeline comparison

Three Nari et al. (2025) ESPRESSO tables were examined:

- espsbart: 695 numeric observations
- esp19drs: 656 numeric observations
- esp18drs: 29 numeric observations

The DRS reduced-JD values were converted using JD = table value + 2,400,000 before comparison with full BJD values.

**SBART versus DRS 2018**
- 29 of 29 DRS observations matched SBART timestamps exactly.
- Median RV offset: -10.863 m/s.
- Median absolute residual: 0.051 m/s.
- Maximum absolute residual: 0.295 m/s.

**SBART versus DRS 2019**
- 651 DRS observations matched SBART timestamps exactly.
- Median RV offset: -14.919 m/s.
- Median absolute residual: 0.256 m/s.
- Maximum absolute residual: 2.952 m/s.

**DRS 2018 versus DRS 2019**
- No matches within 1,800 seconds.
- The two DRS tables represent different observing periods in this comparison.

The SBART and DRS products contain overlapping observations and must not be counted as three independent ESPRESSO datasets. Their RV zero-points differ and should be accounted for during future calibration.

### Benchmarking implications

- HARPS YARARA and ESO HARPS archive observations show evidence of overlap.
- ESPRESSO SBART and DRS products show strong cross-pipeline overlap.
- ESPRESSO is a different spectrograph from HARPS and may support cross-instrument validation.
- These Nari et al. datasets are publication-associated data and should not be described as publication-independent validation.
- No observations were deleted or modified.
- No scientific algorithms or model parameters were changed.
- Independent benchmark conclusions remain provisional pending final provenance and cross-instrument checks.


## 8.4 HD40307 — Mayor et al. (2009) and Tuomi et al. (2013) Observation-Level Overlap

### Mayor et al. (2009) published RV comparison

The published Mayor et al. (2009) RV table was compared against the ESO HARPS archive observations for HD40307.

- Published numeric observations: 129
- Matched observations within 300 seconds: 127
- Unique matched ESO archive observations (DPIDs): 127
- Median absolute time difference: 0.034560 seconds
- Median absolute RV difference: 1.505171 m/s
- Mean absolute RV difference: 1.596171 m/s
- 95th percentile absolute RV difference: 2.766497 m/s
- Maximum absolute RV difference: 4.318722 m/s
- All 127 matches belong to ESO programme `072.C-0488(E)`.
- Two published observations remain unmatched within the 300-second threshold; one additional match was found within 1800 seconds and is not classified as a 300-second match.

These results provide strong evidence of observation-level overlap. The Mayor et al. (2009) observations must therefore not be treated as an independent observation-level benchmark against this ESO archive dataset.

Diagnostic file:
`data/hd40307_mayor_2009_overlap_diagnostic.csv`

### Tuomi et al. (2013) Table A.2 comparison

The 345 extracted published rows from Tuomi et al. (2013), Table A.2, were matched against the ESO HARPS archive observations for HD40307.

- Published rows: 345
- Matched ESO observations: 345
- Unique matched ESO archive DPIDs: 345
- Duplicate DPID assignments: 0
- Maximum absolute time difference: 0.429408 seconds

The paper labels its time column as JD. These timestamps align with the ESO archive BJD values to sub-second precision; the time-column label is therefore retained as published rather than relabelled as BJD.

The paper provides separate differential radial-velocity series for the full spectrum (F) and red spectral region (R). They were compared separately with the ESO DRS RV values:

| Comparison | Median ESO-minus-published offset | Median absolute residual after offset |
|---|---:|---:|
| F series | +31,334.148 m/s | 0.306 m/s |
| R series | +31,334.048 m/s | 0.635 m/s |

The large constant offset must not be interpreted as an instrumental zero-point error. The published values are differential RVs, whereas the ESO DRS values use an absolute RV scale; their reference conventions differ. The residual statistics are reported after subtracting each series' median offset.

The one-to-one timestamp and DPID correspondence provides very strong evidence that all 345 published rows correspond to observations in the ESO archive. This is not an independent observation-level benchmark.

Verification file:
`data/hd40307_tuomi_2013_overlap_verification.csv`

### Benchmarking implications

- Both the Mayor et al. (2009) and Tuomi et al. (2013) datasets overlap with the local ESO HARPS archive observations.
- HD40307 must not be counted as an independent observation-level validation target against either publication.
- The F and R RV series remain distinct and are not merged.
- No observations were deleted or modified.
- No scientific algorithms, model parameters, or production code were changed.
- These findings strengthen the provenance assessment but do not independently validate planet detections or the RV model.

## 8.5 HD160691 (μ Arae) — Pepe et al. (2007) Observation-Level Overlap

### Published RV table and time convention

The published radial-velocity measurements were extracted from Table 3 of Pepe et al. (2007), "The HARPS search for southern extra-solar planets IX. μ Ara, a system with four planets" (A&A, 462, 769).

- Published numeric records extracted: 86
- The table reports its time column as reduced JD (`T - 2,400,000`).
- The published time column is retained as JD and is not relabelled as BJD.
- The table contains the historical 2003 measurement and observations from the 2004–2006 HARPS observing period.

### Individual ESO exposure matching

Each published timestamp was compared with the nearest individual ESO HARPS archive exposure for HD160691. Matching was assessed using a 300-second tolerance.

- Published records: 86
- Matched published records within 300 seconds: 83
- Unique matched ESO archive DPIDs: 83
- Duplicate DPID assignments: 0
- Unmatched published records: 3
- Median absolute time difference: 41.258 seconds
- Maximum absolute time difference: 233.998 seconds

The 83 matched observations belong to the following ESO programmes:

| ESO programme | Matched observations |
|---|---:|
| `072.C-0488(E)` | 77 |
| `073.D-0578(A)` | 6 |

The three unmatched published records correspond to:
- 2003-09-24: a historical measurement preceding the available ESO HARPS archive observations in this dataset.
- 2004-06-04 and 2004-06-05: published observations preceding the first available local ESO archive observation for this target, dated 2004-06-06.

### RV comparison

For the 83 timestamp-matched observations:

- Median RV offset (published minus ESO): approximately -6.950 m/s.
- Median absolute RV residual after subtracting the median offset: 1.343 m/s.
- 95th percentile absolute residual after offset: 4.182 m/s.

The published values are nightly measurements, whereas the matched ESO values are individual exposures. Therefore, these RV residual statistics are exploratory and should not be interpreted as a direct same-measurement comparison or as a definitive instrumental zero-point estimate.

### Benchmarking implications

- The 83 unique timestamp matches provide strong evidence of observation-level overlap between Pepe et al. (2007) and the local ESO HARPS archive dataset.
- HD160691 must not be treated as an independent observation-level benchmark against Pepe et al. (2007).
- The three unmatched published records are retained as unmatched; no synthetic matches are assigned.
- No observations were deleted or modified.
- No scientific algorithms, model parameters, or production code were changed.

Verification file:
`data/hd160691_pepe_2007_final_overlap_verification.csv`

Diagnostic file:
`data/hd160691_pepe_2007_individual_overlap_diagnostic.csv`

**End of Interim Stage 6 Report**



## 8.6 HD19994 ? Mayor et al. (2004) CORALIE Orbital Reproduction

### Reference dataset and provenance

A 48-observation radial-velocity time series associated with Mayor et al. (2004), bibcode `2004A&A...415..391M`, was retrieved from the NASA Exoplanet Archive literature time-series collection.

- Target: HD 19994
- Reference: Mayor et al. (2004), A&A, 415, 391
- Telescope: 1.2-m Euler Swiss telescope
- Instrument: CORALIE
- Observatory: ESO La Silla, Chile
- Time reference: BJD
- RV units: m/s
- RV uncertainty units: m/s
- Observations: 48
- Unique timestamps: 48
- Time baseline: 1,518.889 days
- RV range: 19,280 to 19,382 m/s
- Mean reported RV uncertainty: 6.667 m/s

The downloaded file is the NASA Exoplanet Archive literature time-series copy. Its association with the publication and its metadata were verified; byte-for-byte identity with an original CORALIE source file has not been established.

Reference file:

`data/hd19994_mayor_2004_nasa_archive.tbl`

### Published-orbit reproduction

The published orbital parameters were held fixed for the reproduction:

| Parameter | Adopted value |
|---|---:|
| Period | 535.7 days |
| Eccentricity | 0.30 |
| Published periastron epoch | 2450944 (time standard not independently verified) |
| Argument of periastron | 41 degrees |
| Published semi-amplitude | 36.2 m/s |

Only the systemic velocity and semi-amplitude were fitted to the 48 archived observations.

| Metric | Reproduction result |
|---|---:|
| Fitted systemic velocity | 19,335.1774 m/s |
| Fitted semi-amplitude | 35.9578 m/s |
| Difference from published K | -0.2422 m/s |
| Relative K difference | -0.67% |
| Weighted residual RMS | 7.9807 m/s |
| Reduced chi-square | 2.1255 |
| Residual minimum | -27.5106 m/s |
| Residual maximum | +22.2548 m/s |

The recovered semi-amplitude is close to the published value. This is a successful reference-level orbital reproduction, conditional on the adopted published orbital parameters. A formal uncertainty for the newly fitted semi-amplitude was not calculated in this test.

### Localized residual variability

A previously identified interval, BJD 2451500-2451700, was examined separately. It contains 19 observations.

| Metric | Interval (19 observations) | Outside interval (29 observations) |
|---|---:|---:|
| Mean residual | -3.311 m/s | +0.086 m/s |
| Weighted residual RMS | 12.491 m/s | 5.844 m/s |
| Diagnostic chi-square per (N-2) | 3.415 | 1.471 |
| Minimum residual | -27.511 m/s | -12.421 m/s |
| Maximum residual | +22.255 m/s | +18.249 m/s |

The weighted residual RMS inside the selected interval is approximately 2.14 times the value outside it. This indicates elevated residual variability within that interval. The diagnostic chi-square values use an (N-2) denominator; the orbital parameters were fitted globally and were not refitted independently within each subset. These values should not be interpreted as formal subset-specific reduced chi-square statistics.

The interval was selected for a targeted diagnostic rather than through a blind search. The comparison is therefore descriptive and must not be interpreted as a blind detection or a formal significance test. Stellar activity, instrumental effects, and other possible causes have not been distinguished.

Residual plot:

`data/hd19994_mayor_2004_residuals.png`

### Benchmarking implications and limitations

- HD 19994 provides a CORALIE literature-reference reproduction, not an observation-level match against the local HARPS dataset.
- The recovered semi-amplitude agrees closely with the published reference value.
- The elevated residual variability in the selected interval remains unexplained.
- The NASA archive copy is not claimed to be byte-identical to the original publication data file.
- This exercise is not an independent planet discovery validation because it reproduces a published orbital solution using a literature time series associated with that publication.
- No observations were deleted or modified.
- No production scientific algorithms or model parameters were changed.
- No conclusions about the physical cause of the residual variability are made.

## 8.7 HD136352 (?? Lupi) ? HARPS DACE?ESO Provenance and RV Consistency Investigation

### Reference context and data sources

HD136352 was examined using the local ESO HARPS archive observations, DACE standard-processed radial velocities, and the published HARPS reference context.

The relevant reference is Udry et al. (2019), A&A, 622, A37, which reports 649 HARPS spectra and 240 one-hour-binned radial-velocity measurements for HD136352.

The individual ESO archive dataset contains 685 observations for this target. These counts describe different data products and must not be treated as interchangeable.

A separate published dataset from Kane et al. (2020), *HARPS, HIRES and AAT Radial Velocities of HD 136352*, was also examined. Its HARPS table contains 246 observations.

### ESO archive provenance

The local ESO HARPS dataset contains 685 HD136352 observations.

The ESO archive cross-match established observation-level provenance for the local records. The RV values used in the local dataset were verified against the ESO drift-corrected barycentric CCF RV field (`drs_ccf_rvc`) after conversion from km/s to m/s.

The local ESO dataset therefore has verified archive provenance. This does not, by itself, establish equivalence to a particular publication's binned time series.

### DACE standard-processing comparison

The DACE standard HARPS dataset contains 716 records for HD136352.

A one-to-one time-based cross-match using a 300-second tolerance produced:

| Metric | Result |
|---|---:|
| DACE HARPS records | 716 |
| Local ESO observations | 685 |
| Matched observations | 680 |
| Unmatched DACE records | 36 |
| Unmatched ESO observations | 5 |
| Median absolute time difference | approximately 66.7 seconds |
| Maximum time difference among matches | approximately 201.1 seconds |

For the 680 matched observations, the global median DACE-minus-ESO RV offset was approximately -5.676 m/s. After subtracting that median offset, the residual RMS was approximately 1.164 m/s and the median absolute deviation was approximately 0.457 m/s.

These statistics indicate substantial overall agreement, but they do not establish that the two processing products are numerically identical or that a single global offset explains every observation.

### Programme-specific discrepancy

The 38 DACE records associated with programme 192.C-0852(A) comprise:

- 31 HARPS03 records.
- 7 HARPS15 records.

All 38 records report DRS version 3.3.6, DRS ID 15, latest-DRS status, and CCF RV extraction.

The seven HARPS15 observations correspond to the investigated discrepant records. Their RV differences relative to the matched ESO observations are substantially larger than those seen for most other matched records:

- 2015-06-08: approximately -8.03 m/s.
- 2015-06-10: approximately -8.07 to -8.50 m/s.
- 2015-08-24: approximately +7.00 to +7.24 m/s.
- 2016-02-07: approximately -9.65 m/s.

The HARPS15 records show differences in CCF FWHM and contrast relative to the HARPS03 records. The two observations on 2015-08-24 also have `cal_drift_rv` values near -0.0204 km/s.

These are diagnostic observations, not proof of a causal mechanism. The common DRS version does not establish identical calibration histories, and the available metadata do not establish that the CCF or drift terms caused the RV discrepancies. The discrepancy therefore remains unresolved.

### Other unmatched DACE records

Of the 36 unmatched DACE records, 27 belong to programme 60.A-9036(A) and have extreme RV values around -82,556 to -82,880 m/s with substantially larger quoted uncertainties. The remaining nine unmatched records belong to programme 183.C-0972(A).

These unmatched records are retained as provenance limitations. They are not assigned synthetic ESO matches.

### Kane et al. (2020) published-table comparison

The 246-row Kane et al. HARPS table was independently compared with the local ESO observations.

A time-based match within 300 seconds identified 245 corresponding observations. After removal of the median RV zero-point difference, the residual RMS was approximately 2.138 m/s.

This is a separate publication-table comparison. It must not be conflated with the Udry et al. (2019) one-hour-binned dataset.

### Benchmarking implications and limitations

- The local 685-row ESO dataset has verified archive provenance.
- The DACE standard HARPS comparison shows broad agreement, with a small number of unresolved discrepancies and unmatched records.
- The seven discrepant HARPS15 records require caution; their cause has not been established.
- The 27 extreme unmatched DACE records from programme 60.A-9036(A) are not treated as validated ESO observations.
- The Kane et al. (2020) table provides a separate published-table comparison with 245 matched observations.
- The Udry et al. (2019) set of 240 one-hour-binned measurements has not been directly reproduced or independently validated observation by observation in this investigation.
- HD136352 is therefore a useful provenance and cross-pipeline consistency case, but it is not a fully independent validation benchmark.
- No observations were deleted or modified.
- No production scientific algorithms, model parameters, or training data labels were changed.

Verification inputs:

- `data/hd136352_dace_standard_rv.csv`
- `data/hd136352_dace_public_frames.csv`
- `data/hd136352_kane_2020_table1_raw.tsv`
- `../data/interim/harps_rv_observations_18_targets.csv`

## 8.8 HD72673 — ESO Archive, CCF Mask and Activity-Indicator Investigation

An investigation of HD72673 was conducted using 526 observations retrieved from the ESO HARPS radial-velocity catalogue. This target is separate from the original 18-target local HARPS time-series dataset.

### Archive and CCF mask findings

All 526 observations contained the inspected RV, uncertainty, CCF, BIS and H-alpha catalogue fields.

The CCF mask distribution was:

- K5: 501 observations
- K0: 10 observations
- G2: 10 observations
- M2: 5 observations

Substantial RV distribution differences were observed between masks. These differences must not be interpreted directly as astrophysical RV offsets because the CCF templates have different reference characteristics.

The five catalogue-selected M2 observations had CCF contrasts of approximately 3.54–3.56%, substantially below the typical contrasts of the other mask groups. Ancillary CCF products from six selected observations showed similarly low M2 contrast behaviour, including an observation whose catalogue-selected mask was K5. Therefore, low M2 contrast alone does not explain the anomalous catalogue RV values.

### DRS version and observing-epoch limitations

For K5 observations, the median RV was approximately 14898.946 m/s for DRS 3.5 (448 observations) and 14917.155 m/s for DRS 3.8 (53 observations), a difference of approximately 18.21 m/s.

The version groups were not observed over equivalent time intervals. In programme 192.C-0852(A), DRS 3.5 observations cover January 2014 to May 2015, whereas DRS 3.8 observations cover November 2015 to March 2016. Consequently, the observed RV difference cannot be attributed uniquely to a DRS version change.

### BIS and H-alpha activity-indicator analysis

For the 501 K5 observations, the raw Spearman correlation between catalogue RV and BIS RV was 0.9595.

After programme and DRS-version median-centering, the correlation remained strong (rho = 0.9158). The corresponding centred correlations were:

- BIS span: -0.0811
- H-alpha RV: +0.1505
- H-alpha fit chi-square: -0.3097
- CCF contrast: -0.2403
- CCF FWHM: +0.3632

The strong BIS-RV association is not independent confirmation of stellar activity because both quantities are derived from related CCF information. The remaining indicators show weaker or mixed associations. Median-centering is a diagnostic adjustment; it does not replace a time-series activity model or account fully for within-group dependence and multiple comparisons.

### Benchmarking implications and limitations

- HD72673 is not part of the original 18-target local HARPS time-series dataset; this investigation uses a separate ESO archive query.
- The selected ancillary products provide detailed CCF and spectral information for six observations, not all 526 observations.
- Mask-dependent RV differences are documented.
- DRS version and observing epoch are confounded.
- The available activity indicators do not establish a definitive stellar-activity explanation.
- No planetary signal or planet-free status has been established by this investigation.
- HD72673 remains an unresolved RV/CCF investigation target.
- Negative-control eligibility remains on HOLD pending defensible detection limits and independent evidence.

No observations were deleted or modified. No production scientific algorithms, model parameters, or training labels were changed.


## 8.9 HD115617 (61 Virginis): YARARA–HARPS Observation-Level Provenance Validation

### Objective

Evaluate the temporal and radial-velocity correspondence between the published YARARA v2 dataset and the ESO HARPS archive observations for HD115617.

The purpose was to assess observation-level provenance correspondence, not to independently confirm the known planets or establish a new planetary signal.

### Data Sources

- Published YARARA v2 table retrieved through the IDIA/VizieR source.
- ESO HARPS archive metadata for the Stage 6 target sample.
- Local HARPS date inventory containing 218 observation dates.
- Published YARARA table containing 201 valid RV observations after correcting the table parsing procedure.

The original direct table retrieval returned a database connection error. The IDIA/VizieR copy was used instead. Its time column requires careful interpretation of its zero point and time convention.

### Temporal Correspondence

The published table contained 201 unique observation dates, while the local inventory contained 218 unique dates.

- Shared dates: 181.
- Published-only dates: 20.
- Inventory-only dates: 37.

The initial MJD-to-JD assumption using an offset of 2400000.5 did not produce close matches. A diagnostic using 2400000.0 produced substantially better temporal correspondence.

Within a 300-second nearest-time matching window:

- 192 published observations had a nearest ESO observation.
- 192 distinct ESO raw observation identifiers were selected.
- No raw observation identifier was reused among those nearest matches.
- No ambiguous nearest-time ties were identified.

Within a stricter 10-second window:

- 53 published observations matched.
- All 53 matched observations had distinct ESO raw observation identifiers.
- Median time difference was approximately -0.196 seconds.

These results provide strong temporal correspondence. However, the published table does not expose the ESO raw exposure identifiers, so nearest-time matching alone cannot prove exact exposure identity.

### Radial-Velocity Comparison

The ESO archive RV values were compared with the published YARARA RV values using a provisional scale conversion and a fitted zero-point offset.

For the 53 observations matched within 10 seconds:

- Pearson correlation: approximately 0.961.
- Diagnostic median offset: approximately 7754.309 m/s.
- Residual RMS after offset removal: approximately 1.051 m/s.
- Residual MAD: approximately 0.649 m/s.
- Maximum absolute residual: approximately 3.155 m/s.
- Residuals within 1 times the published uncertainty: 58.5%.
- Residuals within 2 times the published uncertainty: 81.1%.
- Residuals within 3 times the published uncertainty: 98.1%.

The offset was estimated from the same matched observations. Therefore, these residual statistics are an in-sample comparison, not an independent validation result.

The provisional factor-of-1000 conversion strongly improved the numerical comparison, but the archive column unit and time conventions must be verified against authoritative documentation before treating the RV comparison as a definitive unit-calibrated result.

The residual scatter also exceeds the median quoted published uncertainty. A formal combined uncertainty analysis, including ESO uncertainties and possible instrumental or processing systematics, has not been completed.

### Scientific Assessment

The investigation supports the following conclusions:

1. The target identity is established as HD115617 / 61 Virginis.
2. ESO archive provenance is available for this target.
3. Published YARARA observations show strong temporal correspondence with distinct ESO raw observation candidates.
4. The RV series show strong correlation after provisional scale and zero-point treatment.
5. Exact exposure identity and exact RV agreement have not been conclusively established.
6. This comparison does not constitute independent confirmation of the known planets.
7. The matched datasets must not be treated as independent benchmark datasets because they may derive from the same underlying HARPS observations.

### Final Status

**PARTIAL OBSERVATION-LEVEL PROVENANCE VALIDATION**

HD115617 provides a useful provenance-validation case study for Stage 6. The results support substantial temporal correspondence and partial RV agreement, while retaining explicit limitations concerning exposure identity, unit conventions, zero-point fitting, uncertainty treatment, and data independence.

This case study does not establish a new planet, independently confirm an existing planet, or qualify the target as an independent AI benchmark.

## 9. Current Scientific Assessment

### Completed

- HARPS dataset target and time-range inspection.
- ESO archive provenance cross-match for all 18 targets.
- One-to-one observation matching and archive identifier verification.
- Instrument-mode distribution and BJD/RV numerical consistency checks.
- NASA Exoplanet Archive publication metadata retrieval and initial planet-mass consistency review.
- Target-level publication-overlap and cross-pipeline investigations documented in Sections 8.1–8.8:
  - HD10180
  - HD192310
  - HD20794
  - HD40307
  - HD160691
  - HD19994
  - HD136352
  - HD72673: ESO archive, CCF mask, DRS-version and activity-indicator investigation documented; negative-control eligibility remains on HOLD.
- Identification of cases where published observations overlap the local archive data and therefore cannot be treated as independent observation-level benchmarks.
- Documentation of unresolved data-provenance, pipeline, and residual-variability limitations.

### Remaining before benchmark eligibility can be finalized

- Complete a consolidated audit linking discovery references, planet records, and the adopted reference labels.
- Define defensible positive, negative, and uncertain benchmark labels with traceable evidence.
- Identify and verify suitable negative-control systems.
- Assess target-selection bias and sampling limitations.
- Establish which targets and observations qualify as genuinely independent benchmarks.
- Finalize benchmark eligibility and dataset readiness criteria.

Stage 6 has completed substantial provenance and reference-comparison work. However, the investigations in Sections 8.1–8.8 do not by themselves establish a fully independent, label-validated benchmark dataset.

---

## 10. Conclusion

The 37,442-row local HARPS dataset has passed the documented ESO archive observation-matching and numerical consistency checks. All inspected local observations were matched to unique ESO archive records, supporting their archive provenance.

The target-level investigations in Sections 8.1–8.8 provide a more detailed assessment of publication overlap, instrument and pipeline consistency, and reference-data limitations. They also demonstrate why archive provenance must be distinguished from scientific benchmark independence.

HD136352 illustrates this distinction: the local ESO observations have verified archive provenance and show broad agreement with DACE standard HARPS measurements, but seven HARPS15 records have unresolved RV discrepancies. The Kane et al. (2020) comparison is a separate published-table check, while the 240 one-hour-binned Udry et al. (2019) measurements have not been directly validated observation by observation.

Across the investigated systems, publication overlap, pipeline differences, unresolved residual behaviour, and reference-label limitations must be accounted for before any target is designated an independent benchmark.

**Stage 6 status: In Progress — target-level provenance, CCF and activity-indicator investigations documented; final benchmark eligibility and label validation remain pending.**

This report does not approve AI training readiness, claim independent planet confirmation, or establish that the investigated targets form a statistically representative benchmark sample.

No production scientific algorithms or model parameters were changed as part of these investigations.
