"""Timezone aware Cron schedule Implementation."""
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

import pytz
from celery import Celery
from celery.schedules import (  # noqa: F401
    BaseSchedule,
    crontab,
    maybe_schedule,
    schedstate,
    schedule,
    solar,
)
from celery.utils.time import maybe_make_aware

from .utils import NEVER_CHECK_TIMEOUT


class tz_crontab(crontab):
    """Timezone Aware Crontab."""

    def __init__(
        self,
        minute: str = "*",
        hour: str = "*",
        day_of_week: str = "*",
        day_of_month: str = "*",
        month_of_year: str = "*",
        tz: pytz.BaseTzInfo = pytz.utc,
        app: Celery = None,
    ):
        """Overwrite Crontab constructor to include a timezone argument."""
        self.tz: pytz.BaseTzInfo = tz

        nowfun = self.nowfunc

        super(tz_crontab, self).__init__(
            minute=minute,
            hour=hour,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
            month_of_year=month_of_year,
            nowfun=nowfun,
            app=app,
        )

    def nowfunc(self) -> datetime:
        return self.tz.normalize(pytz.utc.localize(datetime.utcnow()))

    def is_due(self, last_run_at: datetime) -> schedstate:
        """Calculate when the next run will take place.

        Return tuple of (is_due, next_time_to_check).
        The last_run_at argument needs to be timezone aware.

        """
        # convert last_run_at to the schedule timezone
        last_run_at = last_run_at.astimezone(self.tz)

        rem_delta = self.remaining_estimate(last_run_at)
        rem = max(rem_delta.total_seconds(), 0)
        due = rem == 0
        if due:
            rem_delta = self.remaining_estimate(self.now())
            rem = max(rem_delta.total_seconds(), 0)
        return schedstate(due, rem)

    # Needed to support pickling
    def __repr__(self) -> str:
        return """<crontab: {0._orig_minute} {0._orig_hour}
         {0._orig_day_of_week} {0._orig_day_of_month}
          {0._orig_month_of_year} (m/h/d/dM/MY), {0.tz}>
        """.format(
            self
        )

    def __reduce__(self) -> tuple:
        return (
            self.__class__,
            (
                self._orig_minute,
                self._orig_hour,
                self._orig_day_of_week,
                self._orig_day_of_month,
                self._orig_month_of_year,
                self.tz,
            ),
            None,
        )

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, crontab):
            return (
                other.month_of_year == self.month_of_year
                and other.day_of_month == self.day_of_month
                and other.day_of_week == self.day_of_week
                and other.hour == self.hour
                and other.minute == self.minute
                and other.tz == self.tz
            )
        return NotImplemented


class clocked(BaseSchedule):
    """clocked schedule.

    Depends on PeriodicTask one_off=True
    """

    def __init__(
        self,
        clocked_time: datetime,
        nowfun: Callable[[], datetime] = None,
        app: Celery = None,
    ) -> None:
        """Initialize clocked."""
        self.clocked_time = maybe_make_aware(clocked_time)
        super(clocked, self).__init__(nowfun=nowfun, app=app)

    def remaining_estimate(self, last_run_at: Optional[datetime]) -> timedelta:
        return self.clocked_time - self.now()

    def is_due(self, last_run_at: datetime) -> schedstate:
        rem_delta = self.remaining_estimate(None)
        remaining_s = max(rem_delta.total_seconds(), 0)
        if remaining_s == 0:
            return schedstate(is_due=True, next=NEVER_CHECK_TIMEOUT)
        return schedstate(is_due=False, next=remaining_s)

    def __repr__(self) -> str:
        return f"<clocked: {self.clocked_time}>"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, clocked):
            return self.clocked_time == other.clocked_time
        return False

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __reduce__(self) -> tuple:
        return self.__class__, (self.clocked_time, self.nowfun)
