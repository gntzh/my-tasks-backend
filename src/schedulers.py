import logging
import math
from datetime import datetime
from multiprocessing.util import Finalize
from typing import Any, Generic, Optional, Type, TypeVar

from celery import Celery, current_app, schedules
from celery.beat import ScheduleEntry, Scheduler
from celery.utils.log import get_logger
from celery.utils.time import maybe_make_aware
from kombu.utils.encoding import safe_repr, safe_str
from kombu.utils.json import dumps, loads
from sqlalchemy.orm import sessionmaker
from src.infra.repo import (
    crontab_schedule_repo,
    interval_schedule_repo,
    periodic_task_repo,
    periodic_tasks_repo,
)
from src.infra.session import engine
from src.models import ModelSchedule, PeriodicTask, PeriodicTasks
from src.tz_crontab import TZCrontab

NEVER_CHECK_TIMEOUT = 100000000

# This scheduler must wake up more frequently than the
# regular of 5 minutes because it needs to take external
# changes to the schedule into account.
DEFAULT_MAX_INTERVAL = 5  # seconds

ADD_ENTRY_ERROR = """\
Cannot add entry %r to database schedule: %r. Contents: %r
"""

# Bootstrap
from src.infra import db_listen  # noqa: F401, E402

logger = get_logger(__name__)
debug, info, warning = logger.debug, logger.info, logger.warning

SessionLocal = sessionmaker(
    engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True
)


class ModelEntry(ScheduleEntry):

    model_schedules = (
        # schedule_type, repo, model_field
        (schedules.crontab, crontab_schedule_repo, "crontab_id"),
        (schedules.schedule, interval_schedule_repo, "interval_id"),
        # (schedules.solar, SolarSchedule, 'solar_id'),
        # (clocked, ClockedSchedule, 'clocked_id')
    )
    save_fields = ["last_run_at", "total_run_count", "no_changes"]

    def __init__(self, model_task: PeriodicTask, app: Celery = None):
        self.app = app or current_app
        self.name = model_task.name
        self.task = model_task.task
        self.schedule = model_task.schedule
        self.model = model_task

        try:
            self.args = loads(model_task.args or "[]")
            self.kwargs = loads(model_task.kwargs or "{}")
        except ValueError as exc:
            logger.exception(
                "Removing schedule %s for argument deseralization error: %r",
                self.name,
                exc,
            )
            self._disable(model_task)

        self.options = {}
        for option in ("queue", "exchange", "routing_key", "priority"):
            value = getattr(model_task, option)
            if value is None:
                continue
            self.options[option] = value

        if getattr(model_task, "expires_", None):
            self.options["expires"] = getattr(model_task, "expires_")

        self.options["headers"] = loads(model_task.headers or "{}")

        self.total_run_count = model_task.total_run_count

        if not model_task.last_run_at:
            model_task.last_run_at = self._default_now()

        self.last_run_at = model_task.last_run_at

    def _disable(self, model_task: PeriodicTask) -> None:
        # task filed error, don't trigger the change
        with SessionLocal().begin() as session:
            session.add(model_task)
            model_task.disable_error_task()

    def is_due(self) -> schedules.schedstate:
        # 供 scheduler.is_due(entry) 调用

        if not self.model.enabled:
            # 5 second delay for re-enable.
            return schedules.schedstate(False, 5.0)

        # START DATE: only run after the `start_time`, if one exists.
        if self.model.start_time is not None:
            now = self._default_now()
            if now < self.model.start_time:
                # The datetime is before the start date - don't run.
                # send a delay to retry on start_time
                delay = math.ceil((self.model.start_time - now).total_seconds())
                return schedules.schedstate(False, delay)

        # ONE OFF TASK: Disable one off tasks after they've ran once
        if self.model.one_off and self.model.enabled and self.model.total_run_count > 0:
            with SessionLocal.begin() as session:
                session.add(self.model)
                self.model.enabled = False
                self.model.total_run_count = 0  # Reset
                self.model.no_changes = False  # Mark the model entry as changed
            # Don't recheck
            return schedules.schedstate(False, NEVER_CHECK_TIMEOUT)

        # CAUTION: make_aware assumes settings.TIME_ZONE for naive datetimes,
        # while maybe_make_aware assumes utc for naive datetimes
        tz = self.app.timezone
        last_run_at_in_tz = maybe_make_aware(self.last_run_at).astimezone(tz)
        return self.schedule.is_due(last_run_at_in_tz)

    def _next_instance(self, last_run_at: datetime = None) -> "ModelEntry":
        self.model.last_run_at = last_run_at or self._default_now()
        self.model.total_run_count += 1
        self.model.no_changes = True
        return self.__class__(self.model)

    __next__ = next = _next_instance  # for 2to3

    def save(self) -> None:
        # Object may not be synchronized, so only
        # change the fields we care about.
        with SessionLocal.begin() as session:
            for field in self.save_fields:
                setattr(self.model, field, getattr(self.model, field))
            session.add(self.model)

    @classmethod
    def to_model_schedule(
        cls, schedule: schedules.BaseSchedule
    ) -> tuple[ModelSchedule, str]:
        for schedule_type, repo, model_field in cls.model_schedules:
            schedule = schedules.maybe_schedule(schedule)
            if isinstance(schedule, schedule_type):
                with SessionLocal.begin() as session:
                    model_schedule = repo.from_celery_schedule(schedule, db=session)
                return model_schedule, model_field
        raise ValueError("Cannot convert schedule type {0!r} to model".format(schedule))

    @classmethod
    def from_entry(cls, name: str, app: Celery = None, **entry_fields) -> "ModelEntry":
        # XXX Sessions connect too frequently
        with SessionLocal.begin() as session:
            model_task = periodic_task_repo.update_or_create(
                name=name, defaults=cls._unpack_fields(**entry_fields), db=session
            )
            return cls(model_task, app=app)

    @classmethod
    def _unpack_fields(
        cls,
        schedule: schedules.BaseSchedule,
        args: list = None,
        kwargs: dict = None,
        relative: bool = None,
        options: dict = None,
        **entry_fields
    ) -> dict[str, Any]:
        model_schedule, model_field = cls.to_model_schedule(schedule)
        entry_fields.update(
            {model_field: model_schedule.id},
            args=dumps(args or []),
            kwargs=dumps(kwargs or {}),
            **cls._unpack_options(**options or {})
        )
        return entry_fields

    @classmethod
    def _unpack_options(
        cls,
        queue: str = None,
        exchange: str = None,
        routing_key: str = None,
        priority: int = None,
        headers: dict = None,
        expire_seconds: int = None,
        **kwargs
    ) -> dict[str, Any]:
        return {
            "queue": queue,
            "exchange": exchange,
            "routing_key": routing_key,
            "priority": priority,
            "headers": dumps(headers or {}),
            "expire_seconds": expire_seconds,
        }

    def __repr__(self) -> str:
        return "<ModelEntry: {0} {1}(*{2}, **{3}) {4}>".format(
            safe_str(self.name),
            self.task,
            safe_repr(self.args),
            safe_repr(self.kwargs),
            self.schedule,
        )


EntryT = TypeVar("EntryT", bound=ModelEntry)
ScheduleData = dict[str, EntryT]


class DatabaseScheduler(Scheduler, Generic[EntryT]):
    app: Celery
    Entry: Type[EntryT] = ModelEntry
    Model: Type[PeriodicTask] = PeriodicTask
    Changes: Type[PeriodicTasks] = PeriodicTasks

    _schedule: Optional[ScheduleData] = None
    _last_timestamp: Optional[datetime] = None
    _initial_read: bool = True
    _heap_invalidated: bool = False

    _heap: list

    def __init__(self, *args, **kwargs) -> None:
        self._dirty: set = set()
        super().__init__(*args, **kwargs)
        self._finalize = Finalize(self, self.sync, exitpriority=5)
        self.max_interval = (
            kwargs.get("max_interval")
            or self.app.conf.beat_max_loop_interval
            or DEFAULT_MAX_INTERVAL
        )

    def setup_schedule(self) -> None:
        self.install_default_entries(self.schedule)
        self.update_from_dict(self.app.conf.beat_schedule)

    def all_as_schedule(self) -> ScheduleData:
        debug("DatabaseScheduler: Fetching database schedule")
        s = {}
        with SessionLocal.begin() as session:
            model_tasks = periodic_task_repo.get_enabled(db=session)
            # session.expunge_all()  # 分离，持久化
            for model_task in model_tasks:
                try:
                    s[model_task.name] = self.Entry(model_task, app=self.app)
                except ValueError:
                    pass
        return s

    def schedule_changed(self) -> bool:
        with SessionLocal.begin() as session:
            last = self._last_timestamp
            ts = periodic_tasks_repo.get(db=session).last_update
            try:
                if ts and ts > (last if last else ts):
                    return True
            finally:
                self._last_timestamp = ts
            return False

    def reserve(self, entry: EntryT) -> EntryT:
        new_entry: EntryT = next(entry)  # TODO 移除 __next__
        # Need to store entry by name, because the entry may change
        # in the mean time.
        self._dirty.add(new_entry.name)
        return new_entry

    def sync(self) -> None:
        if logger.isEnabledFor(logging.DEBUG):
            debug("Writing entries...")
        _tried = set()
        _failed = set()
        # TODO Improve exception handling. Refer to:
        # https://sourcegraph.com/github.com/celery/django-celery-beat/-/blob/django_celery_beat/schedulers.py#L295
        try:
            while self._dirty:
                name = self._dirty.pop()
                try:
                    self.schedule[name].save()
                    _tried.add(name)
                except KeyError:
                    _failed.add(name)
        finally:
            # retry later, only for the failed ones
            self._dirty |= _failed

    def update_from_dict(self, mapping: dict[str, dict[str, Any]]) -> None:
        s = {}
        for name, entry_fields in mapping.items():
            try:
                entry = self.Entry.from_entry(name, app=self.app, **entry_fields)
                if entry.model.enabled:
                    s[name] = entry
            except Exception as exc:
                logger.exception(ADD_ENTRY_ERROR, name, exc, entry_fields)
        self.schedule.update(s)

    def install_default_entries(self, data: ScheduleData) -> None:
        # "data" is not accessed, maybe for compatibility
        entries: dict = {}
        if self.app.conf.result_expires:
            entries.setdefault(
                "celery.backend_cleanup",
                {
                    "task": "celery.backend_cleanup",
                    "schedule": TZCrontab("0", "4", "*"),
                    "options": {"expire_seconds": 12 * 3600},
                },
            )
        self.update_from_dict(entries)

    def schedules_equal(self, *args, **kwargs) -> bool:
        if self._heap_invalidated:
            self._heap_invalidated = False
            return False
        return super(DatabaseScheduler, self).schedules_equal(*args, **kwargs)

    @property
    def schedule(self) -> ScheduleData:
        initial = update = False
        if self._initial_read:
            debug("DatabaseScheduler: initial read")
            initial = update = True
            self._initial_read = False
        elif self.schedule_changed():
            info("DatabaseScheduler: Schedule changed.")
            update = True

        if update:
            self.sync()
            self._schedule = self.all_as_schedule()
            # the schedule changed, invalidate the heap in Scheduler.tick
            if not initial:
                self._heap = []
                self._heap_invalidated = True
            if logger.isEnabledFor(logging.DEBUG):
                debug(
                    "Current schedule:\n%s",
                    "\n".join(repr(entry) for entry in self._schedule.values()),
                )
        return self._schedule
