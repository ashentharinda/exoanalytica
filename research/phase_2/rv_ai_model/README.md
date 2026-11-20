# ExoAnalytica RV AI Model

## Objective
Develop an independent, research-grade AI-assisted
Radial Velocity exoplanet detection system.

## Scientific workflow
1. RV data acquisition and validation
2. Time-series feature extraction
3. Period detection and candidate generation
4. Keplerian orbital modelling
5. Stellar activity and noise diagnostics
6. Machine-learning classification
7. Injection-recovery and independent validation

## Research principles
- Preserve original observations.
- Track units, uncertainties and provenance.
- Separate training, validation and test targets.
- Prevent target-level data leakage.
- Benchmark against established scientific methods.
- Never treat an ML score as planetary confirmation.

## Development policy
This workspace is independent of the production
Transit pipeline. No production UI, API or scientific
algorithm changes are authorized by this scaffold.
