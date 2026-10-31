import datetime as dt

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text

from .db import Base


def now():
    return dt.datetime.now(dt.timezone.utc)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(254), unique=True, nullable=False, index=True)
    password_hash = Column(String(100), nullable=False)
    created = Column(DateTime(timezone=True), default=now)


class Job(Base):
    __tablename__ = "jobs"
    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    status = Column(String(12), default="pending")  # pending|running|done|failed
    source = Column(String(8), nullable=False)  # upload|fetch
    target = Column(String(32))
    stellar = Column(JSON)
    result = Column(JSON)
    error = Column(Text)
    created = Column(DateTime(timezone=True), default=now)
