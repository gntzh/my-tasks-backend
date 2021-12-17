# imported by Alembic
# provides target_metadata to Alembic
from src.models.mapper import Base
from src.models.models import (  # noqa: F401
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    PeriodicTasksChange,
    SolarSchedule,
)

__all__ = ["metadata"]

# Base.metadata.create_all(bind=engine)

metadata = Base.metadata  # type: ignore
