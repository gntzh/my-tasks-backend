from typing import Any

from fastapi import APIRouter, HTTPException

from src import schemas
from src.infra.repo import solar_schedule_repo
from src.infra.session import get_session

router = APIRouter()


@router.get("/", response_model=list[schemas.SolarSchedule])
def list_solar_schedule(
    skip: int = 0,
    limit: int = 100,
) -> Any:
    with get_session().begin():
        solars = solar_schedule_repo.get_multi(skip=skip, limit=limit)
        return solars


@router.post("/", response_model=schemas.SolarSchedule)
def create_solar_schedule(article_data: schemas.SolarScheduleCreate) -> Any:
    with get_session().begin():
        solar = solar_schedule_repo.create(article_data)
    return solar


@router.get("/{id}", response_model=schemas.SolarSchedule)
def get_solar_schedule(id: int) -> Any:
    with get_session().begin():
        if not (solar := solar_schedule_repo.get(id)):
            raise HTTPException(status_code=404, detail="Item not found")
        return solar


@router.put("/{id}", response_model=schemas.SolarSchedule)
def update_solar_schedule(id: int, data: schemas.SolarScheduleUpdate) -> Any:
    with get_session().begin():
        if not (solar := solar_schedule_repo.get(id)):
            raise HTTPException(status_code=404, detail="Item not found")
        solar_schedule_repo.update(solar, data)
        return solar


@router.delete("/{id}")
def delete_solar_schedule(id: int) -> Any:
    with get_session().begin():
        if not solar_schedule_repo.delete(id=id):
            raise HTTPException(status_code=404, detail="Item not found")
