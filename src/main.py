from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import src.infra.db_listen  # noqa: F401
from src.api.auth import router as auth_router
from src.api.router import router
from src.infra.session import DBSessionMiddleware

app = FastAPI(title="My Tasks")

app.add_middleware(DBSessionMiddleware)

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Auth"],
)

app.include_router(router, prefix="/celery-beat")
