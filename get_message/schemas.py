from pydantic import BaseModel

class MessageCreate(BaseModel):
    """
    Схема Pydantic для создания сообщения.

    Поля:
    - text: Текст сообщения.
    - sender: Отправитель ("user" или "bot").
    - session_id: Уникальный идентификатор сессии пользователя.
    """
    text: str
    sender: str  # "user" или "bot"
    session_id: str  # Уникальный идентификатор сессии

    class Config:
        from_attributes = True
