import enum
from datetime import timedelta
from typing import Any, Union

import pytz
from celery import schedules
from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Interval

from src.lib.sa.timezone import TZDateTime
from src.tz_crontab import TZCrontab
from src.utils.timezone import utcnow

from .mapper import Base


# 继承 str，用于 Pydantic
class PERIOD_CHOICES(str, enum.Enum):
    DAYS = "days"
    HOURS = "hours"
    MINUTES = "minutes"
    SECONDS = "seconds"
    MICROSECONDS = "microseconds"


class IntervalSchedule(Base):
    __tablename__ = "celery_interval_schedule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 1 ≤ every
    every = Column(Integer, nullable=False)
    period = Column(String(24), Enum(PERIOD_CHOICES), nullable=False)

    @property
    def schedule(self) -> schedules.schedule:
        return schedules.schedule(timedelta(**{self.period: self.every}), nowfun=utcnow)

    def __str__(self) -> str:
        return f"every {self.every} {self.period}"


def cronexp(field: str) -> str:
    """Representation of cron expression."""
    return field and str(field).replace(" ", "") or "*"


class CrontabSchedule(Base):
    __tablename__ = "celery_crontab_schedule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # minute ≤ 60*4
    minute = Column(String(60 * 4), default="*")
    # hour ≤ 24*4
    hour = Column(String(24 * 4), default="*")
    # day_of_week ≤ 64
    day_of_week = Column(String(64), default="*")
    # day_of_month ≤ 31*4
    day_of_month = Column(String(31 * 4), default="*")
    # month_of_year ≤ 64
    month_of_year = Column(String(64), default="*")
    # TIMEZONE str
    timezone = Column(String(63), default="UTC")

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
    def schedule(self) -> TZCrontab:
        # enable tz aware
        return TZCrontab(
            minute=self.minute,
            hour=self.hour,
            day_of_week=self.day_of_week,
            day_of_month=self.day_of_month,
            month_of_year=self.month_of_year,
            tz=pytz.timezone(self.timezone),
        )


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
    headers = Column(Text, default=None)

    priority = Column(Integer, default=None)  # 0 ≤ priority ≤ 255
    expires = Column(TZDateTime, default=None)

    expire_seconds = Column(Integer, default=None)  # 0 ≤ expire_seconds
    one_off = Column(Boolean, default=False)
    start_time = Column(TZDateTime, default=None)
    enabled = Column(Boolean, default=True)

    last_run_at = Column(TZDateTime, default=None)  # non editable

    total_run_count = Column(Integer, nullable=False, default=0)  # non editable
    # Datetime that this PeriodicTask was last modified
    date_changed = Column(TZDateTime, default=utcnow, onupdate=utcnow)  # auto change
    description = Column(Text, default="")

    no_changes = False

    def __repr__(self) -> str:
        fmt = "{0.name}: {{no schedule}}"
        if self.interval:
            fmt = "{0.name}: {0.interval}"
        elif self.crontab:
            fmt = "{0.name}: {0.crontab}"
        # elif self.solar:
        #     fmt = "{0.name}: {0.solar}"
        return fmt.format(self)

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
        # elif self.solar:
        #     return self.solar.schedule
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


ModelSchedule = Union[Interval, CrontabSchedule]
