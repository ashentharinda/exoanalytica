from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..limits import limiter
from ..models import User
from ..schemas import Credentials
from ..security import hash_pw, make_token, verify_pw

router = APIRouter(prefix="/auth", tags=["auth"])
_DUMMY = hash_pw("dummy-password")  # equalises timing when the email is unknown


@router.post("/register", status_code=201)
@limiter.limit("5/minute")
def register(request: Request, body: Credentials, db: Session = Depends(get_db)):
    user = User(email=body.email.lower(), password_hash=hash_pw(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "That email is already registered.")
    return {"access_token": make_token(user.id)}


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, body: Credentials, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    ok = verify_pw(body.password, user.password_hash if user else _DUMMY)
    if not user or not ok:
        raise HTTPException(401, "Email or password is incorrect.")
    return {"access_token": make_token(user.id)}
