from datetime import timedelta
from pathlib import Path

from pydantic import BaseSettings

BASE_DIR: Path = Path(__file__).resolve(strict=True).parent.parent.parent


class Settings(BaseSettings):
    SECRET_KEY: str = "secrets.token_urlsafe(32)"

    ACCESS_TOKEN_LIFETIME: timedelta = timedelta(minutes=30)
    REFRESH_TOKEN_LIFETIME: timedelta = timedelta(days=30)
    JWT_ALGORITHM: str = "HS256"

    SQLALCHEMY_DATABASE_URI: str = f"sqlite:///{BASE_DIR.as_posix()}/db.sqlite3"

    class Config:
        case_sensitive = True
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"


settings = Settings()
