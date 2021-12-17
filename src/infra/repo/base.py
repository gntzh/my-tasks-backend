from typing import Any, Generic, Optional, Protocol, Type, TypeVar, Union

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm.session import Session

from src.infra.session import get_session

# XXX For some partial updates, need to validate here.


class ModelBase(Protocol):
    id: Any


ModelT = TypeVar("ModelT", bound=ModelBase)
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)


class CRUDBase(Generic[ModelT, CreateSchemaT, UpdateSchemaT]):
    def __init__(self, model: Type[ModelT]) -> None:
        self.model = model

    def count(self, db: Session) -> int:
        return db.execute(select(func.count(self.model.id))).scalars().one()

    def get(self, id: Any, db: Session = None) -> Optional[ModelT]:
        return (
            (db or get_session()).execute(select(self.model).filter_by(id=id)).scalar()
        )

    def get_multi(
        self, *, skip: int = 0, limit: int = 100, db: Session = None
    ) -> list[ModelT]:
        return (
            (db or get_session())
            .execute(
                select(self.model)
                .order_by(self.model.id.desc())
                .offset(skip)
                .limit(limit)
            )
            .scalars()
            .all()
        )

    def create(self, obj_in: CreateSchemaT, db: Session = None) -> ModelT:
        obj_in_data = obj_in.dict()
        db_obj = self.model(**obj_in_data)
        (db := db or get_session()).add(db_obj)
        db.flush((db_obj,))
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db_obj: ModelT,
        obj_in: Union[UpdateSchemaT, dict[str, Any]],
        db: Session = None,
    ) -> ModelT:
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        (db := db or get_session()).add(db_obj)
        db.flush((db_obj,))
        db.refresh(db_obj)
        return db_obj

    def delete(self, id: int, db: Session = None) -> bool:
        db_obj = self.get(id=id, db=(db := db or get_session()))
        if db_obj is None:
            return False
        db.delete(db_obj)
        return True

    def get_or_create(
        self, defaults: dict[str, Any] = None, db: Session = None, **kwargs
    ) -> ModelT:
        db_obj = (
            (db := db or get_session())
            .execute(select(self.model).filter_by(**kwargs))
            .scalar()
        )
        if db_obj is None:
            kwargs |= defaults or {}
            db_obj = self.model(**kwargs)
            db.add(db_obj)
            db.flush((db_obj,))
            db.refresh(db_obj)
        return db_obj

    def update_or_create(
        self, defaults: dict[str, Any] = None, db: Session = None, **kwargs
    ) -> ModelT:
        db_obj = (
            (db := db or get_session())
            .execute(select(self.model).filter_by(**kwargs))
            .scalar()
        )
        if db_obj is None:
            kwargs |= defaults or {}
            db_obj = self.model(**kwargs)
            db.add(db_obj)
            db.flush((db_obj,))
        else:
            for field in kwargs:
                setattr(db_obj, field, kwargs[field])
        db.refresh(db_obj)
        return db_obj
