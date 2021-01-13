from sqlalchemy import Column, Integer, String
from sqlalchemy.sql.sqltypes import Boolean

from .mapper import Base


class User(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True)
    password = Column(String)
    email = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)
