# ExoAnalytica – Phase 2 Literature Review

**Project:** ExoAnalytica  
**Phase:** 2 – Research Gap Analysis and Planning  
**Work Package:** WP1 – Literature Review  
**Status:** Initial Literature Review  
**Date:** 2026-11-19

---

## 1. Introduction

ExoAnalytica aims to develop a multimodal AI-assisted system for exoplanet discovery, candidate vetting, and characterization.

The proposed research investigates three complementary observational methods:

1. Transit Photometry
2. Radial Velocity (RV)
3. Gravitational Microlensing

The purpose of this literature review is to understand existing scientific methods, identify technical challenges, and establish a research direction for ExoAnalytica.

This document represents an initial review, not a completed systematic literature review.

---

## 2. Transit Detection and AI-Based Vetting

### 2.1 ExoMiner (2021)

**Reference:** Valizadegan et al. (2021)

**Paper:** ExoMiner: A Highly Accurate and Explainable Deep Learning Classifier that Validates 301 New Exoplanets.

https://arxiv.org/abs/2111.10009

ExoMiner is a deep-learning-based system designed to classify transit signals and support the vetting of exoplanet candidates.

The research demonstrates the use of diagnostic information and a modular deep-learning architecture to distinguish planet candidates from false positives.

The authors reported validation of 301 exoplanets from the Kepler archive.

The paper also reported a recall of 93.6% at a fixed precision of 99% on its evaluated test set. These figures are specific to the paper's dataset and evaluation methodology and should not be treated as directly comparable to ExoAnalytica results.

**Research relevance to ExoAnalytica:**

- AI-assisted transit candidate classification.
- Diagnostic evidence for false-positive rejection.
- Model explainability.
- Candidate ranking and classification evaluation.
- Comparison of machine-learning approaches with conventional vetting.

### 2.2 ExoMiner++ (2025)

**Reference:** Valizadegan et al. (2025)

**Paper:** ExoMiner++: Enhanced Transit Classification and a New Vetting Catalog for 2-minute TESS Data.

The Astronomical Journal, 170(5), Article 287.

https://doi.org/10.3847/1538-3881/ae03a4

ExoMiner++ extends the ExoMiner approach for transit classification using 2-minute TESS observations.

The research incorporates additional diagnostic inputs, including:

- Periodogram information.
- Flux trends.
- Difference images.
- Unfolded flux.
- Spacecraft attitude-control information.

The study also uses multisource training, combining high-quality labelled Kepler data with TESS data.

The authors present a TESS vetting catalogue with classifications and confidence scores.

**Research relevance to ExoAnalytica:**

- Investigate the value of multiple diagnostic inputs.
- Evaluate cross-mission training and generalization.
- Improve false-positive discrimination.
- Investigate confidence scoring and candidate ranking.
- Study whether additional diagnostics can complement the existing BLS and CNN pipeline.

**Important limitation:**

ExoMiner and ExoMiner++ primarily address transit-signal classification and vetting. They do not, by themselves, establish the complete multimodal Transit + RV + Microlensing architecture proposed for ExoAnalytica.

---

## 3. Radial Velocity Research

### 3.1 Statistical Methods for Exoplanet Detection with Radial Velocities (2023)

**Reference:** Hara, N. C. and Ford, E. B. (2023).

**Journal:** Annual Review of Statistics and Its Application, Volume 10, pages 623–649.

https://doi.org/10.1146/annurev-statistics-033021-012225

Radial Velocity measurements detect the motion of a star caused by the gravitational influence of orbiting planets.

RV observations can provide information about:

- Planetary minimum mass.
- Orbital period.
- Orbital eccentricity.
- Planetary-system architecture.

The analysis is challenging because RV observations are unevenly sampled and contain correlated instrumental and astrophysical noise.

The review discusses statistical approaches to detection and parameter estimation, including the difficulties of exploring complex RV model spaces.

**Research topics for ExoAnalytica:**

1. Periodogram-based signal detection.
2. Keplerian orbital modelling.
3. Stellar activity and correlated-noise modelling.
4. Gaussian Process approaches.
5. Model comparison and uncertainty estimation.
6. Multi-planet signal analysis.

**Potential integration with Transit:**

For a transiting planet, the transit observation constrains orbital inclination.

Combining transit information with RV measurements can improve planetary mass characterization. RV measurements generally provide the quantity M_p sin(i), rather than an unconditional planetary mass.

This combination can also support planetary density estimation when reliable radius and mass measurements are available.

---

## 4. Gravitational Microlensing Research

### 4.1 Microlensing Surveys for Exoplanets (2012)

**Reference:** Gaudi, B. S. (2012).

**Journal:** Annual Review of Astronomy and Astrophysics, Volume 50, pages 411–453.

https://doi.org/10.1146/annurev-astro-081811-125518

Gravitational microlensing detects planets through the gravitational perturbation of light from a distant background source.

Unlike transit photometry and radial velocity, microlensing does not depend on directly detecting photons from the host star or planet.

The method is particularly useful for investigating planets beyond the snow line, wide-orbit planets, and potentially free-floating planets.

Important practical challenges include:

- Microlensing events are relatively rare.
- Events cannot generally be predicted in advance.
- Planetary anomalies may be short-lived.
- Host-star properties may be difficult to determine.
- Different physical models can produce degenerate solutions.

### 4.2 Microlensing Detection of Extrasolar Planets (2013)

**Reference:** Giannini, E. and Lunine, J. I. (2013).

**Journal:** Reports on Progress in Physics, Volume 76, Article 056901.

https://doi.org/10.1088/0034-4885/76/5/056901

This review discusses planetary microlensing and the recovery of physical properties from detailed light-curve analysis and supporting observations.

It highlights the potential of microlensing surveys to investigate planetary populations beyond the snow line.

**Important parameters for future ExoAnalytica research:**

- Einstein timescale (t_E).
- Impact parameter (u_0).
- Planet-to-star mass ratio (q).
- Projected separation (s).
- Finite-source parameter (rho).

**Research topics for ExoAnalytica:**

1. Microlensing light-curve modelling.
2. Planetary anomaly detection.
3. Binary-lens and planetary-lens modelling.
4. Parameter estimation and degeneracy analysis.
5. Uncertainty-aware classification.
6. Microlensing survey data integration.

---

### 4.3 Nancy Grace Roman Space Telescope and Microlensing

The Nancy Grace Roman Space Telescope is expected to provide a major space-based microlensing survey through its Galactic Bulge Time-Domain Survey (GBTDS).

The survey design includes:
- High-cadence F146 imaging at approximately 12.1-minute cadence during six high-cadence seasons.
- Lower-cadence monitoring during four middle seasons to retain sensitivity to longer-duration events.
- Additional photometric and grism-spectroscopic snapshots for stellar characterization.

The survey is designed to investigate planetary demographics in parameter-space regions complementary to transit and radial-velocity surveys, including wide-orbit and free-floating planets.

**Roman Microlensing Data Challenge 2026 (RMDC26):**

RMDC26 provides semi-realistic simulated Roman microlensing data for developing and evaluating analysis methods before and during the mission's science operations. Its published data documentation describes:
- Beginner tier: 188 simulated events and 9,230,048 photometric observations.
- Experienced tier: 2,087 simulated events and 103,281,456 observations, including astrometric measurements and more complex lens/source configurations.
- Separate machine-learning training resources containing 372,655 simulated events, with observation, metadata, and epoch tables.

The machine-learning observations table is approximately 172 GB. It should not be downloaded or loaded in full for the initial ExoAnalytica pilot.

**Research relevance to ExoAnalytica:**
1. Develop and test microlensing event modelling using Roman-like simulated photometry.
2. Investigate joint photometric and astrometric information using the Experienced tier.
3. Evaluate parameter recovery, uncertainty calibration, model degeneracies, and anomaly detection.
4. Test how analysis performance changes across simulated event complexity and observing conditions.
5. Prepare a reproducible workflow for future Roman observations.

**Important scientific distinction:** RMDC26 datasets are simulations, not observations collected by the Roman telescope. Results obtained from these datasets must be reported as simulation-based validation. They do not establish performance on real Roman observations.

As of 19 November 2026, NASA reports that Roman is in science commissioning. Actual GBTDS survey observations should be treated as a future validation source until suitable public survey data products are released. The first available observing window after commissioning is the planned start point for the GBTDS.

**Important modelling consideration:** Roman's astrometric microlensing measurements can provide information complementary to photometric light curves. The analysis must preserve the distinction between the background source star and the foreground lens/host system. Astrometric and photometric constraints should be combined only through an appropriate physical model.

## 5. Comparison of the Three Observational Methods

| Property | Transit | Radial Velocity | Microlensing |
|---|---|---|---|
| Primary observation | Stellar brightness | Stellar velocity | Gravitationally magnified brightness |
| Main signal | Periodic flux decrease | Doppler velocity variation | Microlensing light-curve anomaly |
| Important parameter | Planetary radius | Minimum mass | Mass ratio and projected separation |
| Main challenge | Noise and false positives | Stellar activity and correlated noise | Model degeneracies and rare events |
| Complementary value | Planet size and period | Planet mass and orbit | Different planetary populations |

These methods are complementary, but their observations are not automatically interchangeable.

A multimodal system must account for the physical meaning, observation time, uncertainty, and source identity of each measurement.

---

## 6. Initial Research Gap Hypothesis

### Proposed research direction

**Uncertainty-aware multimodal exoplanet candidate analysis and characterization.**

The proposed direction is to investigate a framework that can analyse Transit, Radial Velocity, and Gravitational Microlensing observations through dedicated scientific pipelines and combine compatible evidence when appropriate.

### Preliminary research questions

**RQ1:** How can independent exoplanet detection methods be represented in a common evidence framework?

**RQ2:** How can uncertainties from different observational methods be propagated during combined characterization?

**RQ3:** How can the system handle missing observations from one or more modalities?

**RQ4:** Can combined evidence improve the reliability of candidate characterization compared with modality-specific analysis?

**RQ5:** How can false-positive risks and model degeneracies be communicated to users?

### Novelty assessment

The existence of the individual methods and multimethod exoplanet studies is already established.

Therefore, the proposed combination of three modalities cannot yet be claimed as a novel contribution.

A systematic review of existing multimodal systems, publications, and software implementations is required before making a novelty claim.

---

## 7. Relevance to the Existing ExoAnalytica System

Phase 1 investigated the existing transit-processing pipeline using Kepler-63.

The Phase 1 validation report documented:

- Baseline BLS period comparison.
- Injection-recovery experiments.
- Existing-signal interference.
- Transit masking experiments.
- Injected-signal preservation.
- Transit-depth preservation diagnostics.

The Kepler-63 experiment showed that the baseline detected period was close to the reference period. However, injection recovery and transit-depth preservation also revealed limitations that require further investigation.

These findings are specific to the tested target and configurations. They are not sufficient to establish general performance across all Kepler or TESS targets.

### Initial improvement areas

1. Transit-depth preservation during preprocessing.
2. Weak transit-signal recovery.
3. BLS detection robustness.
4. False-positive vetting.
5. CNN classification and confidence evaluation.
6. Reproducible multi-target benchmarking.

No algorithm modifications are authorized by this literature review.

---

## 8. Research Limitations and Risks

The following limitations must be addressed during subsequent research:

- Different missions have different sampling cadences and noise properties.
- RV measurements can contain stellar activity and correlated noise.
- Microlensing parameters may be affected by degeneracies.
- A single planet may not have observations available in all three modalities.
- Cross-matching observations requires reliable source identification.
- Synthetic injection results do not automatically represent real-world detection performance.
- AI confidence scores require calibration and independent evaluation.
- Research novelty must be demonstrated through a systematic literature review.

---

## 9. Proposed Next Research Activities

### WP1 – Literature Review

- Read the original ExoMiner and ExoMiner++ papers.
- Review established RV detection and parameter-estimation methods.
- Review microlensing detection and characterization methods.
- Identify existing multimodal exoplanet research systems.

### WP2 – Research Gap Analysis

- Compare existing methods and systems.
- Identify limitations supported by published evidence.
- Define research questions and measurable objectives.
- Evaluate potential scientific contributions.

### WP3 – Dataset Strategy

- Identify suitable Kepler and TESS datasets.
- Investigate Gaia and HARPS RV data access.
- Investigate OGLE event-level data and the Roman Microlensing Data Challenge 2026 (RMDC26) simulated datasets.\n- Monitor the release of suitable public Roman GBTDS observations for later real-data validation.
- Define data-quality and cross-matching requirements.

### WP4 – Architecture Planning

- Design independent modality-specific pipelines.
- Define common candidate and evidence representations.
- Design uncertainty propagation and evidence integration.
- Establish validation and benchmarking criteria.

---

## 10. References

1. Valizadegan, H. et al. (2021). ExoMiner: A Highly Accurate and Explainable Deep Learning Classifier that Validates 301 New Exoplanets.  
   https://arxiv.org/abs/2111.10009

2. Valizadegan, H. et al. (2025). ExoMiner++: Enhanced Transit Classification and a New Vetting Catalog for 2-minute TESS Data. The Astronomical Journal, 170(5), Article 287.  
   https://doi.org/10.3847/1538-3881/ae03a4

3. Hara, N. C. and Ford, E. B. (2023). Statistical Methods for Exoplanet Detection with Radial Velocities. Annual Review of Statistics and Its Application, 10, 623–649.  
   https://doi.org/10.1146/annurev-statistics-033021-012225

4. Gaudi, B. S. (2012). Microlensing Surveys for Exoplanets. Annual Review of Astronomy and Astrophysics, 50, 411–453.  
   https://doi.org/10.1146/annurev-astro-081811-125518

5. Giannini, E. and Lunine, J. I. (2013). Microlensing Detection of Extrasolar Planets. Reports on Progress in Physics, 76, 056901.  
   https://doi.org/10.1088/0034-4885/76/5/056901

---

## 11. Document Status

**Phase:** 2  
**Work Package:** WP1 – Literature Review  
**Status:** Initial review prepared  
**Next milestone:** Expanded literature review, Roman simulation pilot assessment, and research gap refinement

This document is a research-planning artefact. It does not represent a completed algorithm design, implementation, or scientific validation.

No existing ExoAnalytica source code, scientific algorithm, API, database, or user interface has been modified as part of this document.
