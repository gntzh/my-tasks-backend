from typing import Optional

from pydantic import BaseModel, EmailStr


class Register(BaseModel):
    username: str
    email: EmailStr
    password: str


class Login(BaseModel):
    username: str
    email: str


class LoginRes(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: Optional[int]
    scopes: list[str] = []
