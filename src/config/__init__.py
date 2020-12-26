from datetime import timedelta
from pathlib import Path

from pydantic import BaseSettings


class Settings(BaseSettings):
    BASE_DIR: Path = Path(__file__).resolve(strict=True).parent.parent.parent
    SECRET_KEY: str = "secrets.token_urlsafe(32)"
    # 60 minutes * 24 hours * 7 days = 7 days
    ACCESS_TOKEN_LIFETIME: timedelta = timedelta(minutes=30)
    REFRESH_TOKEN_LIFETIME: timedelta = timedelta(days=30)

    # SQLALCHEMY_DATABASE_URI: str = f"sqlite:///{BASE_DIR.as_posix()}/db.sqlite3"
    # SQLALCHEMY_DATABASE_URI = "postgresql://user:password@postgresserver/db"
    SQLALCHEMY_DATABASE_URI = "postgresql://webdev:123456@127.0.0.1:5432/celery_tasks"

    class Config:
        case_sensitive = True


settings = Settings()
