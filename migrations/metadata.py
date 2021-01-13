# imported by Alembic
# provides target_metadata to Alembic
from src.models import (  # noqa: F401
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    PeriodicTasks,
    SolarSchedule,
)
from src.models.mapper import Base
from src.models.user import User  # noqa: F401

__all__ = ["metadata"]

# Base.metadata.create_all(bind=engine)

metadata = Base.metadata  # type: ignore
