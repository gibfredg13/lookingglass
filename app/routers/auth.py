from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.routers.dependencies import CurrentAnalyst, get_db
from app.schemas import AnalystCreate, AnalystRead, Token
from app.services.auth import authenticate_analyst, create_analyst, create_access_token, get_analyst_by_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AnalystRead, status_code=status.HTTP_201_CREATED)
def register(payload: AnalystCreate, db: Annotated[Session, Depends(get_db)]) -> AnalystRead:
    if get_analyst_by_email(db, payload.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    analyst = create_analyst(db, payload.email, payload.password, payload.full_name, payload.role)
    return AnalystRead.model_validate(analyst)


@router.post("/login", response_model=Token)
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[Session, Depends(get_db)]) -> Token:
    analyst = authenticate_analyst(db, form_data.username, form_data.password)
    if analyst is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": str(analyst.id)})
    return Token(access_token=token)


@router.get("/me", response_model=AnalystRead)
def me(analyst: CurrentAnalyst) -> AnalystRead:
    return AnalystRead.model_validate(analyst)

