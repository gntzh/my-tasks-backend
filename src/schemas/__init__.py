from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field, Json, PositiveInt, root_validator, validator

from src.models import PERIOD_CHOICES
from src.utils.crontab_validators import validate_crontab
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
    day_of_month: str = Field("*", max_length=31 * 4)
    month_of_year: str = Field("*", max_length=64)
    day_of_week: str = Field("*", max_length=64)
    # TIMEZONE str
    timezone: str = Field("UTC", max_length=63)

    @validator("minute")
    def check_minute(cls, v: str) -> str:
        validate_crontab(v, 0)
        return v

    @validator("hour")
    def check_hour(cls, v: str) -> str:
        validate_crontab(v, 1)
        return v

    @validator("day_of_month")
    def check_day_of_month(cls, v: str) -> str:
        validate_crontab(v, 2)
        return v

    @validator("month_of_year")
    def check_month_of_year(cls, v: str) -> str:
        validate_crontab(v, 3)
        return v

    @validator("day_of_week")
    def check_day_of_week(cls, v: str) -> str:
        validate_crontab(v, 4)
        return v


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


class ClockedScheduleBase(BaseModel):
    clocked_time: datetime


class ClockedScheduleCreate(ClockedScheduleBase):
    pass


class ClockedScheduleUpdate(ClockedScheduleBase):
    pass


class ClockedScheduleInDBBase(ClockedScheduleBase):
    id: int

    class Config:
        orm_mode = True


class ClockedSchedule(ClockedScheduleInDBBase):
    pass


class ClockedScheduleInDB(ClockedScheduleInDBBase):
    pass


class SolarScheduleBase(BaseModel):
    event: str = Field(..., max_length=24)
    latitude: Decimal = Field(..., ge=-90, le=90)
    longitude: Decimal = Field(..., ge=-180, le=180)


class SolarScheduleCreate(SolarScheduleBase):
    pass


class SolarScheduleUpdate(SolarScheduleBase):
    pass


class SolarScheduleInDBBase(SolarScheduleBase):
    id: int

    class Config:
        orm_mode = True


class SolarSchedule(SolarScheduleInDBBase):
    pass


class SolarScheduleInDB(SolarScheduleInDBBase):
    pass


class PeriodicTaskBase(BaseModel):

    name: str = Field(..., max_length=200)
    task: str = Field(..., max_length=200)

    interval_id: Optional[int] = None
    crontab_id: Optional[int] = None
    clocked_id: Optional[int] = None
    solar_id: Optional[int] = None

    args: Json[list] = Field(default_factory=list)  # type: ignore
    kwargs: Json[dict] = Field(default_factory=dict)  # type: ignore

    queue: Optional[str] = Field(None, max_length=200)

    exchange: Optional[str] = Field(None, max_length=200)
    routing_key: Optional[str] = Field(None, max_length=200)
    headers: Json[dict] = Field(default_factory=dict)  # type: ignore
    priority: Optional[int] = Field(None, ge=0, le=255)
    expires: Optional[datetime] = None
    expire_seconds: Optional[PositiveInt] = None
    one_off: bool = False
    start_time: Optional[datetime] = None
    enabled: bool = True
    description: str = ""

    @root_validator
    def check_unique_schedule(cls, values: dict) -> dict:
        # values contains the default values
        num = 0
        for field in ("interval_id", "crontab_id", "solar_id", "clocked_id"):
            if values.get(field) is not None:
                num += 1
        if num != 1:
            raise ValueError(
                "Only one of clocked, interval, crontab, or solar must be set"
            )
        if values.get("clocked_id") is not None and not values["one_off"]:
            raise ValueError("Clocked task must be one off, one_off must set True")
        return values


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
