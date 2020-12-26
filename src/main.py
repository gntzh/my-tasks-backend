from fastapi import FastAPI

import src.infra.db_listen  # noqa: F401
from src.api.router import router
from src.infra.session import DBSessionMiddleware

app = FastAPI()

app.add_middleware(DBSessionMiddleware)


app.include_router(router, prefix="/celery_beat")
