# Stage 6 — Independent Benchmarking
## Scientific Progress and Data Provenance Report

**Status:** In Progress
**Report type:** Interim scientific assessment
**Project:** ExoAnalytica
**Stage:** 6 — Independent Benchmarking

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

---

**End of Interim Stage 6 Report**
