# rabbit/schemas.py
from pydantic import BaseModel

# Модель для принятия сообщения
class MessageRequest(BaseModel):
    message: str  # Поле для сообщения
