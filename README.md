# ExoAnalytica

**ExoAnalytica** is an independent research and software development project focused on AI-assisted exoplanet discovery, signal vetting, and planetary characterization.

The long-term research vision is to develop a multi-method system combining three major exoplanet detection approaches:

- **Transit Photometry** — Analysis of stellar light curves from missions such as NASA Kepler and TESS.
- **Radial Velocity (RV)** — Analysis of stellar radial velocity observations, including data from the ESO HARPS archive.
- **Gravitational Microlensing** — Future research using suitable microlensing observations, including OGLE data and potential observations from NASA's Roman Space Telescope mission.

The project emphasizes scientific transparency, observational data provenance, reproducibility, responsible AI development, and open research practices.

## Research Scope and Development Status

### 1. Transit Photometry

The existing ExoAnalytica application provides a transit-analysis workflow using Kepler and TESS light-curve data.

Current capabilities include:

- Light-curve upload or target-based data retrieval.
- Light-curve preprocessing.
- Box Least Squares (BLS) period search.
- CNN-based transit signal screening.
- Candidate vetting and planetary parameter estimation.

**Planned research development:**

The existing transit CNN is intended to be retrained using appropriately labelled real astronomical observations from Kepler and TESS.

This retraining is planned after the current RV model research and training activities. Until real-data retraining and independent evaluation are completed, existing model scores should be treated as screening outputs rather than confirmed planetary detections.

### 2. Radial Velocity Research

The RV research track focuses on developing AI-assisted methods for analysing stellar radial velocity observations.

Research activities include:

- Investigating astronomical RV data sources, including ESO HARPS.
- Observation-level data provenance and archive cross-matching.
- Data preparation and quality assessment.
- Development and evaluation of RV machine-learning approaches.
- Known-planet validation and independent benchmarking research.

The HARPS research includes observation-level provenance investigations. Provenance matching alone does not establish independent confirmation of a planetary signal.

The RV model research and training activities are ongoing. Research results should be interpreted according to their documented validation status.

### 3. Gravitational Microlensing

Gravitational microlensing is a planned research direction within the broader ExoAnalytica architecture.

Potential observational resources include:

- OGLE microlensing observations.
- Future suitable observations from NASA's Nancy Grace Roman Space Telescope.

Microlensing data integration, model development, and scientific validation remain future research activities.

## Research Development Roadmap

| Stage | Research activity | Status |
|---|---|---|
| 1 | Existing transit-analysis application | Implemented baseline |
| 2 | RV data research and provenance investigations | Ongoing |
| 3 | RV AI model development, training and evaluation | Ongoing |
| 4 | Transit model retraining using real Kepler/TESS observations | Planned |
| 5 | Microlensing data research and model development | Future |
| 6 | Multi-method integration and evaluation | Long-term objective |

These stages describe the research roadmap, not a claim that every method is already operational.

## Application Architecture

| Layer | Location | Description |
|---|---|---|
| Presentation | `frontend/` | Static UI and Plotly visualizations, served by nginx |
| API | `backend/app/routers/` | FastAPI, JWT authentication, Pydantic schemas and rate limiting |
| Business logic / ML | `backend/app/services/` | Preprocessing, BLS, CNN, physics calculations and worker execution |
| Application database | PostgreSQL | Users, jobs and results |
| Optional storage | `backend/app/services/storage.py` | S3-compatible archive storage |

The current application architecture primarily supports the transit-analysis workflow. The RV and microlensing research tracks are developed as part of the broader research project and should not be assumed to be fully integrated into the application.

## Data Sources and Research Data Management

Potential and investigated astronomical data resources include:

| Research method | Data resources |
|---|---|
| Transit | NASA Kepler and TESS through MAST |
| Radial Velocity | ESO HARPS archive and other verified RV resources |
| Microlensing | OGLE and future suitable NASA Roman observations |

Data availability and actual project acquisition status are documented separately.

Research data management follows an evolving FAIR-oriented approach:

- **Findable:** Structured metadata and source identification.
- **Accessible:** Documentation of archive locations and access conditions.
- **Interoperable:** Consistent units, timestamps and metadata.
- **Reusable:** Provenance, processing history and validation records.

See [DATA_AVAILABILITY.md](DATA_AVAILABILITY.md) and [OSDMP.md](OSDMP.md) for further information.

## Security Map

- **Path traversal:** User filenames are never used. Jobs live in `/data/jobs/<uuid4>/`, resolved and checked with `is_relative_to`; uploads are saved as `input.csv|fits`. Content is sniffed (FITS magic bytes / no NULs), size-capped while streaming.
- **Validation:** Pydantic models and bounded form fields; NASA targets must match `^(TIC|KIC|EPIC) ?\d{1,10}$`.
- **Isolation:** Analysis runs in a child process with CPU/memory/file-size rlimits, a timeout, a stripped environment (no secrets), and its own single-use directory. Containers run non-root, read-only, all capabilities dropped.
- **Auth/limits:** bcrypt passwords, pinned-algorithm JWTs (60 min), per-IP rate limits (5/min register, 10/min login and analyses), max 3 active jobs per user, ownership checks on every job lookup.

## Scientific Limitations and Responsible Interpretation

- The baseline transit CNN is trained on synthetic transits. Its scores are screening outputs, not confirmed detections.
- Real-data retraining and appropriate independent evaluation are required before making stronger claims about real-world detection performance.
- Period search uses BLS (0.5–40 days). Aliases (half/double period) and eclipsing binaries can produce misleading candidates; odd/even and secondary-eclipse checks are important.
- Planetary mass is estimated using an empirical mass-radius relation (Chen & Kipping 2017), so derived gravity and density are estimates.
- The habitable-zone calculation uses solar-type flux limits without a stellar effective-temperature correction.
- RV provenance matching is not equivalent to independent planetary confirmation.
- Planned microlensing research must undergo its own data validation and scientific evaluation.

Scientific outputs should be interpreted in the context of the method, input data, model limitations, and documented validation status.

## Run Locally

```bash
cp .env.example .env
# Set POSTGRES_PASSWORD and JWT_SECRET before starting.

docker compose up --build
```

Open http://localhost:8080.

API documentation may be available through the configured API service and deployment settings.

## Cloud Deployment

- **Render / Cloud Run:** Deploy `backend` and `frontend` as separate services; point nginx `proxy_pass` at the API's internal URL. Use managed PostgreSQL via `DATABASE_URL`, and platform secret management instead of `.env`.
- **AWS ECS:** Use separate API and web tasks, RDS for PostgreSQL, and `STORAGE_BACKEND=s3` with a task role. Put an Application Load Balancer and WAF in front for TLS and additional rate limiting.

Deployment configuration should be reviewed against the actual target environment before production use.

## Open Science, Licensing and Citation

ExoAnalytica adopts open-science-oriented documentation and reproducibility practices.

Project documentation includes:

- [Open Science and Data Management Plan](OSDMP.md)
- [Data Availability Statement](DATA_AVAILABILITY.md)
- [Software Citation](CITATION.cff)
- [Contribution Guidelines](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security Policy](SECURITY.md)

The software is distributed under the **Apache License 2.0**. See [LICENSE](LICENSE).

The software license does not automatically apply to third-party astronomical observations, archives, catalogues, or external datasets. Their respective access conditions, attribution requirements, and reuse terms must be followed.

A public research software release and DOI are planned for a later stage of project development.

## Contributing

Contributions are welcome in accordance with the project's scientific integrity, data provenance, reproducibility, and contribution guidelines.

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Project Repository

Source code and research documentation:

https://github.com/ashentharinda/exoanalytica
