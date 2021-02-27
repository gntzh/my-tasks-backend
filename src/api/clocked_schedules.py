from typing import Any

from fastapi import APIRouter, HTTPException

from src import schemas
from src.infra.repo.repo import clocked_schedule_repo
from src.infra.session import get_session

router = APIRouter()


@router.get("/", response_model=list[schemas.ClockedSchedule])
def list_clocked_schedule(
    skip: int = 0,
    limit: int = 100,
) -> Any:
    with get_session().begin():
        clockeds = clocked_schedule_repo.get_multi(skip=skip, limit=limit)
        return clockeds


@router.post("/", response_model=schemas.ClockedSchedule)
def create_clocked_schedule(article_data: schemas.ClockedScheduleCreate) -> Any:
    with get_session().begin():
        clocked = clocked_schedule_repo.create(article_data)
    return clocked


@router.get("/{id}", response_model=schemas.ClockedSchedule)
def get_clocked_schedule(id: int) -> Any:
    with get_session().begin():
        if not (clocked := clocked_schedule_repo.get(id)):
            raise HTTPException(status_code=404, detail="Item not found")
        return clocked


@router.put("/{id}", response_model=schemas.ClockedSchedule)
def update_clocked_schedule(id: int, data: schemas.ClockedScheduleUpdate) -> Any:
    with get_session().begin():
        if not (clocked := clocked_schedule_repo.get(id)):
            raise HTTPException(status_code=404, detail="Item not found")
        clocked_schedule_repo.update(clocked, data)
        return clocked


@router.delete("/{id}")
def delete_clocked_schedule(id: int) -> Any:
    with get_session().begin():
        if not clocked_schedule_repo.delete(id=id):
            raise HTTPException(status_code=404, detail="Item not found")
