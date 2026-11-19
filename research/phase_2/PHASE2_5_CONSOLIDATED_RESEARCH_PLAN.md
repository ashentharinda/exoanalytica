# ExoAnalytica - Phase 2.5
# Consolidated Research Plan and Dataset Pilot Selection

**Project:** ExoAnalytica  
**Phase:** 2.5 - Research Consolidation and Pilot Selection  
**Status:** Research plan for review; no implementation authorization  
**Date:** 2026-11-19  
**Repository:** `ashentharinda/exoanalytica`

---

## 1. Purpose

Phase 2.5 consolidates the four Phase 2 work packages into one executable research plan:

1. Literature review.
2. Research-gap analysis.
3. Dataset strategy.
4. Multimodal architecture planning.

The purpose is to convert the preliminary research direction into measurable research questions, define a small and scientifically defensible pilot for each observational method, and establish decision gates before software implementation.

This document is a planning and selection framework. It does not authorize changes to existing application code, scientific algorithms, API routes, database structures, or user interface.

## 2. Consolidated Research Direction

The current research direction is:

**An uncertainty-aware, provenance-preserving framework for analysing physically distinct exoplanet detection methods, with scientifically justified evidence association and explicit treatment of missing observations, selection effects, model uncertainty, and method-specific limitations.**

The three analysis methods remain independent at the scientific-model level:

- Transit photometry: periodic flux reductions and transit-shape information.
- Radial velocity: stellar line-of-sight velocity variations and Keplerian/system-noise modelling.
- Gravitational microlensing: event magnification and planetary perturbations, including photometric and, where available, astrometric information.

The research must support two different use cases:

### 2.1 Same-system characterization

Transit and RV observations may be jointly interpreted when target identity and planet association are independently supported. For a verified transiting planet, transit geometry can constrain inclination and RV can constrain the mass function, allowing a better-constrained mass and density estimate when the data support it.

### 2.2 Independent candidate and population analysis

Microlensing events will generally be analysed as independent events and compared with transit/RV populations at a population or catalogue level. A microlensing event must not be linked to an unrelated transit or RV target simply because a catalogue name, coordinate, or broad sky position appears similar.

For microlensing, the background source star and foreground lens/planet-host system are distinct identities and must be represented separately.

## 3. Research Questions and Measurable Objectives

The following questions refine the preliminary Phase 2 questions. They are research questions, not claims that the gaps are already novel.

| ID | Research question | Evidence required |
|---|---|---|
| RQ1 | How can outputs from transit, RV, and microlensing analyses be represented in a common evidence model without removing their physical assumptions? | Documented evidence fields, units, provenance, assumptions, uncertainty representation, and modality-specific validation |
| RQ2 | How reliably can uncertainty be preserved and calibrated from method-specific parameter estimation through reporting? | Parameter-recovery experiments, posterior coverage, calibration diagnostics, and sensitivity tests |
| RQ3 | How should the framework distinguish an unobserved modality from a searched-but-undetected signal? | Explicit observation/search states and sensitivity-conditioned non-detection tests |
| RQ4 | How can cross-method candidate association be made reliable without assuming that different detections refer to the same planet? | Verified identity examples, ambiguous cases, association confidence, and documented false-association analysis |
| RQ5 | How do method-specific detection and sample-selection effects influence comparisons between exoplanet populations? | Survey selection documentation, completeness assumptions, population weighting, and sensitivity analysis |
| RQ6 | How reliably can microlensing parameters be recovered from Roman-like simulated photometric and astrometric data, and what is needed before transfer to real Roman observations? | RMDC26 simulation benchmark, photometric/astrometric comparison, uncertainty evaluation, and a separate future real-data validation plan |

### 3.1 Required observation-state vocabulary

The evidence layer should distinguish at least:

1. **Observed and detected:** a relevant observation exists and a signal was detected.
2. **Observed and not detected:** the relevant search was performed, but no signal was detected; interpretation depends on sensitivity and completeness.
3. **Not observed:** no suitable observation is available.
4. **Not searched or not processed:** data may exist, but the relevant analysis has not been performed.
5. **Not applicable:** the modality or measurement is not meaningful for the particular analysis.

A missing modality must never be converted automatically into a negative detection.

## 4. Pilot Dataset Selection

The first pilots are deliberately small. Their purpose is to verify data access, schema, provenance, physical modelling feasibility, and reproducibility before expanding the sample.

### 4.1 Pilot A - Transit: Kepler baseline and controlled extension

**Primary reproducibility target:** KIC 11554435 (Kepler-63).

Reason for selection:
- It is already part of the project's Phase 1 validation work.
- A prior baseline period comparison and preprocessing/injection diagnostics are documented.
- It provides continuity with the existing transit pipeline.

Initial tasks:
- Reproduce the documented retrieval and data preparation.
- Verify original FITS integrity, time coverage, cadence, quality flags, and uncertainty fields.
- Compare the current output with the Phase 1 report and published reference information.
- Preserve the current baseline; do not alter algorithms as part of this pilot.

**Limitation:** Kepler-63 is a reproducibility case, not a statistically representative benchmark and not sufficient to establish general transit performance.

**Controlled extension:** After the baseline is reproduced, select a small group of additional Kepler targets with reliable published ephemerides and accessible light curves. Select a separate small TESS sample only after confirming target-specific products, cadence, quality information, and reference labels. Do not assume that Kepler performance transfers directly to TESS.

### 4.2 Pilot B - Radial Velocity: HARPS time-series feasibility

**Primary source:** ESO HARPS Radial Velocities Catalogue DR1 and linked ESO archive products.

The public catalogue contains 289,843 RV measurements for 6,488 objects observed between 2003 and 2023. The catalogue includes DRS RV measurements with typical precision around 0.5 m/s and separate H-alpha measurements with much larger typical errors. Catalogue-level records do not guarantee that every target has a sufficiently useful time series for planet modelling.

**Selection rule:** Do not select a target from a catalogue name match alone. For each candidate system, verify:

- Exact target identity and coordinate cross-match.
- Availability of the underlying time-series measurements, not only a catalogue summary.
- Number and temporal distribution of usable epochs.
- Time baseline and phase coverage relative to the published orbital period.
- Measurement uncertainties, quality flags, and instrument/pipeline metadata.
- Published orbital solution and reference uncertainties.
- Whether stellar activity or known additional planets materially complicate the pilot.

**Initial pilot size:** Select two or three systems only after this screening. A target failing the time-series or provenance checks should be rejected rather than forced into the pilot.

**Analysis objective:** Reproduce a documented RV signal or published solution with an independently specified model. Compare posterior estimates, residual behaviour, and uncertainty with the reference publication. Preserve the distinction between (M_p\sin i) and true mass unless inclination information justifies the latter.

### 4.3 Pilot C - Archival microlensing: OGLE and contributed light curves

**Primary sources:**
- OGLE event publications and associated public event products.
- NASA Exoplanet Archive microlensing resources and contributed planet light curves.

Select two or three events only after verifying:

- A stable event identifier and source publication.
- Publicly accessible time-series photometry, with observation times and uncertainties.
- Photometric passband and observatory/instrument metadata where available.
- Published model parameters or posterior samples.
- Availability of alternative solutions and degeneracy information.
- Sufficient documentation to reproduce at least one published fit.

The NASA Exoplanet Archive notes that contributed microlensing light curves exist for many, but not all, microlensing objects. The archive's Microlensing Table and Planetary Systems Table may list multiple solutions. Preserve those alternatives rather than selecting one solution without justification.

**Analysis objective:** Reproduce selected event-level fits and compare recovered parameters and uncertainty with published solutions. Do not convert event-level parameters into a definitive host mass, planet mass, or physical orbit unless the required additional constraints are available.

### 4.4 Pilot D - Roman-like microlensing: RMDC26 simulations

**Primary source:** Roman Microlensing Data Challenge 2026 (RMDC26).

RMDC26 provides semi-realistic simulated data intended to represent the type and scale of data expected from the Roman Galactic Bulge Time-Domain Survey.

Available challenge tiers documented by RGES PIT:

| Tier | Events | Observations | Main characteristics |
|---|---:|---:|---|
| Beginner | 188 | 9,230,048 | Photometric light curves; 14 columns |
| Experienced | 2,087 | 103,281,456 | Photometric and astrometric measurements; more complex lens/source configurations; 18 columns |

The Experienced sample is filtered for likely anomalous events and is not representative of the complete expected Roman event population.

A separate Machine Learning resource contains 372,655 events and an observations table of approximately 172 GB. It should not be downloaded or loaded in full for the initial pilot. Its metadata include population weights; any population-level use must account for those weights and the dataset's documented selection.

**Pilot sequence:**

**D1 - Schema and access inspection**
- Access the official Beginner Parquet product through the documented Hugging Face or Roman Research Nexus route.
- Inspect schema, units, time conventions, event identifiers, missing values, uncertainty fields, and metadata.
- Confirm whether the selected product exposes the truth/reference parameters needed for each proposed metric.
- Record file version, retrieval method, and checksum.

**D2 - Small photometric smoke test**
- Select approximately five events for a data-ingestion and end-to-end modelling smoke test.
- Include simple and more challenging event morphologies where the documented metadata permit.
- Use this tiny subset only to verify workflow behaviour; do not report it as a performance benchmark.

**D3 - Controlled benchmark**
- After schema and truth availability are confirmed, define a held-out event-level evaluation sample from an appropriate permitted data split.
- Keep every observation belonging to an event in the same partition.
- Do not tune model settings on a held-out challenge test set.
- If reference truth is unavailable for a product, use the challenge's prescribed evaluation route or another independently documented labelled simulation source; do not invent ground truth.

**D4 - Astrometric extension**
- Only after the photometric workflow is reproducible, select a small Experienced-tier sample.
- Validate astrometric coordinate frames, units, time references, uncertainty/covariance fields, and source/lens identity.
- Compare photometry-only inference with joint photometric/astrometric inference only where both data types support a valid common physical model.

**D5 - Large-scale ML data**
- Do not download the approximately 172 GB observations table in full.
- If later justified, use the documented event-level remote query/join workflow and preserve metadata weights and event grouping.

**Validation boundary:** RMDC26 experiments establish performance on simulated Roman-like data only. They do not establish performance on real Roman observations.

### 4.5 Pilot selection summary

| Pilot | Initial selection | Main purpose | Selection is conditional on |
|---|---|---|---|
| A - Kepler transit | KIC 11554435 | Reproduce Phase 1 baseline | Existing data and reference reproducibility |
| A2 - Kepler/TESS extension | Small verified target shortlist | Test robustness beyond one target/mission | Target-level data and reliable reference information |
| B - HARPS RV | 2-3 systems | Reproduce published RV solutions | Accessible usable time series and metadata |
| C - OGLE microlensing | 2-3 events | Reproduce event-level models | Public light curves and documented model solutions |
| D - RMDC26 Beginner | ~5 smoke-test events, then a separately defined evaluation sample | Roman-like photometric modelling | Schema and valid reference/truth information |
| D2 - RMDC26 Experienced | Small selected event sample | Photometric + astrometric modelling | Valid astrometric fields and event-level provenance |

These are proposed pilot sizes, not fixed scientific sample sizes for final statistical conclusions.

## 5. Roman Mission Readiness and Data Release Boundary

The Roman mission entered science commissioning in October 2026. STScI's current planning documentation lists the first high-cadence Galactic Bulge Time-Domain Survey observing window as approximately 12 February to 24 April 2027, subject to change.

Therefore, as of this plan's date:

- RMDC26 is the immediate Roman-like simulation resource.
- Actual Roman GBTDS observations are a future validation source.
- Planned observing dates are not proof that public data products have already been released.
- The team must check current NASA/STScI schedules and archive release notes before claiming actual Roman data availability.

The survey design includes high-cadence F146 observations at approximately 12.1-minute cadence during designated high-cadence seasons, plus lower-cadence monitoring and additional photometric/grism observations. The pipeline must use the actual cadence and metadata in each released product rather than hard-coding a nominal schedule.

## 6. Dataset Provenance and Quality Manifest

Every pilot dataset must have a manifest entry recording:

- Dataset and survey name.
- Mission, instrument, and product type.
- Target/event identifier and identifier namespace.
- Archive or repository URL.
- Product/release version.
- Retrieval date and method.
- Original filename and checksum.
- Time system, units, and coordinate frame.
- Measurement and uncertainty columns.
- Quality flags and filtering decisions.
- Reference publication and model solution.
- Simulation versus observation status.
- License, acknowledgement, and citation requirements.
- Processing software/version and configuration.

Original data should remain immutable. Any normalized or filtered product must be traceable to its source and transformation history. Large raw datasets and cache files should not automatically be committed to Git.

## 7. Validation and Evaluation Framework

### 7.1 Transit

Evaluate, as appropriate:
- Period and epoch recovery against reference ephemerides.
- Transit duration and depth preservation.
- Injection-recovery completeness across signal strengths.
- False-alarm and false-positive behaviour.
- Robustness across targets and mission products.
- Uncertainty calibration for fitted transit parameters.

### 7.2 Radial velocity

Evaluate:
- Period and orbital-parameter recovery.
- RV semi-amplitude and eccentricity uncertainty.
- Residual structure and correlated-noise diagnostics.
- Posterior coverage and sensitivity to stellar-activity assumptions.
- Consistency with published solutions using comparable parameter definitions.

### 7.3 Microlensing

Evaluate where supported by the model and reference data:
- Event and anomaly classification.
- Recovery of (t_E), (u_0), (q), (s), and (ho).
- Posterior coverage and parameter bias.
- Alternative-solution and degeneracy recovery.
- Photometry-only versus photometry-plus-astrometry constraints.
- Sensitivity to cadence, noise, and incomplete observations.

### 7.4 Evidence association and integration

Evaluate:
- Correct association of verified same-system transit/RV evidence.
- False association rate on ambiguous or unrelated targets.
- Correct distinction between missing, not searched, and observed non-detection.
- Preservation of modality-specific uncertainty and assumptions.
- Correct separation of microlensing source identity and lens/host identity.

Do not create one aggregate accuracy score across all modalities unless a scientifically justified common target and weighting scheme is established.

## 8. Data Partitioning and Leakage Prevention

- Keep all observations from one target/event within the same partition.
- Never split individual time-series rows randomly across train and test sets.
- Keep published reference solutions and challenge test labels out of model tuning where they are intended as blind evaluation.
- Record all exclusions and selection decisions before evaluating final performance.
- Separate model development, validation, and final evaluation.
- For population studies, account for survey selection functions and documented sample weights.
- Treat the RMDC26 Experienced tier as an anomaly-selected sample, not as a representative Roman population sample.

## 9. Research Work Sequence and Decision Gates

### Gate 1 - Documentation consistency
- Review Phase 2 literature, gap, dataset, and architecture documents together.
- Resolve duplicate or inconsistent statements and references.
- Maintain a clear boundary between established prior work and proposed contributions.

**Exit condition:** Consolidated plan approved and references checked.

### Gate 2 - Pilot data feasibility
- Reproduce the Kepler-63 baseline data package.
- Inspect the HARPS catalogue and underlying target-level time series.
- Identify OGLE events with accessible light curves and published solutions.
- Inspect RMDC26 Beginner schema and event-level reference/truth availability.

**Exit condition:** A small documented shortlist exists for each method, with no unresolved data-access or identity issue that invalidates the proposed pilot.

### Gate 3 - Scientific protocol
- Specify model assumptions and baseline methods for each modality.
- Specify metrics and uncertainty tests before examining final evaluation results.
- Define event/target-level partitions and leakage controls.
- Record expected limitations and stopping criteria.

**Exit condition:** Reproducible experiment protocol approved.

### Gate 4 - Independent scientific prototypes
- Transit baseline reproduction and controlled extension.
- RV model reproduction on selected HARPS targets.
- OGLE event-level microlensing reproduction.
- RMDC26 Beginner photometric prototype, followed by a limited Experienced-tier astrometric study.

**Exit condition:** Each module has its own documented validation report and known limitations.

### Gate 5 - Evidence integration research
- Define evidence records and association states.
- Test only verified same-system transit/RV examples.
- Test missing-modality and non-detection semantics.
- Keep microlensing event analysis independent unless a scientifically defensible association exists.

**Exit condition:** Evidence integration protocol passes controlled association and uncertainty tests.

### Gate 6 - Application integration decision
Only after the scientific prototypes and integration protocol have been reviewed should a separate proposal be made for changes to the existing ExoAnalytica application.

**Exit condition:** Explicit approval for any source-code, scientific algorithm, API, database, worker, or UI changes.

## 10. Potential Research Contributions and Novelty Caution

Potential contributions to investigate include:

1. A provenance-preserving evidence representation for physically distinct exoplanet detection methods.
2. Explicit treatment of unobserved, unsearched, and observed-but-not-detected modalities.
3. Uncertainty-aware cross-method association and characterization.
4. Selection-aware comparison of transit, RV, and microlensing candidate populations.
5. Reproducible photometric and astrometric microlensing evaluation using Roman-like simulations, with a controlled path to future observational validation.

These are candidate contributions. None should be described as novel until a systematic comparison with existing publications, datasets, and software demonstrates the distinction.

The combination of multiple methods, transit-plus-RV joint modelling, multimodal classification, and microlensing machine learning already have prior art. The research contribution must be narrower and experimentally demonstrated.

## 11. Immediate Next Actions

The next work should be limited to data feasibility, not application development:

1. Reproduce the Kepler-63 Phase 1 data manifest and baseline without changing the scientific pipeline.
2. Inspect HARPS catalogue fields and shortlist target-level time series.
3. Shortlist OGLE events with accessible light curves and published model solutions.
4. Inspect the RMDC26 Beginner Parquet schema and identify how event-level reference parameters are supplied.
5. Produce a pilot selection register with accepted/rejected candidates and reasons.
6. Return for review before downloading large datasets or writing scientific prototype code.

No mass download is required for this stage.

## 12. References and Official Data Resources

1. ExoMiner (2021): https://arxiv.org/abs/2111.10009
2. ExoMiner++ (2025): https://doi.org/10.3847/1538-3881/ae03a4
3. Hara & Ford (2023), RV statistical methods: https://doi.org/10.1146/annurev-statistics-033021-012225
4. Gaudi (2012), microlensing surveys: https://doi.org/10.1146/annurev-astro-081811-125518
5. Giannini & Lunine (2013), microlensing: https://doi.org/10.1088/0034-4885/76/5/056901
6. juliet (2019): https://doi.org/10.1093/mnras/stz2688
7. PlanetNet-MMG (2026): https://doi.org/10.1016/j.eswa.2026.132396
8. ESO HARPS Radial Velocities Catalogue DR1: https://www.eso.org/qi/catalog/show/416
9. ESO HARPS DR1 release description: https://www.eso.org/cms/eso-archive-news/first-data-release-of-harps-radial-velocity-catalog.html
10. NASA Exoplanet Archive - Microlensing resources: https://exoplanetarchive.ipac.caltech.edu/docs/microlensing.html
11. NASA Exoplanet Archive - Contributed data: https://exoplanetarchive.ipac.caltech.edu/docs/contributed_data.html
12. RGES PIT - RMDC26 overview: https://rges-pit.org/data-challenge/
13. RGES PIT - RMDC26 data documentation: https://rges-pit.org/data-challenge/data/
14. Roman Research Nexus: https://roman.science.stsci.edu/hub/
15. Roman User Documentation - first two years of science operations: https://roman-docs.stsci.edu/roman-community-defined-surveys/roman-observations-in-the-first-two-years-of-science-operations
16. NASA - Roman enters science commissioning (22 October 2026): https://science.nasa.gov/blogs/roman/2026/10/22/nasas-roman-space-telescope-enters-final-commissioning-phase/

---

## 13. Document Status

**Phase:** 2.5 - Consolidated Research Plan and Dataset Pilot Selection  
**Status:** Planning document  
**Application code changes:** None  
**Scientific algorithm changes:** None  
**API/database/UI changes:** None  
**Large dataset downloads:** Not initiated  
**Next milestone:** Pilot Data Feasibility and Pilot Selection Register

---

End of document.
