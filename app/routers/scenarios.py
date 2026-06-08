from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Scenario
from app.routers.dependencies import CurrentAnalyst, get_db
from app.schemas import ScenarioCloneRequest, ScenarioCreate, ScenarioRead

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.post("", response_model=ScenarioRead, status_code=status.HTTP_201_CREATED)
def create_scenario(
    payload: ScenarioCreate,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
) -> ScenarioRead:
    scenario = Scenario(
        name=payload.name,
        case_type=payload.case_type,
        triggers=payload.triggers,
        impacts=payload.impacts,
        time_horizon_hours=payload.time_horizon_hours,
        probability=payload.probability,
        is_template=payload.is_template,
        template_id=payload.template_id,
        owner_id=analyst.id,
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return ScenarioRead.model_validate(scenario)


@router.get("/templates", response_model=list[ScenarioRead])
def list_templates(
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
    case_type: str | None = None,
) -> list[ScenarioRead]:
    """List scenario templates (own + public)."""
    stmt = select(Scenario).where(
        Scenario.is_template == True,
        or_(Scenario.owner_id == analyst.id, Scenario.owner_id == None),
    )
    if case_type:
        stmt = stmt.where(Scenario.case_type == case_type)
    stmt = stmt.order_by(Scenario.created_at.desc())
    scenarios = db.scalars(stmt).all()
    return [ScenarioRead.model_validate(item) for item in scenarios]


@router.post("/{scenario_id}/clone", response_model=ScenarioRead, status_code=status.HTTP_201_CREATED)
def clone_scenario(
    scenario_id: int,
    payload: ScenarioCloneRequest,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
) -> ScenarioRead:
    """Clone a scenario or template into analyst's workspace."""
    # Allow cloning own scenarios or templates
    stmt = select(Scenario).where(
        Scenario.id == scenario_id,
        or_(Scenario.owner_id == analyst.id, Scenario.is_template == True),
    )
    source = db.scalar(stmt)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

    clone = Scenario(
        name=payload.name,
        case_type=source.case_type,
        triggers=source.triggers,
        impacts=source.impacts,
        time_horizon_hours=source.time_horizon_hours,
        probability=source.probability,
        is_template=False,
        template_id=source.id if source.is_template else source.template_id,
        owner_id=analyst.id,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return ScenarioRead.model_validate(clone)


@router.get("", response_model=list[ScenarioRead])
def list_scenarios(
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
    case_type: str | None = None,
    is_template: bool | None = None,
    q: str | None = None,
) -> list[ScenarioRead]:
    stmt = select(Scenario).where(Scenario.owner_id == analyst.id)
    if case_type:
        stmt = stmt.where(Scenario.case_type == case_type)
    if is_template is not None:
        stmt = stmt.where(Scenario.is_template == is_template)
    if q:
        stmt = stmt.where(or_(Scenario.name.ilike(f"%{q}%"), Scenario.triggers.ilike(f"%{q}%")))
    stmt = stmt.order_by(Scenario.created_at.desc())
    scenarios = db.scalars(stmt).all()
    return [ScenarioRead.model_validate(item) for item in scenarios]


@router.get("/{scenario_id}", response_model=ScenarioRead)
def get_scenario(
    scenario_id: int,
    analyst: CurrentAnalyst,
    db: Annotated[Session, Depends(get_db)],
) -> ScenarioRead:
    stmt = select(Scenario).where(Scenario.id == scenario_id, Scenario.owner_id == analyst.id)
    scenario = db.scalar(stmt)
    if scenario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    return ScenarioRead.model_validate(scenario)
