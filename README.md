# ExoAnalytica

Upload or fetch a TESS/Kepler light curve, detect transit signals with a CNN, and estimate the planet's radius, mass, density, gravity, equilibrium temperature and habitable-zone status.

## Run locally
```bash
cp .env.example .env          # set POSTGRES_PASSWORD (hex) and JWT_SECRET (openssl rand -hex 32)
docker compose up --build     # first build trains the baseline model (~1-2 min)
```
Open http://localhost:8080. API docs: `docker compose exec api python -c "print('see /docs via port-forward')"` or publish port 8000 temporarily.

## Layers
| Layer | Where |
|---|---|
| Presentation | `frontend/` static UI + Plotly, served by unprivileged nginx |
| API | `backend/app/routers`, `security.py`, `schemas.py` (FastAPI, JWT, Pydantic, slowapi) |
| Business logic / ML | `services/preprocess.py` (clean, BLS, fold), `model.py` (CNN), `physics.py`, `worker.py` |
| Data | PostgreSQL (users, jobs, results); optional S3 archive in `services/storage.py` |

## Security map
- **Path traversal**: user filenames are never used. Jobs live in `/data/jobs/<uuid4>/`, resolved and checked with `is_relative_to`; uploads are saved as `input.csv|fits`. Content is sniffed (FITS magic bytes / no NULs), size-capped while streaming.
- **Validation**: Pydantic models and bounded form fields; NASA targets must match `^(TIC|KIC|EPIC) ?\d{1,10}$`.
- **Isolation**: analysis runs in a child process with CPU/memory/file-size rlimits, a timeout, a stripped environment (no secrets), and its own single-use directory. Containers run non-root, read-only, all capabilities dropped.
- **Auth/limits**: bcrypt passwords, pinned-algorithm JWTs (60 min), per-IP rate limits (5/min register, 10/min login and analyses), max 3 active jobs per user, ownership checks on every job lookup.

## Honest limitations
- The baseline CNN is trained on **synthetic** transits so the pipeline runs end to end. For real detections, retrain `ExoCNN` on labelled Kepler DR25 / TESS TOI views (same two-view input) and mount the weights at `MODEL_PATH`. Until then, treat scores as screening only.
- Period search is BLS (0.5-40 d). Aliases (half/double period) and eclipsing binaries can fool it; vet candidates with odd/even and secondary-eclipse checks.
- Mass comes from an empirical mass-radius relation (Chen & Kipping 2017), so g and density are estimates. Habitable zone uses solar-type flux limits without a Teff correction.
- The worker's rlimit sandbox is process-level. For hostile multi-tenant use, run the worker as a separate container or Cloud Run Job per analysis, with egress limited to MAST.
- Schema is created on startup; add Alembic before production changes. Job workspaces are deleted after each run.

## Cloud deployment
- **Render / Cloud Run**: deploy `backend` and `frontend` as two services; point nginx `proxy_pass` at the API's internal URL. Use managed Postgres (Cloud SQL / RDS) via `DATABASE_URL`, and secrets from the platform's secret manager instead of `.env`.
- **AWS ECS**: one task with `api`, one with `web`, RDS for Postgres, `STORAGE_BACKEND=s3` with a task role. Put ALB + WAF in front for TLS and extra rate limiting.
