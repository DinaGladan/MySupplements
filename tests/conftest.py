"""Shared pytest fixtures.

The whole suite runs WITHOUT PostgreSQL and WITHOUT Ollama:
- the DB is replaced with in-memory Supplement objects (see the factory below),
- the FastAPI get_db dependency is overridden with a no-op session,
- LLM calls are monkeypatched away in the individual API tests.
"""
import pytest
from fastapi.testclient import TestClient

from app.db.database import get_db
from app.main import app
from app.models.supplement import Supplement
from app.schemas.goals_schema import GoalType, ParsedGoals
from app.schemas.profile_schema import (
    Gender,
    IntakeLevel,
    ParsedProfile,
    SleepQuality,
    StressLevel,
)


@pytest.fixture
def make_supplement():
    """Factory that builds an in-memory Supplement (no database involved)."""

    def _make(
        name,
        *,
        id=1,
        goal_tags=None,
        state=None,
        lifestyle=None,
        diet=None,
        deficiency=None,
        penalties=None,
        description="test supplement",
    ):
        return Supplement(
            id=id,
            name=name,
            description=description,
            goal_tags=goal_tags or [],
            state_scores=state or {},
            lifestyle_scores=lifestyle or {},
            diet_scores=diet or {},
            deficiency_scores=deficiency or {},
            penalties=penalties or {},
        )

    return _make


@pytest.fixture
def sample_supplements(make_supplement):
    """A small, realistic set of supplements used by engine and API tests."""
    return [
        make_supplement(
            "magnesium_glycinate",
            id=1,
            goal_tags=["better_sleep", "stress_reduction", "mood_support", "recovery"],
            state={
                "sleep_quality:poor": 3,
                "stress_level:high": 3,
                "stress_level:medium": 1,
                "fatigue_level:high": 1,
            },
            lifestyle={"activity_level:high": 2, "caffeine_intake:high": 1},
        ),
        make_supplement(
            "melatonin",
            id=2,
            goal_tags=["better_sleep"],
            state={"sleep_quality:poor": 3},
            lifestyle={"caffeine_intake:high": 1},
        ),
        make_supplement(
            "b_complex",
            id=3,
            goal_tags=["more_energy", "better_focus", "mood_support"],
            state={
                "fatigue_level:high": 3,
                "fatigue_level:medium": 1,
                "focus_issues:true": 2,
                "stress_level:high": 1,
            },
            lifestyle={"activity_level:high": 1},
            diet={"diet_type:vegan": 3, "diet_type:vegetarian": 2},
        ),
        make_supplement(
            "collagen",
            id=4,
            goal_tags=["skin_health", "hair_health", "nail_strength", "recovery"],
            lifestyle={"activity_level:high": 1},
            penalties={
                "diet_type:vegan": {
                    "penalty": 4,
                    "warning": "Kolagen nije kompatibilan s veganskom prehranom.",
                }
            },
        ),
        make_supplement(
            "biotin",
            id=5,
            goal_tags=["hair_health", "nail_strength", "skin_health"],
        ),
    ]


@pytest.fixture
def profile_sleep_stress():
    """User who sleeps poorly, is stressed and drinks a lot of coffee."""
    return ParsedProfile(
        age=23,
        gender=Gender.female,
        sleep_quality=SleepQuality.poor,
        stress_level=StressLevel.high,
        caffeine_intake=IntakeLevel.high,
    )


@pytest.fixture
def goals_sleep_stress():
    return ParsedGoals(goals=[GoalType.better_sleep, GoalType.stress_reduction])


@pytest.fixture
def client():
    """TestClient with get_db overridden.

    Instantiated without a `with` block so the app lifespan (which would call
    Base.metadata.create_all against a real PostgreSQL) does NOT run.
    """

    def _fake_get_db():
        yield None

    app.dependency_overrides[get_db] = _fake_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()
