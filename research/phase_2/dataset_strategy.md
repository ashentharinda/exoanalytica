# ExoAnalytica - Phase 2
# Dataset Strategy

**Project:** ExoAnalytica
**Phase:** 2 - Research Planning
**Document:** Dataset Strategy
**Status:** Preliminary dataset plan
**Date:** 2026-11-19

---

## 1. Purpose

This document defines a reproducible dataset strategy for the ExoAnalytica research project.

The project investigates three exoplanet detection methods:

1. Transit photometry
2. Radial velocity (RV)
3. Gravitational microlensing

The objective is to identify scientifically suitable public datasets, define data quality requirements, establish a consistent data provenance strategy, and plan independent validation experiments.

This document does not authorize changes to existing scientific algorithms or application code.

## 2. Dataset Selection Principles

Datasets should be selected according to:

- Public availability and access conditions.
- Scientific reliability and traceable provenance.
- Availability of original observations or suitable processed products.
- Availability of measurement uncertainties.
- Clearly documented units and time standards.
- Sufficient observational coverage.
- Reproducibility of published results.
- Compatibility with the intended scientific analysis.
- Availability of independent validation information.
- Licensing, acknowledgement, and citation requirements.

A dataset must not be selected only because it is easy to download.

## 3. Primary Data Sources

### 3.1 Transit Photometry

**Primary archive:** Mikulski Archive for Space Telescopes (MAST)

**Missions:**
- Kepler
- K2
- TESS

**Potential data products:**
- Extracted light curves
- Target Pixel Files
- Data Validation products
- Mission catalogues
- Associated stellar information

**File formats:**
- FITS
- CSV or other tabular exports where available

**Candidate access tools:**
- Lightkurve
- Astroquery
- MAST interfaces and services

**Primary archive links:**
- Kepler: https://archive.stsci.edu/missions-and-data/kepler
- TESS: https://archive.stsci.edu/missions-and-data/tess
- MAST: https://archive.stsci.edu/

**Initial strategy:**

Kepler will be the initial controlled validation dataset because ExoAnalytica already has a Kepler-based processing workflow and previous validation work.

TESS will be investigated as a separate mission-validation dataset. Differences in cadence, observing sectors, systematics, and data products must be considered.

**Important quality fields:**
- Time
- Flux
- Flux uncertainty
- Quality flags
- Cadence
- Mission and sector/quarter
- Target identifier
- Pipeline and data-product provenance

Do not assume that all light curves use the same time reference or flux normalization.

### 3.2 Radial Velocity

**Primary instrument/data source:** HARPS

**Archive:** European Southern Observatory (ESO) Science Archive

The first public HARPS Radial Velocities Catalogue release contains observations from 2003 to 2023, including 289,843 catalogue observations of 6,488 unique astronomical objects.

The catalogue provides pipeline radial velocities and independent H-alpha line measurements, with different precision characteristics.

**Access links:**
- ESO Science Archive: https://www.eso.org/public/science/archive/
- HARPS catalogue: https://www.eso.org/qi/catalog/show/416
- HARPS release information: https://www.eso.org/cms/eso-archive-news/first-data-release-of-harps-radial-velocity-catalog.html
- Catalogue DOI: https://doi.org/10.18727/archive/33

**Potential data products:**
- Radial velocity measurements
- Measurement uncertainties
- Observation timestamps
- Spectral products
- Cross-correlation and pipeline products
- Instrument and observing metadata

**Important distinction:**

The public HARPS catalogue is useful for identifying targets and available measurements. It must not automatically be treated as a complete, uniformly sampled RV time series for every target.

For a scientific RV analysis, verify the availability and suitability of target-specific observation times, RV values, uncertainties, instrument configuration, and relevant metadata.

**Initial strategy:**

1. Identify suitable known planetary systems.
2. Check whether usable HARPS time-series observations are available.
3. Verify units, time system, uncertainty conventions, and instrument configuration.
4. Identify possible stellar activity and correlated-noise concerns.
5. Retain the original observations and provenance.

Other RV instruments such as ESPRESSO and CORALIE may be investigated later, subject to data suitability and access conditions.

### 3.3 Gravitational Microlensing

**Primary initial source:** OGLE public microlensing data resources

**Potential resource:**
OGLE-III and OGLE-IV reanalysis datasets published by Golovich and collaborators.

**Access link:**
https://gdo-microlensing.llnl.gov/

The resource provides event-level products, including:
- Fitted light-curve visualizations
- MAP model parameters
- MCMC parameter samples
- Event-specific data products

**Potential analysis inputs:**
- Event observation times
- Magnification or photometric measurements
- Measurement uncertainties, where provided
- Event identifiers
- Model parameters
- Alternative solutions
- Posterior samples

**Initial strategy:**

1. Select a small number of documented events.
2. Inspect available event-level files.
3. Verify the format and units of each observation.
4. Identify the published model and its assumptions.
5. Check whether posterior samples and alternative solutions are available.
6. Preserve event degeneracies and model uncertainty.

**Important limitation:**

A microlensing event is not automatically equivalent to a confirmed planet or a uniquely characterized planetary system.

Do not convert event-level model parameters into definitive planet properties unless supported by the published analysis.

Roman microlensing resources are now included in this strategy through the RMDC26 simulated datasets. These are suitable for a controlled prototype and simulation-based validation. Actual Roman GBTDS observations remain a separate future validation source and must not be conflated with the simulations.



### 3.4 Nancy Grace Roman Space Telescope - Microlensing

**Survey:** Galactic Bulge Time-Domain Survey (GBTDS)

**Status as of 19 November 2026:** NASA reported that Roman entered science commissioning in October 2026. The GBTDS is planned to begin in the first available observing window after commissioning. Therefore, the data strategy below separates currently available simulated datasets from future public Roman survey observations.

**A. Current pilot source - Roman Microlensing Data Challenge 2026 (RMDC26)**

Official data documentation:
https://rges-pit.org/data-challenge/data/

RMDC26 provides semi-realistic simulated data intended to represent the type and scale of data expected from the Roman GBTDS.

Available tiers:

| Dataset | Events | Observations | Data characteristics |
|---|---:|---:|---|
| Beginner | 188 | 9,230,048 | Photometric light curves; 14 columns |
| Experienced | 2,087 | 103,281,456 | Photometric and astrometric measurements; more complex lens/source configurations; 18 columns |
| Machine Learning | 372,655 | 18,441,855,367 observations in the observations table | Separate observation, metadata, and epoch tables; approximately 172 GB observations table |

The Beginner and Experienced test Parquet files are available through the RGES-PIT Hugging Face repositories. The two tiers are also mounted on the Roman Research Nexus for supported workflows.

**Initial selection:**
1. Start with a small subset of the Beginner tier.
2. Inspect schema, units, cadence, uncertainty fields, event identifiers, and simulation metadata.
3. Select a limited number of events with documented truth parameters.
4. Keep event-level grouping intact for validation.
5. Move to a small Experienced-tier sample only after the photometric workflow is understood.
6. Do not download or load the approximately 172 GB Machine Learning observations table in full for the initial pilot. Use documented remote querying or small selected subsets if needed.

**Potential analysis tasks:**
- Event classification and anomaly identification.
- Recovery of event-level microlensing parameters.
- Planetary perturbation modelling where applicable.
- Posterior and uncertainty calibration against simulation truth.
- Photometric and astrometric joint modelling using suitable Experienced-tier events.
- Comparison of alternative lens solutions and degeneracies.

**Important dataset limitations:**
- These are simulated observations, not actual Roman telescope survey data.
- The Experienced tier is filtered for likely anomalous events and is not representative of the complete expected event population.
- The machine-learning data product has a separate structure and should not be assumed interchangeable with the two challenge tiers.
- Simulation-based success must not be described as real-observation performance.

**B. Future validation source - actual Roman GBTDS observations**

Monitor official Roman and STScI data-release documentation for public GBTDS products after science operations begin.

The survey design includes approximately 12.1-minute F146 high-cadence observations during six high-cadence seasons, with lower-cadence monitoring in four middle seasons and additional photometric and grism-spectroscopic snapshots.

When public data become available, verify:
- Observation and event identifiers.
- Time system and cadence.
- Photometric calibration and uncertainty products.
- Astrometric measurements and uncertainty covariance where supplied.
- Quality flags, data-release version, and pipeline provenance.
- Event-level modelling products and publication references.
- Whether the data are suitable for independent validation.

Do not assume that all planned survey products will be released simultaneously or in the same format as RMDC26.

**C. Roman data access and analysis preparation**
- Roman Research Nexus: https://roman.science.stsci.edu/hub/
- Roman User Documentation: https://roman-docs.stsci.edu/
- RMDC26 challenge: https://rges-pit.org/data-challenge/
- RMDC26 data documentation: https://rges-pit.org/data-challenge/data/

The initial pilot should use a small reproducible sample and document the exact dataset tier, file version, event identifiers, and retrieval method.

## 4. Reference and Validation Catalogues

**Primary reference source:** NASA Exoplanet Archive

https://exoplanetarchive.ipac.caltech.edu/

Useful resources include:

- Planetary Systems (PS)
- Planetary Systems Composite Parameters (PSCompPars)
- Kepler Objects of Interest (KOI)
- Threshold-Crossing Events (TCE)
- Microlensing Planets table
- Stellar and host-star information

Programmatic access:
https://exoplanetarchive.ipac.caltech.edu/docs/program_interfaces.html

TAP documentation and query examples:
https://exoplanetarchive.ipac.caltech.edu/docs/API_queries.html

The current archive documentation indicates that TAP should be preferred for most programmatic table access. Legacy API table names and endpoints may have been retired.

**Reference data rules:**

- Record the table name and query.
- Record retrieval date.
- Record catalogue release/version when available.
- Retain publication references.
- Distinguish confirmed planets, candidates, false positives, and unclassified objects.
- Preserve parameter uncertainties and asymmetric errors.
- Do not treat catalogue values as direct measurements when they are derived parameters.

The NASA Exoplanet Archive is a reference and metadata source; it is not a replacement for original mission observations.

## 5. Initial Pilot Dataset Plan

The first dataset phase should remain deliberately small.

### Pilot A - Transit

Use the existing Kepler validation target KIC 11554435 (Kepler-63) as a reproducibility reference.

Purpose:
- Reproduce the previously documented data retrieval.
- Verify FITS integrity.
- Record cadence and time coverage.
- Preserve the current validated baseline.
- Compare output with published reference information.

This target is a pipeline validation example, not a statistically representative benchmark.

A separate set of known Kepler and TESS targets should be selected after data availability checks.

### Pilot B - Radial Velocity

Select a small set of well-documented planetary systems with accessible HARPS observations.

For each target, verify:
- Target identity
- Number of usable observations
- Observation time span
- RV measurement availability
- Uncertainty availability
- Instrument and pipeline metadata
- Published planetary reference parameters

Do not select targets solely from a catalogue name match.

### Pilot C - Microlensing

Select a small number of OGLE events with publicly available event-level data and documented model solutions.

For each event, verify:
- Event identifier
- Availability of observations
- Photometric uncertainty
- Time coverage
- Model parameter definitions
- Posterior sample availability
- Published event interpretation

Do not assume that the selected microlensing events have corresponding transit or RV observations.\n\n### Pilot D - Roman-like microlensing simulations\n\nBegin with a small, event-level subset of the RMDC26 Beginner tier. Verify the simulation truth fields, observation uncertainties, event grouping, and parameter conventions before selecting validation metrics. After the photometric pilot is reproducible, inspect a small Experienced-tier subset for joint photometric and astrometric modelling. Keep the simulation test set separate from any model-development or tuning sample.\n\nThis pilot validates analysis against simulated truth only. It does not validate performance on actual Roman observations.

## 6. Data Identification and Cross-Matching

A common identifier must not be assumed across all three methods.

Potential identifiers include:

**Transit:**
- Kepler ID (KIC)
- TESS Input Catalog ID (TIC)
- EPIC
- Coordinates
- Mission observation identifiers

**Radial Velocity:**
- Target name
- SIMBAD identifier
- Gaia source identifier
- Coordinates
- ESO observation and catalogue identifiers

**Microlensing:**
- Survey event identifier
- OGLE event designation
- Coordinates
- Published lens-system identifiers

**Reference catalogues:**
- Planet identifier
- Host-star identifier
- Alternative names and aliases
- Published reference identifiers

Cross-matching should use multiple independent fields where possible:

- Coordinates and angular separation
- Gaia source identifiers
- Published aliases
- Host-star information
- Literature references

Every association should record:

- Original identifiers
- Matching method
- Match confidence or status
- Supporting references
- Possible ambiguity

Use explicit association statuses:

1. Confirmed association
2. Probable association
3. Possible association
4. Unresolved association
5. No verified association

A shared host star does not automatically prove that two observations refer to the same planet.

## 7. Data Quality and Standardization

Each dataset should preserve the original source product.

Create normalized working representations only after recording the original metadata.

### 7.1 Time

Record:
- Original timestamp
- Time standard
- Time scale
- Time reference or offset
- Any conversion applied

Do not combine timestamps until their reference systems are verified.

### 7.2 Measurement units

Record original units and converted units separately.

Examples:

Transit:
- Flux
- Relative flux
- Flux uncertainty

RV:
- Radial velocity
- RV uncertainty
- Velocity units

Microlensing:
- Magnitude or flux
- Magnification
- Photometric uncertainty
- Model parameter units

### 7.3 Quality flags

Preserve mission-specific and instrument-specific quality flags.

Do not silently discard observations.

Every filtering step must be recorded and reproducible.

### 7.4 Missing observations

Distinguish:
- Not observed
- Not publicly available
- Not applicable
- Missing from the downloaded product
- Rejected by a documented quality filter

Missing data must not be interpreted as evidence against a planet.

### 7.5 Provenance

For every dataset, record:

- Source archive
- Dataset or observation identifier
- Retrieval date
- Original filename
- File checksum
- Data-product version
- Publication or DOI
- Processing steps
- Quality filtering
- Software version

## 8. Proposed Dataset Metadata Schema

The following fields are proposed for a future dataset manifest.

| Field | Description |
|---|---|
| dataset_id | Internal unique dataset identifier |
| method | Transit, RV, or Microlensing |
| mission_or_instrument | Kepler, TESS, HARPS, OGLE |
| target_or_event_id | Original source identifier |
| host_identifier | Verified host identifier, if available |
| observation_id | Original observation/product identifier |
| source_archive | Originating archive |
| source_uri | Original data location |
| retrieval_date | Retrieval date |
| file_checksum | Integrity verification |
| time_standard | Original time convention |
| measurement_unit | Original measurement unit |
| uncertainty_available | Whether uncertainty is supplied |
| quality_flags | Original quality metadata |
| reference_publication | Supporting publication |
| association_status | Cross-match status |
| processing_version | Processing pipeline version |

This schema is a planning proposal, not an implementation requirement.

## 9. Training, Validation, and Test Strategy

Data leakage must be prevented.

### 9.1 Transit model datasets

Where machine-learning training is performed:

- Group observations by target or planetary system.
- Prevent observations from the same target appearing in both training and test partitions.
- Use independent targets for final evaluation.
- Record class imbalance and selection effects.
- Avoid using test-set information during preprocessing or model selection.

### 9.2 RV datasets

For physical model validation:

- Use documented planetary systems.
- Compare model parameters against published reference solutions.
- Preserve measurement uncertainties.
- Consider correlated noise and stellar activity.
- Avoid random point-level splits that destroy time-series structure.

### 9.3 Microlensing datasets

For physical model validation:

- Use event-level partitions.
- Preserve alternative model solutions.
- Compare inferred parameters with published posterior distributions.
- Avoid splitting observations from one event across training and test sets.

### 9.4 Cross-method evaluation

Distinguish two different experiments:

**Experiment A - Same-system integration**

Use only systems for which the cross-method association has been independently verified.

**Experiment B - Independent method populations**

Compare candidates and population properties without claiming that observations from separate surveys refer to the same planet.

These experiments require different evaluation criteria.

## 10. Benchmark and Validation Metrics

Potential metrics include:

### Transit
- Detection recovery
- False-positive rate
- Precision and recall
- Period error
- Transit depth error
- Injection-recovery completeness

### Radial Velocity
- RV residuals
- Model likelihood
- Parameter posterior consistency
- Period and semi-amplitude recovery
- Predictive performance

### Microlensing
- Event parameter recovery
- Posterior consistency
- Model comparison
- Degeneracy preservation
- Event-level detection performance

### Evidence integration
- Calibration of uncertainty
- Reliability of cross-method associations
- Performance with missing modalities
- Robustness to inconsistent observations
- Reproducibility

Metrics must be selected according to the actual scientific question. A single accuracy score is not sufficient to evaluate the complete framework.

## 11. Proposed Data Organization

A future research data structure could follow:

research_data/
    manifests/
        transit_manifest.csv
        rv_manifest.csv
        microlensing_manifest.csv
    transit/
        kepler/
        tess/
    radial_velocity/
        harps/
    microlensing/
        ogle/
    reference_catalogues/
    validation/
    reports/

Large original datasets and cache files should not automatically be committed to Git.

The repository should primarily retain:
- Dataset manifests
- Download and retrieval instructions
- Small, permitted sample data
- Checksums
- Processing documentation
- Validation reports

Large files should be stored separately when necessary and permitted by the data source.

## 12. Data Access and Citation Requirements

Before downloading or redistributing any data:

- Review the archive's current access conditions.
- Review proprietary periods.
- Check redistribution and licensing conditions.
- Follow archive-specific acknowledgement requirements.
- Record dataset DOIs where supplied.
- Cite the relevant scientific publications.

For HARPS catalogue data, use the ESO-assigned DOI:
https://doi.org/10.18727/archive/33

For NASA Exoplanet Archive data, consult its acknowledgement and DOI guidance:
https://exoplanetarchive.ipac.caltech.edu/docs/acknowledging.html

## 13. Known Risks

1. Public catalogue records may not contain the original time-series observations.
2. Target identifiers may differ between archives.
3. Some observations may be proprietary or restricted.
4. Different missions use different time standards and quality conventions.
5. RV observations may be affected by stellar activity and instrumental systematics.
6. Microlensing solutions may be degenerate.
7. Cross-method overlap may be limited.
8. Survey selection effects may bias the apparent population.
9. Dataset sizes and availability may change.
10. A large dataset does not guarantee scientific suitability.

## 14. Recommended Execution Order

**Step 1:** Verify the existing Kepler validation dataset.

**Step 2:** Build a small and documented Kepler/TESS availability shortlist.

**Step 3:** Identify HARPS targets with suitable public RV observations.

**Step 4:** Identify OGLE events with suitable public event-level data.

**Step 5:** Verify source identifiers and reference publications.

**Step 6:** Create dataset manifests and record checksums.

**Step 7:** Establish independent validation samples.

**Step 8:** Review the complete dataset strategy before implementing additional analysis modules.

No large-scale download or application-code modification is required at this planning stage.

## 15. References and Official Data Resources

1. MAST - Kepler Mission Data:
   https://archive.stsci.edu/missions-and-data/kepler

2. MAST - TESS Mission Data:
   https://archive.stsci.edu/missions-and-data/tess

3. ESO - HARPS Radial Velocities Catalogue:
   https://www.eso.org/qi/catalog/show/416

4. ESO - HARPS Data Release:
   https://www.eso.org/cms/eso-archive-news/first-data-release-of-harps-radial-velocity-catalog.html

5. OGLE Reanalysis Microlensing Data:
   https://gdo-microlensing.llnl.gov/

6. NASA Exoplanet Archive:
   https://exoplanetarchive.ipac.caltech.edu/

7. NASA Exoplanet Archive API and TAP documentation:
   https://exoplanetarchive.ipac.caltech.edu/docs/program_interfaces.html

8. NASA Exoplanet Archive Data Resources:
   https://exoplanetarchive.ipac.caltech.edu/docs/data.html

## 16. Document Status

**Phase:** 2 - Research Planning

**Work package:** Dataset Strategy

**Status:** Preliminary strategy drafted.

**Dataset downloads:** Not initiated by this document.

**Application code changes:** None authorized.

**Scientific algorithm changes:** None authorized.

**Next work package:** Consolidated research plan and controlled pilot selection across Kepler, HARPS, OGLE, and RMDC26.

---

End of document.
