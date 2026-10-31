import json
import shutil
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..db import SessionLocal, get_db
from ..limits import limiter
from ..models import Job, User
from ..schemas import FetchRequest, Stellar
from ..security import current_user
from ..services import storage
from ..services.runner import run_worker

router = APIRouter(prefix="/analysis", tags=["analysis"])


def _out(j: Job, full: bool = False) -> dict:
    d = {"id": j.id, "status": j.status, "source": j.source, "target": j.target,
         "created": j.created.isoformat(),
         "score": ((j.result or {}).get("detection") or {}).get("score")}
    if full:
        d.update(result=j.result, error=j.error)
    return d


def _check_capacity(db: Session, user: User):
    active = db.query(Job).filter(Job.user_id == user.id, Job.status.in_(["pending", "running"])).count()
    if active >= settings.max_active_jobs_per_user:
        raise HTTPException(429, "You already have analyses running. Wait for one to finish.")


def process_job(job_id: str):
    db = SessionLocal()
    job_dir = storage.job_path(job_id)
    job = db.get(Job, job_id)
    try:
        job.status = "running"
        db.commit()
        outcome = run_worker(job_dir)
        if "error" in outcome:
            job.status, job.error = "failed", outcome["error"]
        else:
            job.status, job.result = "done", outcome
        storage.archive_input(job_dir, job.user_id, job_id)
    except Exception:
        job.status, job.error = "failed", "Analysis failed unexpectedly."
    finally:
        db.commit()
        db.close()
        shutil.rmtree(job_dir, ignore_errors=True)  # workspaces are single-use


@router.post("/upload", status_code=202)
@limiter.limit("10/minute")
async def upload(request: Request, bg: BackgroundTasks, file: UploadFile = File(...),
                 radius_rsun: Optional[float] = Form(None, gt=0.08, le=100),
                 mass_msun: Optional[float] = Form(None, gt=0.08, le=100),
                 teff_k: Optional[float] = Form(None, ge=2300, le=50000),
                 injection: bool = Form(False),
                 user: User = Depends(current_user), db: Session = Depends(get_db)):
    _check_capacity(db, user)
    job_id = str(uuid.uuid4())
    job_dir = storage.new_job_dir(job_id)
    kind = await storage.save_upload(file, job_dir)
    stellar = Stellar(radius_rsun=radius_rsun, mass_msun=mass_msun, teff_k=teff_k).model_dump()
    (job_dir / "spec.json").write_text(json.dumps({"source": "upload", "kind": kind, "stellar": stellar, "injection": injection}))
    db.add(Job(id=job_id, user_id=user.id, source="upload", stellar=stellar))
    db.commit()
    bg.add_task(process_job, job_id)
    return {"id": job_id, "status": "pending"}


@router.post("/fetch", status_code=202)
@limiter.limit("10/minute")
def fetch(request: Request, body: FetchRequest, bg: BackgroundTasks,
          user: User = Depends(current_user), db: Session = Depends(get_db)):
    _check_capacity(db, user)
    job_id = str(uuid.uuid4())
    job_dir = storage.new_job_dir(job_id)
    stellar = body.stellar.model_dump()
    (job_dir / "spec.json").write_text(json.dumps(
        {"source": "fetch", "target": body.target, "mission": body.mission, "stellar": stellar, "injection": body.injection}))
    db.add(Job(id=job_id, user_id=user.id, source="fetch", target=body.target, stellar=stellar))
    db.commit()
    bg.add_task(process_job, job_id)
    return {"id": job_id, "status": "pending"}


@router.get("")
def list_jobs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(Job).filter(Job.user_id == user.id).order_by(Job.created.desc()).limit(25).all()
    return [_out(j) for j in rows]


@router.get("/{job_id}")
def get_job(job_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == str(job_id), Job.user_id == user.id).first()
    if not job:
        raise HTTPException(404, "Analysis not found.")
    return _out(job, full=True)