from typing import Any

from sqlalchemy.orm import declared_attr, registry
from src.utils import camel_to_snake


__all__ = ["Base", "mapper_registry"]


mapper_registry = registry()


@mapper_registry.as_declarative_base()
class Base(object):
    id: Any
    __tablename__: str

    @declared_attr
    def __tablename__(cls) -> str:
        return camel_to_snake(cls.__name__)
