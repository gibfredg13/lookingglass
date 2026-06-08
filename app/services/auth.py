"""Authentication service layer."""
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Analyst


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))


def create_access_token(data: dict[str, str | int], expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode["exp"] = int(expire.timestamp())
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict[str, str | int] | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None


def authenticate_analyst(db: Session, email: str, password: str) -> Analyst | None:
    stmt = select(Analyst).where(Analyst.email == email)
    analyst = db.scalar(stmt)
    if analyst is None or not verify_password(password, analyst.hashed_password):
        return None
    return analyst


def get_analyst_by_email(db: Session, email: str) -> Analyst | None:
    stmt = select(Analyst).where(Analyst.email == email)
    return db.scalar(stmt)


def create_analyst(db: Session, email: str, password: str, full_name: str, role: str = "analyst") -> Analyst:
    hashed = hash_password(password)
    analyst = Analyst(email=email, hashed_password=hashed, full_name=full_name, role=role)
    db.add(analyst)
    db.commit()
    db.refresh(analyst)
    return analyst



