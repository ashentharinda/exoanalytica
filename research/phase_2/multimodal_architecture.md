# ExoAnalytica - Phase 2
# Multimodal Architecture Planning

**Project:** ExoAnalytica
**Phase:** 2 - Research Planning
**Work Package:** WP4
**Document:** Multimodal Architecture Planning
**Status:** Proposed research architecture
**Date:** 2026-11-19

---

## 1. Purpose

This document proposes a modular architecture for ExoAnalytica.

The long-term research objective is to investigate an AI-assisted, uncertainty-aware exoplanet analysis framework integrating three observational methods:

1. Transit photometry
2. Radial velocity (RV)
3. Gravitational microlensing

These methods rely on different physical processes, observation formats, mathematical models, and detection limitations.

Therefore, the architecture must preserve method-specific scientific analysis while providing a common framework for evidence representation, association, uncertainty management, and reporting.

This document describes a proposed research architecture. It does not authorize modifications to the existing application, scientific algorithms, database schema, or UI.

## 2. Architectural Principles

The proposed system should follow these principles:

### 2.1 Scientific separation

Each detection method must have its own scientific analysis module.

Transit, RV, and microlensing observations must not be treated as interchangeable measurements.

### 2.2 Modular development

Each module should be independently testable and replaceable without requiring changes to unrelated scientific modules.

### 2.3 Evidence-based integration

The integration layer should combine scientifically justified evidence, not merely combine model scores.

### 2.4 Uncertainty awareness

Measurement uncertainty, parameter uncertainty, model uncertainty, and identification uncertainty must remain distinguishable.

### 2.5 Data provenance

Every result should be traceable to its original observations, source archive, processing configuration, and scientific model.

### 2.6 Missing-modality awareness

The absence of an observation from one detection method must not automatically be interpreted as negative evidence.

### 2.7 Reproducibility

The same input observations and documented processing configuration should allow independent reproduction of analysis results.

### 2.8 Scientific transparency

The system should report limitations and unresolved ambiguities rather than producing unsupported conclusions.

## 3. High-Level Architecture

The proposed architecture contains six principal layers.

1. Data Acquisition Layer
2. Data Validation and Normalization Layer
3. Method-Specific Scientific Analysis Layer
4. Evidence Integration and Association Layer
5. Planetary Characterization Layer
6. Reporting and Research Evaluation Layer

A supporting infrastructure layer will manage jobs, users, storage, provenance, and system security.

## 4. Layer 1 - Data Acquisition

### Purpose

Retrieve observations and relevant metadata from supported astronomical archives.

### Potential sources

**Transit:**
- NASA MAST
- Kepler
- TESS
- K2

**Radial Velocity:**
- ESO Science Archive
- HARPS
- Other suitable public RV archives

**Microlensing:**
- OGLE
- Published microlensing event datasets
- Roman Microlensing Data Challenge 2026 (RMDC26) simulated products\n- Future public Roman Galactic Bulge Time-Domain Survey (GBTDS) observations

**Reference information:**
- NASA Exoplanet Archive
- Stellar catalogues
- Published research catalogues

### Responsibilities

- Identify available observations.
- Retrieve original data products.
- Record archive identifiers.
- Record retrieval timestamps.
- Preserve source metadata.
- Verify file integrity.
- Respect archive access and redistribution conditions.

### Design requirement

Data acquisition must remain separate from scientific interpretation.

A successful download does not imply that the observation is scientifically suitable.

## 5. Layer 2 - Data Validation and Normalization

### Purpose

Check the integrity and suitability of observations before scientific processing.

### Responsibilities

- File format validation.
- Missing-value detection.
- Observation quality checks.
- Unit verification.
- Time-system verification.
- Uncertainty availability checks.
- Quality-flag preservation.
- Data provenance recording.

### Time handling

Different archives may use different time references and scales.

The system must preserve the original time representation and document any conversions.

### Unit handling

Original units must remain recorded.

Normalized values must include explicit conversion information.

### Quality handling

Filtering decisions must be reproducible.

Rejected observations should have documented reasons.

### Output

A validated observation package containing:

- Original data reference
- Normalized data reference
- Quality information
- Measurement uncertainties
- Metadata
- Processing history

## 6. Layer 3 - Method-Specific Scientific Analysis

This layer contains three independent scientific modules.

### 6.1 Transit Analysis Module

**Input:**
- Photometric light curves
- Observation times
- Flux measurements
- Flux uncertainties
- Quality flags
- Stellar parameters where available

**Potential processing:**
- Light-curve preparation
- Systematics handling
- Period search
- Transit detection
- Candidate vetting
- Transit modelling
- Parameter estimation
- Injection-recovery validation

**Potential scientific outputs:**
- Candidate orbital period
- Transit epoch
- Transit duration
- Transit depth
- Planet-to-star radius ratio
- Planet radius when stellar information is sufficient
- Detection statistics
- Parameter uncertainties

**Existing project context:**

ExoAnalytica already contains a Kepler-oriented transit analysis workflow, including preprocessing, BLS-related analysis, vetting, and injection-recovery functionality.

The existing implementation is the starting point for this module.

Its scientific behaviour must not be changed solely to fit this proposed architecture.

Any future modifications require separate authorization and validation.

### 6.2 Radial Velocity Analysis Module

**Input:**
- RV observation times
- Radial velocity measurements
- Measurement uncertainties
- Instrument metadata
- Stellar information where available

**Potential processing:**
- Observation quality assessment
- Time-series inspection
- Period analysis
- Keplerian orbital modelling
- Instrumental offset modelling
- Stellar activity assessment
- Correlated-noise modelling
- Model comparison
- Parameter uncertainty estimation

**Potential scientific outputs:**
- Orbital period
- RV semi-amplitude
- Eccentricity
- Argument of periastron
- Time of periastron passage
- Minimum mass (Mp sin i) where justified
- Posterior distributions
- Model comparison results

**Scientific limitation:**

RV measurements generally constrain Mp sin i rather than the true planetary mass unless additional information is available.

Stellar activity and correlated signals may produce apparent periodic RV variations.

The module must account for these limitations.

### 6.3 Gravitational Microlensing Analysis Module

**Input:**
- Event observation times
- Photometric measurements
- Photometric uncertainties
- Event identifiers
- Lens-model information where available

**Potential processing:**
- Event data validation
- Baseline light-curve inspection
- Magnification modelling
- Planetary perturbation analysis
- Lens-model comparison
- Alternative-solution analysis
- Posterior uncertainty analysis

**Potential scientific outputs:**
- Event classification
- Einstein timescale
- Impact parameter
- Mass-ratio constraints
- Projected separation constraints
- Alternative lens solutions
- Posterior distributions
- Event interpretation confidence

**Scientific limitation:**

Microlensing parameters can be degenerate.

Lens mass, distance, and physical planetary properties may require additional information.

The module must preserve alternative solutions and avoid reporting unsupported physical parameters.



**Roman-specific research inputs:**

The microlensing module should be prepared to analyse Roman-like simulated data from RMDC26 and, later, suitable public GBTDS observations.

Potential input categories include:
- High-cadence photometric time series.
- Photometric measurement uncertainties and quality information.
- Astrometric time-series measurements and their uncertainty information where available.
- Event identifiers and simulation/observation provenance.
- Lens/source configuration metadata and reference or truth parameters for simulated validation.

The Roman GBTDS design includes high-cadence F146 observations at approximately 12.1-minute cadence during six seasons, lower-cadence monitoring during four middle seasons, and additional photometric and grism-spectroscopic snapshots. These planned survey characteristics should guide test design, but the pipeline must use the actual cadence and metadata present in each data product rather than hard-coding an assumed schedule.

**Roman-specific processing considerations:**
- Validate photometric and astrometric measurements independently before joint modelling.
- Preserve coordinate reference frames, time standards, units, and astrometric uncertainty/covariance information.
- Distinguish the background source star from the foreground lens and planetary host.
- Preserve alternative lens solutions and posterior distributions.
- Compare photometry-only results with joint photometric/astrometric results where the data support both.
- Record whether each result comes from simulation or actual observation.

RMDC26 simulations can support prototype development and recovery tests against supplied simulation parameters. Such tests are simulation-based validation only. They do not establish performance on real Roman observations.

Roman grism snapshots may provide stellar characterization information, but they must not be treated as equivalent to a dedicated, high-precision exoplanet RV time series without a separate scientific suitability assessment.

## 7. Layer 4 - Evidence Integration and Association

### Purpose

Connect outputs from independent scientific modules without erasing their physical meaning.

This layer is central to the proposed research direction.

### 7.1 Common evidence representation

Each scientific module should produce a documented evidence record.

A conceptual record may contain:

- Evidence identifier
- Detection method
- Target identifier
- Observation identifier
- Source archive
- Model identifier
- Measured or inferred parameters
- Parameter units
- Uncertainty representation
- Model assumptions
- Quality information
- Provenance
- Validation status

The exact schema will be defined during implementation planning.

### 7.2 Cross-identification

The system must distinguish:

- Observation identity
- Target identity
- Host-star identity
- Planet identity
- Planetary-system identity
- Microlensing-event identity

A shared star identifier does not prove that observations refer to the same planet.

### 7.3 Association states

Proposed association states:

1. Confirmed association
2. Probable association
3. Possible association
4. Unresolved association
5. No verified association

Association decisions must include their supporting evidence.

### 7.4 Two integration scenarios

**Scenario A - Same-system integration**

Multiple observational methods provide evidence for the same planetary system.

Integration is allowed only when the association is independently supported.

For example, transit and RV measurements associated with a verified transiting planet may provide complementary constraints on its radius and mass.

**Scenario B - Independent candidate analysis**

Different detection methods identify different candidates or populations.

These candidates can be analysed and compared without assuming they are the same object.

Microlensing events must not be artificially linked to unrelated transit or RV targets.

### 7.5 Evidence fusion

Potential future approaches include:

- Bayesian evidence integration
- Hierarchical statistical models
- Joint posterior analysis
- Model comparison
- Probabilistic association
- Uncertainty propagation

The selected approach must depend on the scientific problem and available data.

A simple average of confidence scores is not a scientifically valid general-purpose fusion strategy.

## 8. Layer 5 - Planetary Characterization

### Purpose

Produce physically interpretable planetary parameters supported by the available observations.

Potential outputs:

- Planet radius
- Planet mass
- Orbital period
- Orbital eccentricity
- Planet density
- Orbital inclination
- Host-star parameters
- Parameter uncertainties

### Scientific requirements

1. Do not infer a parameter when the observations do not constrain it.
2. Distinguish measured values from derived values.
3. Preserve uncertainty distributions where available.
4. Record assumptions used in derived calculations.
5. Distinguish Mp sin i from true planetary mass.
6. Preserve alternative microlensing solutions.
7. Avoid combining incompatible posterior distributions without a justified statistical model.

The system must indicate which observational methods support each reported parameter.

## 9. Layer 6 - Reporting and Research Evaluation

### Purpose

Generate transparent scientific reports for users and researchers.

Potential report sections:

- Target and candidate identification
- Available observations
- Detection methods used
- Method-specific results
- Evidence integration summary
- Parameter estimates and uncertainties
- Model assumptions
- Data provenance
- Validation results
- Unresolved ambiguities
- Scientific limitations

### Candidate status

The reporting layer should distinguish:

- Candidate
- Validated candidate
- Confirmed planet
- False positive
- Unresolved classification

These statuses must follow documented scientific criteria.

A high machine-learning score alone must not automatically change a candidate into a confirmed planet.

### Human review

Important or ambiguous scientific conclusions should support expert review.

The framework should make it possible to inspect the evidence behind a reported conclusion.

## 10. Supporting Infrastructure

### 10.1 Backend orchestration

The existing FastAPI application may continue to provide job submission, analysis status, authentication, and result retrieval.

Future scientific modules should be integrated through controlled interfaces.

### 10.2 Job execution

Long-running scientific analyses should remain isolated from API request handling.

Existing worker resource restrictions should be preserved unless a separately approved review justifies a change.

### 10.3 Storage

Potential storage categories:

- Original observation references
- Validated observation data
- Intermediate scientific products
- Analysis results
- Model outputs
- Provenance metadata
- Research reports

Large astronomical files should not automatically be stored in Git.

### 10.4 Reproducibility

Each analysis should record:

- Software version
- Model version
- Configuration
- Input dataset identifiers
- Processing parameters
- Random seeds where applicable
- Execution timestamp
- Output checksums where appropriate

### 10.5 Security

The existing authentication, upload limits, worker isolation, and resource constraints should remain part of the system design.

Future data ingestion must not introduce uncontrolled file execution or unrestricted resource consumption.

## 11. Proposed Logical Data Flow

1. User or scheduled process identifies an astronomical target or event.
2. Data acquisition retrieves available observations.
3. Data validation checks integrity and scientific suitability.
4. Observations are routed to the appropriate method-specific module.
5. Each module produces method-specific evidence.
6. Evidence records are stored with provenance and uncertainty.
7. The association layer evaluates whether observations refer to the same target or planetary system.
8. The integration layer evaluates scientifically justified combinations.
9. Characterization produces supported physical parameters.
10. Reporting presents results, limitations, and evidence sources.

Not every analysis must pass through all three detection modules.

The framework must support individual-method analysis when only one type of observation is available.

## 12. Proposed Software Module Boundaries

The following names are conceptual architecture boundaries, not instructions to create or rename files immediately.

- data_acquisition
- data_validation
- transit_analysis
- radial_velocity_analysis
- microlensing_analysis
- evidence_models
- candidate_association
- uncertainty_analysis
- characterization
- scientific_reporting
- provenance
- job_orchestration

The existing repository structure must be inspected before mapping these concepts to actual code.

No folder restructuring is authorized by this planning document.

## 13. Validation Strategy

### 13.1 Module-level validation

Each detection method must be validated independently.

Transit:
- Known reference targets
- Published ephemerides
- Injection-recovery experiments
- False-positive tests

RV:
- Published planetary systems
- Known orbital solutions
- Residual analysis
- Parameter uncertainty comparison

Microlensing:
- Published events
- Known model solutions
- Alternative solution comparison
- Posterior consistency

### 13.2 Integration validation

Test:
- Verified same-system associations
- Unverified associations
- Missing modalities
- Conflicting observations
- Incompatible units
- Incompatible time references
- Uncertain stellar parameters
- Alternative physical solutions

### 13.3 Roman microlensing simulation and future observation validation\n\nFor RMDC26-based prototype evaluation:\n- Record the exact tier, release, event identifiers, and simulation provenance.\n- Use event-level partitions to prevent observations from the same event leaking across development and evaluation sets.\n- Compare recovered parameters and posterior coverage with the supplied simulation truth where appropriate.\n- Evaluate photometric-only and photometric-plus-astrometric analyses separately.\n- Account for the Experienced tier's selection for likely anomalous events; do not interpret it as a representative survey population.\n- Keep the large machine-learning observations table out of the initial full-download workflow; use selected or remotely queried subsets.\n\nFor future actual Roman observations, repeat validation using released observational products and their calibration, quality, and provenance information. Simulation-based performance must not be reported as real-observation validation.\n\n### 13.4 Uncertainty validation

Evaluate:
- Parameter coverage
- Posterior calibration
- Sensitivity to assumptions
- Robustness to missing data
- Model comparison reliability

### 13.4 Independent evaluation

Final performance evaluation should use independent data or targets not used for model selection and tuning.

Avoid data leakage between training, validation, and test partitions.

## 14. Major Architectural Risks

1. Treating unrelated observations as the same planetary system.
2. Combining model scores without a valid statistical interpretation.
3. Losing measurement uncertainties during normalization.
4. Treating missing modalities as negative evidence.
5. Ignoring survey-specific selection effects.
6. Reporting unsupported planetary parameters.
7. Ignoring microlensing degeneracies.
8. Overcomplicating the existing transit implementation.
9. Introducing unnecessary infrastructure before validating scientific requirements.
10. Claiming multimodal novelty without sufficiently reviewing existing work.

## 15. Proposed Development Order

The proposed future implementation sequence is:

**Stage 1 - Existing transit module assessment**

Document existing interfaces, input requirements, outputs, and scientific validation status.

**Stage 2 - Common evidence representation**

Design a stable, provenance-aware data contract.

**Stage 3 - RV research prototype**

Select a small verified dataset and evaluate an independent RV analysis approach.

**Stage 4 - Microlensing research prototype**

Select documented OGLE events and evaluate event-level modelling.

**Stage 5 - Association layer**

Develop and test candidate and planetary-system identification.

**Stage 6 - Uncertainty-aware integration**

Evaluate suitable statistical integration methods.

**Stage 7 - Scientific reporting**

Generate transparent reports and independent validation results.

**Stage 8 - Controlled application integration**

Only after scientific prototypes are validated and implementation changes are explicitly approved.

This is a proposed sequence, not an authorization to begin implementation.

## 16. Proposed Research Contributions

Potential contributions to investigate:

1. A modular framework for physically distinct exoplanet detection methods.
2. Provenance-aware evidence representation across heterogeneous observations.
3. Uncertainty-aware analysis with missing observational modalities.
4. Reliable cross-method candidate association.
5. Transparent planetary characterization with explicit evidence limitations.
6. Evaluation of method-specific selection effects within a common research workflow.

These are potential contributions, not established novel contributions.

Their novelty must be assessed against existing publications and software.

## 17. Final Architectural Position

ExoAnalytica should be investigated as a modular, uncertainty-aware scientific analysis framework rather than a single universal classifier.

Transit, RV, and microlensing modules should retain their individual physical models and scientific validation procedures.

A shared evidence layer should connect their outputs only when scientifically justified.

The framework should support both same-system evidence integration and independent candidate analysis.

Scientific traceability, uncertainty, data provenance, and transparent limitations are essential design requirements.

## 18. Document Status

**Phase:** 2 - Research Planning

**Work package:** WP4 - Multimodal Architecture Planning

**Status:** Proposed architecture drafted.

**Existing application changes:** None authorized.

**Scientific algorithm changes:** None authorized.

**UI changes:** None authorized.

**Next action:** Consolidate the Phase 2 research plan, including an OGLE archival pilot, an RMDC26 simulation pilot, and a separate future validation plan for actual Roman GBTDS observations.

---

End of document.
