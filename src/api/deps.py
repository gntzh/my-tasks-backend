from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from src.infra.session import SessionLocal
from src.infra.repo.user import user_repo
from src.models.user import User
from src.config import settings
from src import schemas

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl="/auth/token",
    scopes={
        "basic": "基础权限",
    },
)


def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(reusable_oauth2),
    uow: Session = Depends(get_db),
) -> User:
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        token_data = schemas.TokenPayload(**payload)
    except (jwt.JWTError, ValidationError):
        raise credentials_exception
    with uow.begin():
        user = user_repo.get(uow, id=token_data.sub)
    if user is None:
        raise credentials_exception
    if "all" in token_data.scopes:
        return user
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )
    return user
