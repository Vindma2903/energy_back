from pydantic import BaseModel, field_validator
from typing import Optional
from enum import Enum
from datetime import datetime


class MessageRole(str, Enum):
    LEAD = "LEAD"
    BOT = "BOT"
    MANAGER = "MANAGER"

    @classmethod
    def __get_pydantic_json_schema__(cls, schema, handler):
        """Позволяет FastAPI корректно отображать Enum в OpenAPI"""
        schema.update(type="string", enum=[role.value for role in cls])


class MessageCreate(BaseModel):
    text: str
    sender: str
    role: MessageRole  # ✅ Теперь Pydantic автоматически конвертирует строки в Enum
    session_id: Optional[str] = None

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        """Проверяем, что текст сообщения не пустой"""
        if not value.strip():
            raise ValueError("Текст сообщения не может быть пустым")
        return value


class MessageResponse(BaseModel):
    message: str
    session_id: str


class SessionCreate(BaseModel):
    user_id: str  # ID пользователя, создающего сессию


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    created_at: Optional[datetime] = None  # ✅ Вернем дату в формате ISO

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_datetime(cls, value):
        """Конвертируем строку в `datetime`, если нужно"""
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value
