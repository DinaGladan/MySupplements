from sqlalchemy import Column, Integer, String, JSON
from app.db.database import Base


class Supplement(Base):
    __tablename__ = "supplements"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

    goal_tags = Column(JSON, default=list)

    state_scores = Column(JSON, default=dict)

    lifestyle_scores = Column(JSON, default=dict)

    diet_scores = Column(JSON, default=dict)

    deficiency_scores = Column(JSON, default=dict)

    penalties = Column(JSON, default=dict)
