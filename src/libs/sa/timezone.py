from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import FunctionElement
from sqlalchemy.types import DateTime, TypeDecorator

if TYPE_CHECKING:
    from sqlalchemy.engine import Dialect
    from sqlalchemy.sql.compiler import SQLCompiler


# Refer to
# https://docs.sqlalchemy.org/en/14/core/compiler.html#utc-timestamp-function
class utcnow(FunctionElement):
    type = DateTime()


@compiles(utcnow, "postgresql")
def pg_utcnow(element: FunctionElement, compiler: "SQLCompiler", **kw: dict) -> str:
    return "TIMEZONE('utc', CURRENT_TIMESTAMP)"


@compiles(utcnow, "sqlite")
def sl_utcnow(element: FunctionElement, compiler: "SQLCompiler", **kw: dict) -> str:
    return "DATETIME('now')"


@compiles(utcnow, "mssql")
def ms_utcnow(element: FunctionElement, compiler: "SQLCompiler", **kw: dict) -> str:
    return "GETUTCDATE()"


@compiles(utcnow, "mysql")
def my_utcnow(element: FunctionElement, compiler: "SQLCompiler", **kw: dict) -> str:
    return "UTC_TIMESTAMP()"


# Refer to
# https://docs.sqlalchemy.org/en/14/core/custom_types.html#store-timezone-aware-timestamps-as-timezone-naive-utc
class TZDateTime(TypeDecorator):
    impl = DateTime(timezone=False)
    cache_ok = True

    def process_bind_param(
        self, value: Optional[datetime], dialect: "Dialect"
    ) -> Optional[datetime]:
        if value is not None:
            if value.tzinfo is None:
                raise TypeError("tzinfo is required")
            else:
                value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(
        self, value: Optional[datetime], dialect: "Dialect"
    ) -> Optional[datetime]:
        if value is not None:
            value = value.replace(tzinfo=timezone.utc)
        return value
