from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from sqlalchemy.orm import Session

from src import schemas
from src.api.deps import get_current_user, get_db
from src.infra import security
from src.infra.repo.user import user_repo
from src.models.user import User
from src.config import settings

router = APIRouter()


@router.post("/", response_model=schemas.User)
def register(data: schemas.Register, uow: Session = Depends(get_db)) -> Any:
    with uow.begin():
        if user_repo.get_by_email(uow, email=data.email):
            raise HTTPException(status_code=400, detail="Email already registered")

        if user_repo.get_by_username(uow, username=data.username):
            raise HTTPException(status_code=400, detail="Username already registered")
        user = User()
        data.password = security.hash_password(data.password)
        user = User(**data.dict())
        uow.add(user)
    return user


@router.post("/login/token", response_model=schemas.LoginRes)
def token(
    data: OAuth2PasswordRequestForm = Depends(),
    uow: Session = Depends(get_db),
) -> Any:
    with uow.begin():
        user = user_repo.get_by_username(uow, username=data.username)
        if user is None or not security.verify_password(data.password, user.password):
            raise HTTPException(
                status_code=400, detail="Incorrect password or username"
            )
    return {
        "token_type": "bearer",
        "access_token": security.create_access_token(
            user.id,
            ["basic"],
        ),
        "refresh_token": security.create_refresh_token(
            user.id,
            ["basic"],
        ),
    }


@router.post("/token/refresh")
def refresh_token(
    refresh_token: str = Body(...),
    token_type: str = Body("bearer"),
    uow: Session = Depends(get_db),
) -> Any:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token_type.lower() != "bearer":
        raise credentials_exception
    try:
        payload: dict = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload["sub"]
    except (jwt.JWTError, KeyError):
        raise credentials_exception

    with uow.begin():
        user = user_repo.get(uow, id=user_id)
    if user is None:
        raise credentials_exception
    return {
        "token_type": "bearer",
        "access_token": security.create_access_token(user_id, ["basic"]),
    }


@router.get("/me", response_model=schemas.User)
def me(current_user: User = Security(get_current_user, scopes=["basic"])) -> Any:
    return current_user
