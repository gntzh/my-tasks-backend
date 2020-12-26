# imported by Alembic
# provides target_metadata to Alembic
from src.models.mapper import Base
from src.models import IntervalSchedule  # noqa: F401

__all__ = ["metadata"]

# Base.metadata.create_all(bind=engine)

metadata = Base.metadata  # type: ignore
