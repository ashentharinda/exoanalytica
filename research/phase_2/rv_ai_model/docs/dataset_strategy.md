# ExoAnalytica RV AI Model
## Dataset Strategy – Version 1.0

**Status:** Proposed research strategy
**Primary objective:** Scientifically reliable training and evaluation

---

## 1. Dataset Objectives

Build a reproducible dataset for identifying planetary radial-velocity
signals while accounting for stellar activity, instrumental effects,
correlated noise, and observational limitations.

The dataset should contain both positive and negative examples.

A dataset containing only known planet detections would create selection
bias and would not adequately represent real-world observations.

## 2. Data Sources

Potential observational sources:

- HARPS public observations
- ESO archive observations
- NASA Exoplanet Archive
- Published RV datasets with accessible measurements
- Other suitable public spectrograph archives

For each source, record:

- Target identifier
- Source archive
- Instrument
- Original file or dataset identifier
- Download date
- Data release or publication
- Units and time standard
- Usage restrictions and citation requirements

Do not assume that all published or archived measurements have identical
formats, uncertainty definitions, or calibration quality.

## 3. Canonical Observation Format

The initial standardized table should support these fields:

| Field | Description |
|---|---|
| target_id | Stable target identifier |
| time | Observation timestamp |
| time_format | Time representation |
| time_scale | UTC, TDB, etc. |
| rv | Radial velocity |
| rv_uncertainty | Measurement uncertainty |
| rv_unit | Usually m/s |
| instrument | Instrument identifier |
| activity_indicator | Optional activity measurement |
| activity_uncertainty | Optional uncertainty |
| source_id | Original source reference |

Preserve original observations separately from normalized data.

Do not discard original timestamps, uncertainties, or instrument metadata.

## 4. Dataset Categories

### A. Real planetary systems

Targets with independently established planetary signals.

Purpose:
- Reference evaluation
- Known-signal recovery
- Orbital parameter comparison

A known planet is not automatically an independent blind-test example
if its identity or period was used during model development.

### B. Real observational noise

Observations with no established planetary signal, or residual datasets
where the treatment of known signals is documented.

Purpose:
- False-positive evaluation
- Noise characterization
- Realistic injection experiments

Absence of a known detection does not prove that a target has no planets.

### C. Synthetic injected planetary signals

Artificial Keplerian signals injected into real observational noise.

Control parameters may include:

- Orbital period
- RV semi-amplitude
- Eccentricity
- Orbital phase
- Measurement uncertainty
- Observation cadence
- Instrument configuration

The original observations and injected signal parameters must be preserved.

Synthetic injections are labelled simulations, not real discoveries.

### D. Stellar activity and difficult cases

Where suitable data are available, include targets with activity indicators
and known activity-related RV variability.

Purpose:
- Test whether the model confuses stellar activity with planetary signals.
- Evaluate robustness against correlated noise.

## 5. Injection Strategy

Start with real observational time sampling and realistic noise.

Inject a controlled Keplerian signal into a documented observational
baseline.

Conceptually:

observed_RV = baseline_RV + injected_planet_RV

The baseline must not be assumed to be pure white noise.

Where necessary, evaluate different baseline treatments:

- Original observations
- Documented residuals after known-signal modelling
- Noise models with correlated components

Record the exact injection parameters and random seed.

Do not inject signals into a dataset and then place the same target in
both training and test splits.

## 6. Training, Validation and Test Separation

Use target-level separation.

All observations and derived samples belonging to one target must remain
within one dataset partition.

Recommended partitions:

- Training: approximately 70%
- Validation: approximately 15%
- Test: approximately 15%

These percentages are initial planning values, not mandatory final values.
The split must also consider the number of independent targets and
instrument coverage.

Additional safeguards:

1. Do not split individual observations randomly across partitions.
2. Do not place injections from one target in multiple partitions.
3. Do not tune thresholds using the final test set.
4. Keep blind targets hidden during model development.
5. Record the target-level split manifest.
6. Avoid duplicate or near-duplicate datasets across partitions.

## 7. Important Scientific Risks

### Data leakage
The same target, observation series, or derived signal may appear in
training and testing.

### Selection bias
Known planets are not representative of all observed stars.

### Instrument effects
Different spectrographs can have different offsets, noise properties,
and systematic errors.

### Correlated noise
Stellar activity and instrumental effects can create periodic signals.

### Sampling bias
Irregular observation cadence and limited time baselines affect
detectability.

### Label uncertainty
A published candidate may have uncertain status or incomplete
independent validation.

These risks must be documented for every dataset release.

## 8. Evaluation Metrics

Classification metrics:

- Precision
- Recall
- F1 score
- ROC-AUC
- PR-AUC
- False-positive rate

Scientific recovery metrics:

- Period recovery error
- Semi-amplitude recovery error
- Eccentricity recovery performance
- Injection-recovery completeness
- False detections per target
- Performance as a function of signal strength
- Performance as a function of observation baseline

Where probabilities are reported, evaluate calibration separately.

Report uncertainty and sample sizes alongside performance metrics.

## 9. Dataset Versioning

Each dataset release should contain:

- Dataset version
- Source manifest
- Target identifiers
- Processing configuration
- Validation summary
- Train/validation/test split manifest
- Injection configuration
- Random seeds
- Checksums
- Known limitations

Never silently replace raw observational data.

## 10. Initial Dataset Development Order

1. Identify a small set of suitable public RV datasets.
2. Inspect formats, units, time standards and metadata.
3. Create a canonical observation schema.
4. Build a source and provenance manifest.
5. Establish a small validated pilot dataset.
6. Implement classical baseline analysis.
7. Develop controlled injection experiments.
8. Expand the dataset after quality checks.

## 11. Important Boundary

The Pi Mensae HARPS pilot from Phase 2.6 is a known-signal research
validation exercise.

It must not be described as blind discovery or independent confirmation.

It may be used as a reference case after its data provenance,
processing decisions, and limitations are documented.

The initial RV AI dataset should not automatically copy or modify the
existing Pi Mensae research files.
