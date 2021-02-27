from typing import Any

from fastapi import APIRouter, HTTPException

from src import schemas
from src.infra.repo.repo import periodic_task_repo
from src.infra.session import get_session

router = APIRouter()


@router.get("/", response_model=list[schemas.PeriodicTask])
def list_periodic_task(
    skip: int = 0,
    limit: int = 100,
) -> Any:
    with get_session().begin():
        tasks = periodic_task_repo.get_multi(skip=skip, limit=limit)
        return tasks


@router.get("/{id}", response_model=schemas.PeriodicTask)
def get_period_task(id: int) -> Any:
    with get_session().begin():
        if not (task := periodic_task_repo.get(id)):
            raise HTTPException(status_code=404, detail="Item not found")
        return task


@router.post("/", response_model=schemas.PeriodicTask)
def create_periodic_task(data: schemas.PeriodicTaskCreate) -> Any:
    with get_session().begin():
        task = periodic_task_repo.create(data)
    return task


@router.put("/{id}", response_model=schemas.PeriodicTask)
def update_periodic_task(id: int, data: schemas.PeriodicTaskUpdate) -> Any:
    with get_session().begin():
        if not (task := periodic_task_repo.get(id)):
            raise HTTPException(status_code=404, detail="Item not found")
        periodic_task_repo.update(task, data)
        return task


@router.delete("/{id}")
def delete_periodic_task(id: int) -> Any:
    with get_session().begin():
        if not periodic_task_repo.delete(id=id):
            raise HTTPException(status_code=404, detail="Item not found")


@router.get("/{id}/enable")
def enable_task(id: int) -> Any:
    with get_session().begin():
        if not (task := periodic_task_repo.get(id)):
            raise HTTPException(status_code=404, detail="Item not found")
        task.enable()


@router.get("/{id}/disable")
def disable_task(id: int) -> Any:
    with get_session().begin():
        if not (task := periodic_task_repo.get(id)):
            raise HTTPException(status_code=404, detail="Item not found")
        task.disable()
