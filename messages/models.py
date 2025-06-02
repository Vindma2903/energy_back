from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum,Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from infrastructure.database.base import Base  # ✅ Путь к базовому классу моделей
import enum
from sqlalchemy import Enum as SQLAlchemyEnum

class MessageRole(enum.Enum):
    LEAD = "LEAD"
    BOT = "BOT"
    MANAGER = "MANAGER"

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    sender = Column(String(36), nullable=False)
    role = Column(SQLAlchemyEnum(MessageRole, name="message_role", create_type=False), nullable=False)
    session_id = Column(String, ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_sent_to_rabbitmq = Column(Boolean, default=False, nullable=False, server_default='false')
    is_processed_by_bot = Column(Boolean, default=False, nullable=False)  # Добавленное поле

    session = relationship("Session", back_populates="messages")



class Session(Base):
    """
    Таблица для хранения данных о сессиях пользователей.

    Поля:
    - id: Уникальный идентификатор сессии.
    - session_id: Уникальный идентификатор сессии (UUID).
    - user_id: Идентификатор пользователя (используется для отслеживания сессии).
    - created_at: Время создания сессии.
    - last_active: Время последней активности пользователя.
    """
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)  # ID записи
    session_id = Column(String, unique=True, nullable=False)  # Уникальный идентификатор сессии
    user_id = Column(String, nullable=False, index=True)  # ID пользователя, привязанный к сессии
    created_at = Column(DateTime, default=datetime.utcnow)  # Время создания сессии
    last_active = Column(DateTime, default=datetime.utcnow)  # Время последнего взаимодействия

    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    lead = relationship("Lead", back_populates="session", uselist=False, cascade="all, delete-orphan")  # Один `Lead` на `Session`


class Lead(Base):
    """
    Таблица для хранения данных о лидах (контактах пользователей).

    Поля:
    - id: Уникальный идентификатор лида.
    - first_name: Имя лида (может быть `NULL`).
    - last_name: Фамилия лида (может быть `NULL`).
    - session_id: Идентификатор сессии (внешний ключ).
    """
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)  # Уникальный идентификатор лида
    first_name = Column(String, nullable=True)  # Имя лида
    last_name = Column(String, nullable=True)  # Фамилия лида
    session_id = Column(String, ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)  # ✅ Убрали `unique=True`

    session = relationship("Session", back_populates="lead")  # Связь с `Session`


