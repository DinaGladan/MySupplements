from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories.supplement_repository import (
    get_all_supplements,
    get_supplement_by_name,
)

router = APIRouter()


class SupplementOut(BaseModel):
    id: int
    name: str
    description: str | None
    goal_tags: list[str]
    state_scores: dict
    lifestyle_scores: dict
    diet_scores: dict
    deficiency_scores: dict
    penalties: dict

    model_config = {"from_attributes": True}


@router.get(
    "",
    response_model=list[SupplementOut],
    summary="List all supplements",
    description="Returns every supplement in the database. Use this to verify the seed worked.",
)
def list_supplements(db: Session = Depends(get_db)) -> list[SupplementOut]:
    return get_all_supplements(db)


@router.get(
    "/{name}",
    response_model=SupplementOut,
    summary="Get one supplement by name",
    description="Fetch a single supplement by its exact name (e.g. magnesium_glycinate).",
)
def get_supplement(name: str, db: Session = Depends(get_db)) -> SupplementOut:
    supplement = get_supplement_by_name(db, name)
    if not supplement:
        raise HTTPException(status_code=404, detail=f"Supplement '{name}' not found.")
    return supplement
