# ai_logics/schemas.py

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserMessage(BaseModel):
    session_id: int
    message_id: int
    text: str
    created_at: Optional[datetime] = None

    class Config:
        # Это гарантирует, что дата будет преобразована в строку ISO при выводе
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class UserMessageResponse(BaseModel):
    success: bool
    message: str
    data: Optional[UserMessage] = None
