"""Workspace + upload handling. User-supplied filenames are NEVER used on disk."""
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from ..config import settings

ALLOWED_EXT = {".csv", ".fits", ".fit"}


def job_path(job_id: str) -> Path:
    root = Path(settings.jobs_root).resolve()
    uuid.UUID(job_id)  # raises unless it is a real UUID, so no separators or ".." can get through
    path = (root / job_id).resolve()
    if not path.is_relative_to(root) or path == root:  # defence in depth
        raise HTTPException(400, "Invalid workspace.")
    return path


def new_job_dir(job_id: str) -> Path:
    path = job_path(job_id)
    path.mkdir(parents=True, mode=0o700)
    return path


async def save_upload(file: UploadFile, dest: Path) -> str:
    if Path(file.filename or "").suffix.lower() not in ALLOWED_EXT:
        raise HTTPException(415, "Upload a .csv or .fits file.")
    head = await file.read(2880)
    if head.startswith(b"SIMPLE  ="):  # FITS magic bytes
        kind = "fits"
    elif head and b"\x00" not in head:
        kind = "csv"
    else:
        raise HTTPException(415, "File content is not valid CSV or FITS.")
    limit = settings.max_upload_mb * 1024 * 1024
    total = len(head)
    target = dest / f"input.{kind}"  # fixed server-side name
    with open(target, "wb") as out:
        out.write(head)
        while chunk := await file.read(1 << 20):
            total += len(chunk)
            if total > limit:
                out.close()
                shutil.rmtree(dest, ignore_errors=True)
                raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB.")
            out.write(chunk)
    return kind


def archive_input(job_dir: Path, user_id: int, job_id: str) -> None:
    if settings.storage_backend != "s3":
        return
    import boto3

    s3 = boto3.client("s3")
    for p in job_dir.glob("input.*"):
        s3.upload_file(str(p), settings.s3_bucket, f"uploads/{user_id}/{job_id}/{p.name}",
                       ExtraArgs={"ServerSideEncryption": "AES256"})
