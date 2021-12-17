from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import router
from src.infra.db_listen import listen_db
from src.infra.session import DBSessionMiddleware

app = FastAPI(title="My Tasks")

app.add_middleware(DBSessionMiddleware)
listen_db()

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

app.include_router(router)
