from fastapi import FastAPI

import src.infra.db_listen  # noqa: F401
from src.api.auth import router as auth_router
from src.api.router import router
from src.infra.session import DBSessionMiddleware

app = FastAPI(title="My Tasks")

app.add_middleware(DBSessionMiddleware)


app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Auth"],
)

app.include_router(router, prefix="/celery-beat")
