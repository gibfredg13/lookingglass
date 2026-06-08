from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Analyst
from app.services.auth import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_db(request: Request) -> Generator[Session, None, None]:
    session_factory = request.app.state.session_factory
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def get_current_analyst(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Analyst:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    analyst_id = payload.get("sub")
    if analyst_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")

    stmt = select(Analyst).where(Analyst.id == int(analyst_id))
    analyst = db.scalar(stmt)
    if analyst is None or not analyst.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Analyst not found or inactive")
    return analyst


CurrentAnalyst = Annotated[Analyst, Depends(get_current_analyst)]
