# ExoAnalytica - Phase 2.6
# Pilot Data Feasibility Register

**Project:** ExoAnalytica  
**Phase:** 2.6 - Pilot Data Feasibility  
**Assessment date:** 2026-11-19  
**Status:** Initial source-level feasibility assessment; target-level verification remains in progress  
**Scope:** Public data access, data structure, provenance, and pilot suitability  
**Restrictions:** No application-code, scientific-algorithm, API, database, worker, or UI changes. No bulk dataset downloads.

---

## 1. Purpose

This register records whether the proposed pilot datasets can be accessed and whether their documented data products appear suitable for controlled scientific experiments.

A source being publicly listed does not, by itself, establish that a particular target or event has sufficient observations for a reproducible analysis. Each target/event must pass the checks in this register before it is accepted.

Status vocabulary:

- **Verified - source level:** An authoritative archive or data provider documents the relevant data product and access route.
- **Partially verified:** The source exists, but a required property such as raw time-series availability, schema, or target-level coverage remains unverified.
- **Pending:** A target/event has not yet passed the required checks.
- **Rejected:** A candidate fails a documented requirement; record the reason.

## 2. Initial Feasibility Summary

| Pilot | Source | Initial status | Main finding | Next gate |
|---|---|---|---|---|
| Transit | MAST Kepler; KIC 11554435 / Kepler-63 | Partially verified | Phase 1 report records four FITS files and 10,297 prepared observations; MAST documents public Kepler light-curve products and retrieval tools. | Reconcile local files with MAST product identifiers, quarters, time coverage, quality flags, and uncertainties. |
| RV | ESO HARPS Radial Velocities Catalogue DR1 | Verified - source level | Public catalogue has 289,843 measurements for 6,488 objects and 52 documented columns, including time, RV, uncertainty, target coordinates, and instrument metadata. | Query candidate systems and inspect actual per-target epoch counts, baseline, flags, and phase coverage. |
| Archival microlensing | OGLE III/IV reanalysis; NASA Exoplanet Archive contributed data | Partially verified | LLNL documents event folders with fitted light-curve PDFs, MAP parameters, and MCMC traces. This page alone does not establish access to raw photometric time-series. | Identify events with downloadable time, flux/magnitude, uncertainty, passband, and observatory data plus published solutions. |
| Roman-like microlensing | RGES-PIT RMDC26 Beginner tier | Verified - source level; schema inspection pending | Official page documents a public Parquet file with 188 events, 9,230,048 observations, and 14 columns. It is simulated data. | Inspect Parquet metadata/schema and identify documented truth/reference fields before choosing events. |
| Roman-like photometric + astrometric microlensing | RGES-PIT RMDC26 Experienced tier | Verified - source level; deferred | Official page documents 2,087 events, 103,281,456 observations, and 18 columns; includes astrometry and a sample filtered for likely anomalies. | Defer until Beginner photometric workflow is understood; inspect coordinate frames, units, uncertainties, and selection effects. |

## 3. Pilot A - Transit: Kepler-63 (KIC 11554435)

### Existing evidence

The Phase 1 Final Validation Report records:

- Target: Kepler-63 (KIC 11554435).
- Four FITS files.
- 10,297 prepared observations.
- Approximately 228.96 days of observation baseline.
- Detected BLS period: 9.4312678112 days.
- Reference period: 9.4341505 days.
- Relative period difference: 0.03056%.

The report also documents limitations: this is one target, weak injected signals were not reliably recovered, and detrending produced measurable depth attenuation in the tested configuration. The target is a reproducibility case, not a representative benchmark.

### Source feasibility

MAST documents public Kepler extracted light curves, target pixel files, data-validation products, and programmatic retrieval via Astroquery/MAST services.

### Remaining checks

1. Identify the exact MAST product identifiers corresponding to the local four FITS files.
2. Record quarter/sector-equivalent product coverage, cadence, and time system.
3. Inspect FITS headers and table columns for time, flux, flux uncertainty, and quality flags.
4. Confirm checksums or stable file metadata for reproducibility.
5. Reproduce the documented data preparation without changing the pipeline or its scientific parameters.

**Decision:** Retain KIC 11554435 as the primary transit reproducibility target. Do not treat the Phase 1 result as general pipeline performance.

## 4. Pilot B - Radial Velocity: HARPS

### Source-level verification

The ESO HARPS Radial Velocities Catalogue DR1 documents:

- 289,843 catalogue measurements for 6,488 objects.
- Observations from 2003-09-19 to 2023-05-30.
- 52 columns.
- Target name and coordinates: `tel_object`, `tel_targ_alpha`, `tel_targ_delta`.
- Barycentric time: `drs_bjd` (days).
- Drift-corrected barycentric RV: `drs_ccf_rvc` (km/s).
- Estimated RV uncertainty: `drs_dvrms` (m/s).
- Instrument mode: `ins_mode` (HAM or EGGS).
- Signal-to-noise: `drs_snr`.
- Bisector and CCF diagnostics: `drs_bis_rv`, `drs_ccf_fwhm`, `drs_bis_span`.
- SIMBAD identifiers, coordinates, and stellar metadata.

The catalogue is a valuable target-discovery and measurement resource. A catalogue entry alone is not proof that the time series is sufficiently sampled or suitable for a planet-orbit fit.

### Candidate-selection status

**No HARPS target is accepted yet.** Candidate names must not be promoted to selected pilot targets until their exact catalogue rows and observation-level records are inspected.

### Required target checks

For each candidate:

1. Cross-match the target name and coordinates against a reliable stellar/planet catalogue and publication.
2. Extract all available HARPS DR1 rows for that target.
3. Count unique usable epochs and inspect duplicate or near-duplicate observations.
4. Calculate the time baseline and inspect temporal gaps.
5. Check `ins_mode`, DRS version, SNR, uncertainty, and quality/diagnostic fields.
6. Confirm units and use the barycentric time field consistently.
7. Compare sampling with the published orbital period and assess phase coverage.
8. Locate the published orbital solution and uncertainties.
9. Check known multi-planet signals and stellar-activity complications.

Select only two or three systems after screening. Preserve the distinction between minimum mass (M_p\sin i) and true mass.

### Important caveat

The catalogue description reports typical precision around 0.5 m/s for DRS RV measurements, while H-alpha line measurements have much larger typical errors (around 300 m/s). These are not interchangeable measurement series. The intended RV pilot should use the documented DRS RV product and its own uncertainty/diagnostic fields unless a separate scientific reason justifies another series.

**Decision:** Source-level feasibility passed; target-level selection pending.

## 5. Pilot C - Archival Microlensing: OGLE / NASA Exoplanet Archive

### Source-level verification

The Lawrence Livermore National Laboratory OGLE reanalysis resource documents public OGLE-III and OGLE-IV event folders. Each event folder is described as containing:

- `fit.pdf`: full light curve and parallax + Gaussian-process model fit.
- `fit_zoom.pdf`: zoomed event fit.
- `map.csv`: maximum-a-posteriori model parameters.
- `parallax_trace.csv`: MCMC parameter samples.

This is useful for model/reference information and posterior inspection. However, the listed four products do not, by themselves, demonstrate that the original observation-level photometric time series is available for independent re-fitting.

NASA Exoplanet Archive microlensing/contributed-data resources are an additional route to investigate for event-level contributed light curves and published information.

### Candidate-selection status

**No OGLE event is accepted yet.** A publication, event identifier, or fitted PDF alone is not enough to qualify an event for an independent data-reproduction pilot.

### Required event checks

1. Record stable event identifier and discovery/reanalysis publication.
2. Confirm an accessible observation-level light curve with time, measured flux or magnitude, and uncertainty.
3. Record passband, observatory, instrument, time standard, and relevant calibration information.
4. Locate published model parameters and uncertainty/posterior information.
5. Preserve alternative solutions and known degeneracies.
6. Verify whether the event is a planetary event and distinguish source-star identity from foreground lens/host identity.
7. Confirm that the available observations are sufficient to reproduce at least one published fit.

Select two or three events only after all essential checks pass.

**Decision:** Archive/model-reference feasibility partially passed; raw light-curve feasibility and event selection pending.

## 6. Pilot D - Roman-like Microlensing: RMDC26

### Beginner tier

The official RGES-PIT data page documents:

- Parquet file: `RMDC26_Beginner_Tier_test.parquet`.
- 188 events.
- 9,230,048 observations.
- 14 columns.
- Photometric light curves.
- Public Hugging Face dataset and a Roman Research Nexus mounted copy.

This is simulated challenge data designed to represent aspects of the expected Roman GBTDS data. It is not actual Roman survey observations.

### Required schema inspection

Before selecting any events, inspect Parquet metadata without loading the full table into memory. Record:

- Exact column names and data types.
- Event identifier and observation grouping.
- Time coordinate and time standard.
- Flux/magnitude units and normalization convention.
- Measurement uncertainty fields.
- Filter/passband and observatory/epoch fields, if present.
- Simulation labels and truth/reference parameter availability.
- Missing values, invalid measurements, and quality flags.
- Whether the provided challenge file has a prescribed evaluation split or restrictions on using reference information.

The official Beginner page documents the number of columns but does not enumerate all 14 names in its main data description. Do not invent a schema from the Machine Learning tier or assume the two products have identical structures.

### Machine Learning tier distinction

The separate `RGES-PIT/MachineLearning` product is not the same table as the Beginner challenge Parquet file. Its documented normalized tables are:

- Observations: `event_id`, `epoch_id`, `filt`, `flux_uJy`, `flux_err_uJy`, `true_flux_uJy`, `saturation_flag`.
- Metadata: `event_id`, `name`, `sim_label`, physical parameters, labels, and `final_weight`.
- Epochs: `epoch_id`, `bjd`, and observer-position coordinates.

The Machine Learning observations table contains over 18.4 billion rows and is approximately 172 GB. It must not be downloaded or loaded in full for the initial pilot. If used later, first filter metadata and query selected event IDs with a columnar/remote-query workflow. Account for `final_weight` when evaluating population representation.

### Experienced tier

The Experienced tier contains 2,087 events, 103,281,456 observations, and 18 columns, including astrometric measurements and more complex lens/source configurations. Its event sample is filtered for likely anomalies and is not representative of the full expected Roman event population.

Defer this tier until the Beginner photometric workflow is understood. Before joint photometric/astrometric modelling, verify coordinate frames, units, time conventions, uncertainty/covariance fields, and source/lens identity.

**Decision:** Beginner source-level feasibility passed; schema/truth inspection pending. Experienced tier deferred. No large dataset download authorized or started.

## 7. Pilot Acceptance Rules

A candidate target/event may be marked **Accepted for pilot** only when:

1. Data access is confirmed for the required observation-level data.
2. Identifiers and source provenance are stable and recorded.
3. Units, time standards, and uncertainties are documented.
4. The observation baseline/cadence/phase coverage is appropriate to the intended experiment.
5. A reference solution, truth set, or defensible evaluation protocol exists.
6. Known selection effects, degeneracies, and model limitations are recorded.
7. The candidate can be analysed without changing the existing application pipeline.

A candidate failing a critical requirement should be marked **Rejected** or **Deferred**, with the reason recorded. Do not fill a pilot quota with unsuitable data.

## 8. Immediate Work Sequence

1. Reconcile Kepler-63 local FITS files with MAST product identifiers and headers.
2. Query the HARPS catalogue for candidate known planetary systems and inspect per-target observation rows.
3. Verify event-level raw photometry availability for OGLE/NASA microlensing candidates.
4. Inspect RMDC26 Beginner Parquet schema and truth/reference fields using metadata or a small, controlled sample.
5. Update this register with accepted/rejected candidates, evidence, and source references.
6. Review the completed register before any bulk download or prototype implementation.

## 9. Research Integrity and Scope Control

- Simulation results must never be described as actual Roman observational performance.
- A catalogue record does not automatically constitute a usable time series.
- Missing observations are not non-detections.
- Microlensing source stars and foreground lens/host systems must remain distinct.
- Alternative microlensing solutions and degeneracies must be preserved.
- Transit + RV association requires independently supported target and planet identity.
- No aggregate cross-modality accuracy score should be reported without a scientifically justified definition and weighting.
- No application code, scientific algorithm, API, database, worker, or UI modification is included in this phase.
- No large dataset download is included in this initial feasibility assessment.

## 10. Official Sources and References

### Transit / Kepler
- MAST Kepler mission and data products: https://archive.stsci.edu/missions-and-data/kepler
- MAST Kepler search and retrieval: https://archive.stsci.edu/kepler/search_retrieve.html
- Kepler data product overview: https://exoplanetarchive.ipac.caltech.edu/docs/Kepler_Data_Products_Overview.html

### Radial velocity / HARPS
- ESO HARPS Radial Velocities Catalogue DR1: https://www.eso.org/qi/catalog/show/416
- ESO first HARPS catalogue release: https://www.eso.org/cms/eso-archive-news/first-data-release-of-harps-radial-velocity-catalog.html
- ESO programmatic archive access: https://www.eso.org/cms/eso-data/programmatic-access.html
- Catalogue DOI: https://doi.org/10.18727/archive/33

### Archival microlensing
- LLNL OGLE reanalysis data access: https://gdo-microlensing.llnl.gov/
- NASA Exoplanet Archive microlensing resources: https://exoplanetarchive.ipac.caltech.edu/docs/microlensing.html
- NASA Exoplanet Archive contributed data: https://exoplanetarchive.ipac.caltech.edu/docs/contributed_data.html

### Roman / RMDC26
- RMDC26 challenge: https://rges-pit.org/data-challenge/
- RMDC26 data and Parquet products: https://rges-pit.org/data-challenge/data/
- RGES-PIT Machine Learning dataset card: https://huggingface.co/datasets/RGES-PIT/MachineLearning

---

**Phase 2.6 status:** Initial feasibility assessment documented. Transit reproducibility target retained; HARPS target selection, OGLE raw-light-curve verification, and RMDC26 Beginner schema inspection remain the next evidence gates.
