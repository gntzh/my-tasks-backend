from datetime import datetime, timedelta
from typing import Any, Union

from jose import jwt
from passlib.context import CryptContext

from src.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: Union[str, Any],
    scopes: list = None,
    lifetime: timedelta = None,
) -> str:
    scopes = [] if scopes is None else scopes
    expire = datetime.utcnow() + (lifetime or settings.ACCESS_TOKEN_LIFETIME)
    to_encode = {"exp": expire, "sub": str(subject), "scopes": scopes, "type": "access"}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any],
    scopes: list = None,
    lifetime: timedelta = None,
) -> str:
    scopes = [] if scopes is None else scopes
    expire = datetime.utcnow() + (lifetime or settings.REFRESH_TOKEN_LIFETIME)
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "scopes": scopes,
        "type": "refresh",
    }
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)
