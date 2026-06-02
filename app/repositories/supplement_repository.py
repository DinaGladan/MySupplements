from sqlalchemy.orm import Session
from app.models.supplement import Supplement


def get_all_supplements(db: Session) -> list[Supplement]:
    return db.query(Supplement).all()


def get_supplement_by_name(db: Session, name: str) -> Supplement | None:
    return db.query(Supplement).filter(Supplement.name == name).first()
