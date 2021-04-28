from datetime import datetime
from typing import Optional

from fastapi import APIRouter

from src.infra.repo.repo import periodic_tasks_change_repo

from .clocked_schedules import router as clocked_schedules_router
from .crontab_schedules import router as crontab_scheduler_router
from .interval_schedules import router as interval_schedules_router
from .periodic_tasks import router as periodic_task_router
from .solar_schedules import router as solar_schedules_router

router = APIRouter()

router.include_router(
    interval_schedules_router,
    prefix="/interval-schedules",
    tags=["Interval Schedules"],
)

router.include_router(
    crontab_scheduler_router,
    prefix="/crontab-schedules",
    tags=["Crontab Schedules"],
)

router.include_router(
    clocked_schedules_router,
    prefix="/clocked-schedules",
    tags=["Clocked Schedules"],
)

router.include_router(
    solar_schedules_router,
    prefix="/solar-schedules",
    tags=["Solar Schedules"],
)


router.include_router(
    periodic_task_router,
    prefix="/periodic-tasks",
    tags=["Periodic Tasks"],
)


@router.get("/last-update", response_model=datetime, tags=["Periodic Tasks"])
def last_update() -> Optional[datetime]:
    if (obj := periodic_tasks_change_repo.get()) is None:
        return None
    else:
        return obj.last_update
