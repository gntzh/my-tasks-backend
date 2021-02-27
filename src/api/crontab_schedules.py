from typing import Any

from fastapi import APIRouter, HTTPException

from src import schemas
from src.infra.repo.repo import crontab_schedule_repo
from src.infra.session import get_session

router = APIRouter()


@router.get("/", response_model=list[schemas.CrontabSchedule])
def list_crontab_schedule(
    skip: int = 0,
    limit: int = 100,
) -> Any:
    with get_session().begin():
        crontabs = crontab_schedule_repo.get_multi(skip=skip, limit=limit)
        return crontabs


@router.post("/", response_model=schemas.CrontabSchedule)
def create_crontab_schedule(article_data: schemas.CrontabScheduleCreate) -> Any:
    with get_session().begin():
        crontab = crontab_schedule_repo.create(article_data)
    return crontab


@router.get("/{id}", response_model=schemas.CrontabSchedule)
def get_crontab_schedule(id: int) -> Any:
    with get_session().begin():
        if not (schedule := crontab_schedule_repo.get(id)):
            raise HTTPException(status_code=404, detail="Item not found")
        return schedule


@router.put("/{id}", response_model=schemas.CrontabSchedule)
def update_crontab_schedule(id: int, data: schemas.CrontabScheduleUpdate) -> Any:
    with get_session().begin():
        if not (schedule := crontab_schedule_repo.get(id)):
            raise HTTPException(status_code=404, detail="Item not found")
        crontab_schedule_repo.update(schedule, data)
        return schedule


@router.delete("/{id}")
def delete_crontab_schedule(id: int) -> Any:
    with get_session().begin():
        if not crontab_schedule_repo.delete(id=id):
            raise HTTPException(status_code=404, detail="Item not found")
