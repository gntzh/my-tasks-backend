import json
from typing import Any, Optional, Type, Union

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm.session import Session

from src import schedules, schemas
from .base import CRUDBase, ModelT, UpdateSchemaT
from src.infra.session import get_session
from src.models.models import (
    PERIOD_CHOICES,
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    PeriodicTasksChange,
    SolarSchedule,
)
from src.utils.timezone import utcnow


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

        model_schedule = (
            (db := db or get_session())
            .execute(select(IntervalSchedule).filter_by(every=every, period=period))
            .scalar()
        )
        if model_schedule is None:
            model_schedule = PeriodicTask(every=every, period=period)
            db.add(model_schedule)
        # TODO delete duplicate items
        # https://sourcegraph.com/github.com/celery/django-celery-beat/-/blob/django_celery_beat/models.py#L185

        return model_schedule


class ClockedScheduleRepo(
    CRUDBase[
        ClockedSchedule,
        schemas.ClockedScheduleCreate,
        schemas.ClockedScheduleUpdate,
    ]
):
    def from_celery_schedule(
        self,
        schedule: schedules.clocked,
        db: Session = None,
    ) -> ClockedSchedule:
        spec = {"clocked_time": schedule.clocked_time}
        return self.get_or_create(db=db, **spec)


class SolarScheduleRepo(
    CRUDBase[
        SolarSchedule,
        schemas.SolarScheduleCreate,
        schemas.SolarScheduleUpdate,
    ]
):
    def from_celery_schedule(
        self,
        schedule: schedules.solar,
        db: Session = None,
    ) -> SolarSchedule:
        spec = {
            "event": schedule.event,
            "latitude": schedule.lat,
            "longitude": schedule.lon,
        }
        return self.get_or_create(db=db, **spec)


class CrontabScheduleRepo(
    CRUDBase[
        CrontabSchedule, schemas.CrontabScheduleCreate, schemas.CrontabScheduleUpdate
    ]
):
    def from_celery_schedule(
        self,
        schedule: schedules.tz_crontab,
        db: Session = None,
    ) -> CrontabSchedule:
        spec = {
            "minute": schedule._orig_minute,
            "hour": schedule._orig_hour,
            "day_of_week": schedule._orig_day_of_week,
            "day_of_month": schedule._orig_day_of_month,
            "month_of_year": schedule._orig_month_of_year,
            "timezone": "UTC" if schedule.tz is None else schedule.tz.zone,
        }
        return self.get_or_create(db=db, **spec)


class PeriodicTaskRepo(
    CRUDBase[PeriodicTask, schemas.PeriodicTaskCreate, schemas.PeriodicTaskUpdate]
):
    @staticmethod
    def _json2str(data: dict[str, Any]) -> None:
        for key in ("args", "kwargs", "headers"):
            if (t := data.get(key)) is not None:
                data[key] = json.dumps(t)

    def create(
        self, obj_in: schemas.PeriodicTaskCreate, db: Session = None
    ) -> PeriodicTask:
        obj_in_data = obj_in.dict()
        self._json2str(obj_in_data)
        db_obj = self.model(**obj_in_data)
        (db := db or get_session()).add(db_obj)
        db.flush((db_obj,))  # get a persistent instance
        db.refresh(db_obj)  # access relationship
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
        (db := db or get_session()).add(db_obj)
        db.flush((db_obj,))
        db.refresh(db_obj)
        return db_obj

    def get_by_name(self, name: str, db: Session = None) -> Optional[ModelT]:
        return (
            (db or get_session())
            .execute(select(self.model).filter_by(name=name))
            .scalar()
        )

    def get_enabled(self, db: Session = None) -> list[PeriodicTask]:
        return (
            (db or get_session())
            .execute(
                select(self.model)
                .filter_by(enabled=True)
                .order_by(self.model.id.desc())
            )
            .scalars()
            .all()
        )


class PeriodicTasksChangeRepo:
    def __init__(self, model: Type[PeriodicTasksChange]) -> None:
        self.model = model

    def get(self, db: Session = None) -> PeriodicTasksChange:
        return get_session(db).execute(select(self.model)).scalar()

    def update_or_create(self, db: Session = None) -> PeriodicTasksChange:
        session = get_session(db)
        if db_obj := session.execute(select(self.model)).scalar():
            db_obj.last_update = utcnow()
        else:
            obj = self.model(last_update=utcnow())
            session.add(obj)
        return db_obj


interval_schedule_repo = IntervalScheduleRepo(IntervalSchedule)
crontab_schedule_repo = CrontabScheduleRepo(CrontabSchedule)
clocked_schedule_repo = ClockedScheduleRepo(ClockedSchedule)
solar_schedule_repo = SolarScheduleRepo(SolarSchedule)
periodic_tasks_change_repo = PeriodicTasksChangeRepo(PeriodicTasksChange)
periodic_task_repo = PeriodicTaskRepo(PeriodicTask)
