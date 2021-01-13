from typing import Optional, Type

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.infra.repo import CRUDBase
from src.models.user import User


class UserRepo(CRUDBase):
    def __init__(self, model: Type[User]) -> None:
        self.model = User

    def get(self, db: Session, *, id: int) -> Optional[User]:
        return db.execute(select(self.model).filter_by(id=id)).scalar()

    def get_by_username(self, db: Session, *, username: str) -> Optional[User]:
        return db.execute(select(self.model).filter_by(username=username)).scalar()

    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.execute(select(self.model).filter_by(email=email)).scalar()


user_repo = UserRepo(User)
