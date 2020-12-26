from typing import Any

from fastapi import APIRouter, HTTPException

from src import schemas
from src.infra.repo import interval_schedule_repo
from src.infra.session import get_session

router = APIRouter()


@router.get("/", response_model=list[schemas.IntervalSchedule])
def list_interval_schedule(
    skip: int = 0,
    limit: int = 100,
) -> Any:
    with get_session().begin():
        intervals = interval_schedule_repo.get_multi(skip=skip, limit=limit)
        return intervals


@router.post("/", response_model=schemas.IntervalSchedule)
def create_interval_schedule(article_data: schemas.IntervalScheduleCreate) -> Any:
    with get_session().begin():
        interval = interval_schedule_repo.create(article_data)
    return interval


@router.get("/{id}", response_model=schemas.IntervalSchedule)
def get_interval_schedule(id: int) -> Any:
    with get_session().begin():
        if not (interval := interval_schedule_repo.get(id)):
            raise HTTPException(status_code=404, detail="Item not found")
        return interval


@router.put("/{id}", response_model=schemas.IntervalSchedule)
def update_interval_schedule(id: int, data: schemas.IntervalScheduleUpdate) -> Any:
    with get_session().begin():
        if not (interval := interval_schedule_repo.get(id)):
            raise HTTPException(status_code=404, detail="Item not found")
        interval_schedule_repo.update(interval, data)
        return interval


@router.delete("/{id}")
def delete_interval_schedule(id: int) -> Any:
    with get_session().begin():
        if not interval_schedule_repo.delete(id=id):
            raise HTTPException(status_code=404, detail="Item not found")
