from sqlalchemy import insert, select, update
from sqlalchemy.event import listen

from src.models import CrontabSchedule, IntervalSchedule, PeriodicTask, PeriodicTasks
from src.utils.timezone import utcnow


class PeriodicTasksChange:
    # Periodic tasks change
    @classmethod
    def changed(cls, mapper, connection, target) -> None:
        if not target.no_changes:
            cls.update_changed(mapper, connection, target)

    # Schedule and Periodic tasks tasks change
    @classmethod
    def update_changed(cls, mapper, connection, target) -> None:
        if connection.execute(select(PeriodicTasks)).scalar() is None:
            connection.execute(insert(PeriodicTasks).values(last_update=utcnow()))
        else:
            connection.execute(update(PeriodicTasks).values(last_update=utcnow()))


listen(PeriodicTask, "after_delete", PeriodicTasksChange.changed)
listen(PeriodicTask, "after_insert", PeriodicTasksChange.changed)
listen(PeriodicTask, "after_update", PeriodicTasksChange.changed)
listen(IntervalSchedule, "after_insert", PeriodicTasksChange.update_changed)
listen(IntervalSchedule, "after_delete", PeriodicTasksChange.update_changed)
listen(IntervalSchedule, "after_update", PeriodicTasksChange.update_changed)
listen(CrontabSchedule, "after_insert", PeriodicTasksChange.update_changed)
listen(CrontabSchedule, "after_delete", PeriodicTasksChange.update_changed)
listen(CrontabSchedule, "after_update", PeriodicTasksChange.update_changed)
