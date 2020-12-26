from typing import Any, Generic, Optional, Protocol, Type, TypeVar, Union
import json

from celery import schedules
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm.session import Session

from src import schemas
from src.infra.session import get_session
from src.models import PERIOD_CHOICES, IntervalSchedule, PeriodicTask, PeriodicTasks
from src.utils.timezone import utcnow


class ModelBase(Protocol):
    id: Any


ModelT = TypeVar("ModelT", bound=ModelBase)
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)


class CRUDBase(Generic[ModelT, CreateSchemaT, UpdateSchemaT]):
    def __init__(self, model: Type[ModelT]) -> None:
        self.model = model

    def get(self, id: Any, db: Session = None) -> Optional[ModelT]:
        return (
            (db or get_session()).execute(select(self.model).filter_by(id=id)).scalar()
        )

    def get_multi(
        self, *, skip: int = 0, limit: int = 100, db: Session = None
    ) -> list[ModelT]:
        return (
            (db or get_session())
            .execute(
                select(self.model)
                .order_by(self.model.id.desc())
                .offset(skip)
                .limit(limit)
            )
            .scalars()
            .all()
        )

    def create(self, obj_in: CreateSchemaT, db: Session = None) -> ModelT:
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)
        (db or get_session()).add(db_obj)
        return db_obj

    def update(
        self,
        db_obj: ModelT,
        obj_in: Union[UpdateSchemaT, dict[str, Any]],
        db: Session = None,
    ) -> ModelT:
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        (db or get_session()).add(db_obj)
        return db_obj

    def get_or_create(
        self, defaults: dict[str, Any] = None, db: Session = None, **kwargs
    ) -> ModelT:
        session = db or get_session()
        db_obj = session.execute(select(self.model).filter_by(**kwargs)).scalar()
        if db_obj is None:
            kwargs |= defaults or {}
            db_obj = self.model(**kwargs)
            session.add(db_obj)
        return db_obj

    def update_or_create(
        self, defaults: dict[str, Any] = None, db: Session = None, **kwargs
    ) -> ModelT:
        session = db or get_session()
        db_obj = session.execute(select(self.model).filter_by(**kwargs)).scalar()
        if db_obj is None:
            kwargs |= defaults or {}
            db_obj = self.model(**kwargs)
        else:
            for field in kwargs:
                setattr(db_obj, field, kwargs[field])
        session.add(db_obj)
        return db_obj


class IntervalScheduleRepo(
    CRUDBase[
        IntervalSchedule, schemas.IntervalScheduleCreate, schemas.IntervalScheduleUpdate
    ]
):
    def from_celery_schedule(
        self,
        schedule: schedules.schedule,
        period: PERIOD_CHOICES = PERIOD_CHOICES.SECONDS,
        db: Session = None,
    ) -> IntervalSchedule:
        every = max(schedule.run_every.total_seconds(), 0)
        session = get_session(db)
        model_schedule = session.execute(
            select(IntervalSchedule).filter_by(every=every, period=period)
        ).scalar()
        if model_schedule is None:
            model_schedule = PeriodicTask(every=every, period=period)
            session.add(model_schedule)
        # TODO 清除重复的
        # https://sourcegraph.com/github.com/celery/django-celery-beat/-/blob/django_celery_beat/models.py#L185

        return model_schedule


class PeriodicTaskRepo(
    CRUDBase[PeriodicTask, schemas.PeriodicTaskCreate, schemas.PeriodicTaskUpdate]
):
    @staticmethod
    def _json2str(data: dict[str]) -> None:
        for key in ("args", "kwargs", "headers"):
            if (t := data.get(key)) is not None:
                data[key] = json.dumps(t)

    def create(
        self, obj_in: schemas.PeriodicTaskCreate, db: Session = None
    ) -> PeriodicTask:
        obj_in_data = jsonable_encoder(obj_in)
        self._json2str(obj_in_data)
        db_obj = self.model(**obj_in_data)
        (db or get_session()).add(db_obj)
        return db_obj

    def update(
        self,
        db_obj: PeriodicTask,
        obj_in: Union[UpdateSchemaT, dict[str, Any]],
        db: Session = None,
    ) -> PeriodicTask:
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        self._json2str(obj_data)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        (db or get_session()).add(db_obj)
        return db_obj

    def get_by_name(self, name: str, db: Session = None) -> Optional[ModelT]:
        return (
            (db or get_session())
            .execute(select(self.model).filter_by(name=name))
            .scalar()
        )

    def get_enabled(self, db: Session = None) -> list[PeriodicTask]:
        return (
            get_session(db)
            .execute(
                select(self.model)
                .filter_by(enabled=True)
                .order_by(self.model.id.desc())
            )
            .scalars()
            .all()
        )


class PeriodicTasksRepo:
    def __init__(self, model: Type[PeriodicTasks]) -> None:
        self.model = model

    def get(self, db: Session = None) -> PeriodicTasks:
        return get_session(db).execute(select(self.model)).scalar()

    def update_or_create(self, db: Session = None) -> PeriodicTasks:
        session = get_session(db)
        if obj := session.execute(select(self.model)).scalar():
            obj.last_update = utcnow()
        else:
            obj = self.model(last_update=utcnow())
            session.add(obj)
        return obj


interval_schedule_repo = IntervalScheduleRepo(IntervalSchedule)
periodic_task_repo = PeriodicTaskRepo(PeriodicTask)
periodic_tasks_repo = PeriodicTasksRepo(PeriodicTasks)
