from contextvars import ContextVar
from typing import Optional

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
    Response,
)

from src.config import settings

__all__ = (
    "engine",
    "create_session",
    "get_session",
    "DBSessionMiddleware",
    "SessionHolder",
)

engine = create_engine(settings.SQLALCHEMY_DATABASE_URI, future=True)

session_holder_var: ContextVar["SessionHolder"] = ContextVar("session_holder")


def create_session() -> Session:
    return Session(engine, future=True)


def get_session(session: Session = None) -> Session:
    return session or session_holder_var.get().session


class SessionHolder:
    _session: Optional[Session] = None

    @property
    def is_set(self) -> bool:
        return self._session is not None

    @property
    def session(self) -> Session:
        if self._session is None:
            self._session = create_session()
        return self._session

    def cleanup(self) -> None:
        if self._session is not None:
            self._session.close()


class DBSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        token = session_holder_var.set(SessionHolder())
        res = await call_next(request)
        session_holder_var.get().cleanup()
        session_holder_var.reset(token)
        return res
