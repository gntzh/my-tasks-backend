from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, Json, PositiveInt

from src.models import PERIOD_CHOICES
from src.utils.timezone import utcnow

# TODO Customize JsonStr
# Or refer to django-celery-beat's implementation using JsonField


class IntervalScheduleBase(BaseModel):
    every: int = Field(ge=1)
    period: PERIOD_CHOICES


class IntervalScheduleCreate(IntervalScheduleBase):
    pass


class IntervalScheduleUpdate(IntervalScheduleBase):
    pass


class IntervalScheduleInDBBase(IntervalScheduleBase):
    id: int

    class Config:
        orm_mode = True


class IntervalSchedule(IntervalScheduleInDBBase):
    pass


class IntervalScheduleInDB(IntervalScheduleInDBBase):
    pass


class CrontabScheduleBase(BaseModel):
    minute: str = Field("*", max_length=60 * 4)
    hour: str = Field("*", max_length=24 * 4)
    day_of_week: str = Field("*", max_length=64)
    day_of_month: str = Field("*", max_length=31 * 4)
    month_of_year: str = Field("*", max_length=64)
    # TIMEZONE str
    timezone: str = Field("UTC", max_length=63)


class CrontabScheduleCreate(CrontabScheduleBase):
    pass


class CrontabScheduleUpdate(CrontabScheduleBase):
    pass


class CrontabScheduleInDBBase(CrontabScheduleBase):
    id: int

    class Config:
        orm_mode = True


class CrontabSchedule(CrontabScheduleInDBBase):
    pass


class CrontabScheduleInDB(CrontabScheduleInDBBase):
    pass


class PeriodicTaskBase(BaseModel):

    name: str = Field(..., max_length=200)
    task: str = Field(..., max_length=200)

    interval_id: Optional[int] = None
    crontab_id: Optional[int] = None

    args: Json[list] = Field(default_factory=list)
    kwargs: Json[dict] = Field(default_factory=dict)

    queue: Optional[str] = Field(None, max_length=200)

    exchange: Optional[str] = Field(None, max_length=200)
    routing_key: Optional[str] = Field(None, max_length=200)
    headers: Optional[str] = None
    priority: Optional[int] = Field(None, ge=0, le=255)
    expires: Optional[datetime] = None
    expire_seconds: Optional[PositiveInt] = None
    one_off: bool = False
    start_time: Optional[datetime] = None
    enabled: Optional[bool] = True
    description: str = ""


class PeriodicTaskCreate(PeriodicTaskBase):
    pass


class PeriodicTaskUpdate(PeriodicTaskBase):
    pass


class PeriodicTaskInDBBase(PeriodicTaskBase):
    id: int
    last_run_at: Optional[datetime] = None
    total_run_count: int = 0
    date_changed: datetime = Field(default_factory=utcnow)

    class Config:
        orm_mode = True


class PeriodicTask(PeriodicTaskInDBBase):
    pass


class PeriodicTaskInDB(PeriodicTaskInDBBase):
    pass
