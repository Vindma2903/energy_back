import enum
from datetime import datetime

from passlib.context import CryptContext
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum

from infrastructure.database.base import Base

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserStatus(enum.Enum):
    CONFIRMED = "CONFIRMED"
    PENDING = "PENDING"
    BLOCKED = "BLOCKED"

    def __str__(self):
        return self.value


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    registration_date = Column(DateTime, default=datetime.utcnow)
    is_admin = Column(Boolean, default=False)

    status = Column(Enum(UserStatus), default=UserStatus.PENDING, nullable=False)
