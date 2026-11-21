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

## 9. Current Scientific Assessment

### Completed

- HARPS dataset target and time-range inspection.
- ESO archive cross-match for all 18 targets.
- One-to-one observation matching.
- Archive identifier availability verification.
- Instrument-mode distribution inspection.
- BJD numerical consistency verification.
- RV measurement numerical consistency verification.
- RV uncertainty numerical consistency verification.
- NASA publication metadata retrieval.
- Initial planet-mass field consistency audit.
- Initial controversial-record identification.

### Pending

- Resolve all discovery references to bibliographic records.
- Determine observation/publication overlap.
- Assess whether any genuinely independent benchmark observations
  are available.
- Identify suitable negative-control systems.
- Define reliable positive, negative, and uncertain labels.
- Evaluate selection bias and target-level sampling.
- Finalize benchmark eligibility and dataset readiness.

---

## 10. Conclusion

The 37,442-row HARPS dataset has passed the current ESO archive
observation-matching and numerical consistency checks.

All local observation timestamps matched unique ESO archive records.
Archive identifiers and instrument metadata were available for every
matched record.

This provides strong evidence of observation-level archive provenance
for the inspected dataset.

However, scientific benchmark independence has not yet been
established. Publication overlap and reference-label reliability
remain essential unresolved questions.

Stage 6 therefore remains **In Progress**.

No AI training-readiness approval or planet-confirmation claim is
made by this interim report.


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

**End of Interim Stage 6 Report**

