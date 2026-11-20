# ExoAnalytica RV AI Model
## Research Architecture – Version 1.0

**Status:** Proposed research architecture
**Scope:** Independent Radial Velocity (RV) research module
**Production integration:** Not authorized at this stage

---

## 1. Research Objective

Develop an AI-assisted Radial Velocity system capable of identifying,
evaluating, and characterizing possible exoplanet signals in stellar
radial-velocity observations.

The system should distinguish planetary signals from:

- Stellar activity
- Instrumental offsets and systematics
- Correlated noise
- Measurement noise
- Other non-planetary periodic signals

The objective is not simply to classify a periodogram. The system must
evaluate the observational evidence and quantify uncertainty.

## 2. Core Design Principles

1. Scientific methods must remain interpretable and reproducible.
2. Classical statistical methods must provide independent baselines.
3. AI predictions must not replace scientific validation.
4. Uncertainty must be retained throughout the pipeline.
5. Data provenance and experiment configurations must be recorded.
6. Training and evaluation must prevent target-level data leakage.
7. The RV module must remain independent of the production Transit pipeline.

## 3. Proposed Processing Architecture

### Layer 1 – Data Acquisition

Potential sources:

- HARPS
- ESPRESSO
- HIRES
- SOPHIE
- Publicly available radial-velocity datasets

Every dataset must retain its original source, instrument, target identifier,
download date, and applicable usage conditions.

### Layer 2 – Data Validation and Normalization

Validate:

- Observation timestamps
- Time system and time standard
- RV units
- Measurement uncertainties
- Missing and duplicated observations
- Instrument identifiers
- Instrument-specific zero-point offsets

Do not combine observations from different instruments without explicitly
accounting for their offsets and possible systematic differences.

### Layer 3 – Signal Detection

Establish classical signal-detection baselines.

Candidate methods:

- Generalized Lomb–Scargle periodogram
- False-alarm probability estimation
- Keplerian periodogram approaches
- Residual periodogram analysis
- Multi-signal searches

Candidate periods must be treated as hypotheses, not confirmed planets.

### Layer 4 – Orbital Modelling

Evaluate candidate signals using Keplerian models.

Relevant parameters include:

- Orbital period (P)
- RV semi-amplitude (K)
- Eccentricity (e)
- Argument of periastron (omega)
- Time of periastron passage (T_periastron)
- Systemic velocity (gamma)

Where appropriate, account for multiple planets, instrument offsets,
stellar jitter, and correlated noise.

### Layer 5 – Feature Engineering

Potential features:

- Periodogram peak properties
- Signal-to-noise characteristics
- RV amplitude
- Orbital-fit residuals
- False-alarm probability
- Observation baseline
- Sampling-window characteristics
- Phase coverage
- Eccentricity constraints
- Activity indicators, when available
- Instrument information

Features must be calculated without using hidden test labels or future
evaluation information.

### Layer 6 – AI Modelling

The initial research should compare multiple approaches rather than
committing to one neural-network architecture.

Candidate models:

- Random Forest
- Gradient Boosting
- XGBoost, if justified
- 1D CNN using standardized periodogram representations
- Hybrid statistical and machine-learning model

The AI component should estimate whether an observed signal is
consistent with a planetary hypothesis, stellar activity, or noise.

Model scores must not be presented as confirmation probabilities unless
they have been properly calibrated.

### Layer 7 – Scientific Validation

Evaluate:

- Injection-recovery performance
- False-positive rates
- Bootstrap stability
- Recovery completeness
- Sensitivity to correlated noise
- Robustness across instruments
- Performance on unseen targets

Compare AI results with classical statistical baselines.

### Layer 8 – Candidate Reporting

Each candidate report should include:

- Target identifier
- Instrument and data provenance
- Candidate period
- RV semi-amplitude
- Orbital parameters, where constrained
- Measurement and model uncertainties
- Statistical evidence
- AI score and calibration status
- Validation results
- Known limitations

A candidate must never be described as a confirmed planet solely because
an AI model assigns it a high score.

## 4. Proposed Software Structure

- src/data: acquisition and data validation
- src/features: periodogram and signal features
- src/models: AI model definitions
- src/training: training and experiment workflows
- src/evaluation: scientific evaluation and metrics
- scripts: reproducible command-line workflows
- configs: experiment configurations
- experiments: experiment-specific outputs
- models: trained research model artifacts
- reports: scientific reports
- tests: unit and integration tests

## 5. Classical Baselines

Before training an AI model, establish reproducible baselines using:

- Generalized Lomb–Scargle
- Keplerian fitting
- Appropriate false-alarm estimation
- Residual and noise diagnostics

RadVel and RVSearch are relevant research tools to evaluate.
Their scientific assumptions and limitations must be reviewed before use.

## 6. Research Milestones

### RV-01: Research foundation
Documentation, directory structure, data standards and reproducibility.

### RV-02: Dataset acquisition
Identify public datasets and establish provenance records.

### RV-03: Classical RV baseline
Implement and validate periodogram and orbital-fitting baselines
inside the independent research workspace.

### RV-04: Synthetic injection framework
Inject controlled planetary signals into real observational noise.

### RV-05: AI model development
Train and compare candidate models using controlled datasets.

### RV-06: Blind validation
Evaluate on independent targets not used during training or model selection.

### RV-07: Research evaluation
Document limitations, performance, false positives and reproducibility.

## 7. Production Boundary

This architecture is a research proposal.

No production API, database schema, user interface, Transit algorithm,
or existing production scientific pipeline should be modified as part
of these research milestones without separate approval.
