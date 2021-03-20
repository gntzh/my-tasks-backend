from typing import TYPE_CHECKING, Union

from sqlalchemy import insert, select, update
from sqlalchemy.event import listen

from src.models.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    ModelSchedule,
    PeriodicTask,
    PeriodicTasksChange,
)
from src.utils.timezone import utcnow

if TYPE_CHECKING:
    from sqlalchemy.engine.base import Connection
    from sqlalchemy.orm import Mapper


# Schedule and Periodic tasks tasks change
def update_changed(
    mapper: "Mapper",
    connection: "Connection",
    target: Union[ModelSchedule, PeriodicTask],
) -> None:
    if connection.execute(select(PeriodicTasksChange)).scalar() is None:
        connection.execute(insert(PeriodicTasksChange).values(last_update=utcnow()))
    else:
        connection.execute(update(PeriodicTasksChange).values(last_update=utcnow()))


def changed(mapper: "Mapper", connection: "Connection", target: PeriodicTask) -> None:
    if not target.no_changes:
        update_changed(mapper, connection, target)


def listen_db() -> None:
    listen(PeriodicTask, "after_delete", changed)
    listen(PeriodicTask, "after_insert", changed)
    listen(PeriodicTask, "after_update", changed)
    listen(IntervalSchedule, "after_insert", update_changed)
    listen(IntervalSchedule, "after_delete", update_changed)
    listen(IntervalSchedule, "after_update", update_changed)
    listen(CrontabSchedule, "after_insert", update_changed)
    listen(CrontabSchedule, "after_delete", update_changed)
    listen(CrontabSchedule, "after_update", update_changed)
    listen(ClockedSchedule, "after_insert", update_changed)
    listen(ClockedSchedule, "after_delete", update_changed)
    listen(ClockedSchedule, "after_update", update_changed)
