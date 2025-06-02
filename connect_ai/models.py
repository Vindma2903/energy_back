from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from infrastructure.database.base import Base  # ✅ Путь к базовому классу моделей

class UserMessage(Base):
    __tablename__ = "user_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)  # Внешний ключ на session_id
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)  # Внешний ключ на сообщения
    text = Column(Text, nullable=False)  # Текст сообщения
    created_at = Column(DateTime, default=datetime.utcnow)  # Время создания сообщения

    # Связь с таблицей `messages`
    message = relationship("Message", backref="user_messages", lazy="select")

    # Связь с таблицей `sessions`
    session = relationship("Session", backref="user_messages", lazy="select")

    def __repr__(self):
        return f"<UserMessage(id={self.id}, session_id={self.session_id}, message_id={self.message_id}, created_at={self.created_at})>"
