import enum
from datetime import timedelta
from typing import Any, Union

import pytz
from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Interval

from src import schedules
from src.libs.sa.timezone import TZDateTime
from src.utils.timezone import utcnow

Base = declarative_base()


# Inherits from str, for Pydantic
class PERIOD_CHOICES(str, enum.Enum):
    DAYS = "days"
    HOURS = "hours"
    MINUTES = "minutes"
    SECONDS = "seconds"
    MICROSECONDS = "microseconds"


class SOLAR_EVENT_CHOICES(str, enum.Enum):
    ASTRONOMICAL_DAWN = "dawn_astronomical"
    CIVIL_DAWN = "dawn_civil"
    NAUTICAL_DAWN = "dawn_nautical"
    ASTRONOMICAL_DUSK = "dusk_astronomical"
    CIVIL_DUSK = "dusk_civil"
    NAUTICAL_DUSK = "dusk_nautical"
    SOLAR_NOON = "solar_noon"
    SUNRISE = "sunrise"
    SUNSET = "sunset"


class IntervalSchedule(Base):
    __tablename__ = "celery_interval_schedule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # XXX Maybe sqlalchemy.types.Interval is better
    # 1 ≤ every
    every = Column(Integer, nullable=False)
    period = Column(String(24), Enum(PERIOD_CHOICES), nullable=False)

    @property
    def schedule(self) -> schedules.schedule:
        return schedules.schedule(timedelta(**{self.period: self.every}), nowfun=utcnow)

    def __str__(self) -> str:
        return f"every {self.every} {self.period}"

    @classmethod
    def from_celery_schedule(
        cls,
        schedule: schedules.schedule,
        period: PERIOD_CHOICES = PERIOD_CHOICES.SECONDS,
    ) -> "IntervalSchedule":
        every = max(schedule.run_every.total_seconds(), 0)
        return cls(every=every, period=period)


def cronexp(field: str) -> str:
    """Representation of cron expression."""
    return field and str(field).replace(" ", "") or "*"


class CrontabSchedule(Base):
    __tablename__ = "celery_crontab_schedule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # minute ≤ 60*4
    minute = Column(String(60 * 4), nullable=False, default="*")
    # hour ≤ 24*4
    hour = Column(String(24 * 4), nullable=False, default="*")
    # day_of_month ≤ 31*4
    day_of_month = Column(String(31 * 4), nullable=False, default="*")
    # month_of_year ≤ 64
    month_of_year = Column(String(64), nullable=False, default="*")
    # day_of_week ≤ 64
    day_of_week = Column(String(64), nullable=False, default="*")
    # TIMEZONE str
    timezone = Column(String(63), nullable=False, default="UTC")

    def __str__(self) -> str:
        return "{0} {1} {2} {3} {4} (m/h/dM/MY/d) {5}".format(
            cronexp(self.minute),
            cronexp(self.hour),
            cronexp(self.day_of_month),
            cronexp(self.month_of_year),
            cronexp(self.day_of_week),
            str(self.timezone),
        )

    @property
    def schedule(self) -> schedules.tz_crontab:
        # enable tz aware
        return schedules.tz_crontab(
            minute=self.minute,
            hour=self.hour,
            day_of_week=self.day_of_week,
            day_of_month=self.day_of_month,
            month_of_year=self.month_of_year,
            tz=pytz.timezone(self.timezone),
        )

    @property
    def crontab_expr(self) -> str:
        return " ".join(
            (
                cronexp(self.minute),
                cronexp(self.hour),
                cronexp(self.day_of_month),
                cronexp(self.month_of_year),
                cronexp(self.day_of_week),
            )
        )

    @classmethod
    def from_celery_schedule(cls, schedule: schedules.tz_crontab) -> "CrontabSchedule":
        spec = {
            "minute": schedule._orig_minute,
            "hour": schedule._orig_hour,
            "day_of_week": schedule._orig_day_of_week,
            "day_of_month": schedule._orig_day_of_month,
            "month_of_year": schedule._orig_month_of_year,
            "timezone": "UTC" if schedule.tz is None else schedule.tz.zone,
        }
        return cls(**spec)


class ClockedSchedule(Base):
    """Clocked schedule."""

    __tablename__ = "celery_clocked_schedule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    clocked_time = Column(TZDateTime, nullable=False)

    def __str__(self) -> str:
        return f"{self.clocked_time}"

    @property
    def schedule(self) -> schedules.clocked:
        return schedules.clocked(clocked_time=self.clocked_time)

    @classmethod
    def from_celery_schedule(cls, schedule: schedules.clocked) -> "ClockedSchedule":
        spec = {"clocked_time": schedule.clocked_time}
        return cls(**spec)


class SolarSchedule(Base):
    __tablename__ = "celery_solar_schedule"

    __table_args__ = (UniqueConstraint("event", "latitude", "longitude"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    # event ≤ 24
    event = Column(String(24), Enum(PERIOD_CHOICES), nullable=False)
    # -90 ≤ latitude ≤ 90
    latitude = Column(Numeric(precision=9, scale=6), nullable=False)
    # -180 ≤ longitude ≤ 180
    longitude = Column(Numeric(precision=9, scale=6), nullable=False)

    @property
    def schedule(self) -> schedules.solar:
        return schedules.solar(self.event, self.latitude, self.longitude, nowfun=utcnow)

    def __str__(self) -> str:
        return "{0} ({1}, {2})".format(self.event, self.latitude, self.longitude)

    @classmethod
    def from_celery_schedule(cls, schedule: schedules.solar) -> "SolarSchedule":
        spec = {
            "event": schedule.event,
            "latitude": schedule.lat,
            "longitude": schedule.lon,
        }
        return cls(**spec)


class PeriodicTasks(Base):
    """Helper table for tracking updates to periodic tasks.

    This stores a single row with ident=1.  last_update is updated
    via django signals whenever anything is changed in the PeriodicTask model.
    Basically this acts like a DB data audit trigger.
    Doing this so we also track deletions, and not just insert/update.
    """

    __tablename__ = "celery_periodic_tasks"

    last_update = Column(TZDateTime, primary_key=True, nullable=False)


class PeriodicTask(Base):

    __tablename__ = "celery_periodic_task"

    id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(String(200), unique=True)
    task = Column(String(200))

    interval_id = Column(Integer, ForeignKey(IntervalSchedule.id))
    interval = relationship(IntervalSchedule, lazy="joined")

    crontab_id = Column(Integer, ForeignKey(CrontabSchedule.id))
    crontab = relationship(CrontabSchedule, lazy="joined")

    clocked_id = Column(Integer, ForeignKey(ClockedSchedule.id))
    clocked = relationship(ClockedSchedule, lazy="joined")

    solar_id = Column(Integer, ForeignKey(SolarSchedule.id))
    solar = relationship(SolarSchedule, lazy="joined")

    # JSON encoded positional arguments
    args = Column(Text, default="[]")
    kwargs = Column(Text, default="{}")

    queue = Column(String(200), default=None)

    # you can use low-level AMQP routing options here,
    # but you almost certainly want to leave these as None
    # http://docs.celeryproject.org/en/latest/userguide/routing.html#exchanges-queues-and-routing-keys
    exchange = Column(String(200), default=None)
    # routing_key for celery
    routing_key = Column(String(200), default=None)
    # JSON encoded message headers for the AMQP message.
    headers = Column(Text, nullable=False, default=None)

    priority = Column(Integer, default=None)  # 0 ≤ priority ≤ 255
    expires = Column(TZDateTime, default=None)

    expire_seconds = Column(Integer, default=None)  # 0 ≤ expire_seconds
    one_off = Column(Boolean, nullable=False, default=False)
    start_time = Column(TZDateTime, default=None)
    enabled = Column(Boolean, nullable=False, default=True)

    last_run_at = Column(TZDateTime, default=None)  # non editable

    total_run_count = Column(Integer, nullable=False, default=0)  # non editable
    # Datetime that this PeriodicTask was last modified
    date_changed = Column(TZDateTime, default=utcnow, onupdate=utcnow)  # auto change
    description = Column(Text, nullable=False, default="")

    no_changes = False

    def validate(self) -> None:
        num = 0
        for field in ("interval_id", "crontab_id", "solar_id", "clocked_id"):
            if getattr(self, field) is not None:
                num += 1
        if num != 0:
            raise ValueError(
                "Only one of clocked, interval, crontab, or solar must be set"
            )
        if getattr(self, "clocked_id") is not None and not self.one_off:
            raise ValueError("Clocked task must be one off, one_off must set True")

    # TODO FIXME datetime or int(seconds)?
    @property
    def expires_(self) -> Any:
        return self.expires or self.expire_seconds

    @property
    def schedule(self) -> schedules.BaseSchedule:
        if self.interval:
            return self.interval.schedule
        elif self.crontab:
            return self.crontab.schedule
        if self.clocked:
            return self.clocked.schedule
        elif self.solar:
            return self.solar.schedule
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute schedule")

    def disable(self) -> None:
        self.no_changes = False
        self.enabled = False

    def enable(self) -> None:
        self.no_changes = False
        self.enabled = True

    def disable_error_task(self) -> None:
        self.no_changes = True
        self.enabled = False

    def __repr__(self) -> str:
        fmt = "{0.name}: {{no schedule}}"
        if self.interval:
            fmt = "{0.name}: {0.interval}"
        elif self.crontab:
            fmt = "{0.name}: {0.crontab}"
        elif self.clocked:
            fmt = "{0.name}: {0.crontab}"
        elif self.solar:
            fmt = "{0.name}: {0.solar}"
        return fmt.format(self)


ModelSchedule = Union[Interval, CrontabSchedule, ClockedSchedule, SolarSchedule]
