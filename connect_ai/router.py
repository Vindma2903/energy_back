import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from connect_ai.schemas import UserMessage as UserMessageResponse
from messages.models import Message, Session as UserSession
from dependency import get_db
from uuid import UUID
import asyncio

# Настроим логирование
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/get_messages/{user_id}")
async def get_messages(
        user_id: str,
        db: AsyncSession = Depends(get_db)
):
    """Получение сообщений (без отправки в RabbitMQ)"""
    try:
        logger.info(f"🔍 Запрос сообщений для user_id: {user_id}")

        # Определение формата user_id
        user_id_uuid, user_id_is_uuid = None, False
        try:
            user_id_uuid = UUID(user_id.strip())
            user_id_is_uuid = True
        except ValueError:
            pass

        if user_id_is_uuid:
            sessions = (await db.execute(
                select(UserSession).where(UserSession.user_id == user_id_uuid)
            )).scalars().all()
        else:
            try:
                user_id_int = int(user_id.strip())
                sessions = (await db.execute(
                    select(UserSession).where(UserSession.user_id == user_id_int)
                )).scalars().all()
            except ValueError:
                logger.error("❌ Некорректный формат user_id")
                raise HTTPException(status_code=400, detail="Invalid user ID format")

        if not sessions:
            logger.warning(f"⚠️ Сессии не найдены для user_id: {user_id}")
            return {"status": "success", "message": "No sessions found", "messages": []}

        logger.info(f"📊 Найдено {len(sessions)} сессий")

        session_ids = [session.session_id for session in sessions]

        # Получение сообщений
        result = await db.execute(
            select(Message).where(
                Message.session_id.in_(session_ids),
                Message.role == 'LEAD'
            )
        )
        messages = result.scalars().all()

        if not messages:
            logger.warning(f"⚠️ Сообщения не найдены для user_id: {user_id}")
            return {"status": "success", "message": "No messages found", "messages": []}

        logger.info(f"💬 Найдено {len(messages)} сообщений")

        # Логируем полученные сообщения
        for msg in messages:
            logger.debug(f"Получено сообщение: {msg.id} - {msg.text}")

        # Формируем список сообщений для возвращения
        message_list = [{
            "session_id": msg.session_id,
            "message_id": msg.id,
            "text": msg.text,
            "created_at": msg.created_at.isoformat() if msg.created_at else None
        } for msg in messages]

        # Логируем список сообщений, которые будем возвращать
        logger.debug(f"Отправка следующих сообщений в ответ: {json.dumps(message_list, ensure_ascii=False)}")

        return {
            "status": "success",
            "message": f"Found {len(messages)} messages for user {user_id}",
            "messages": message_list
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"🔥 Критическая ошибка: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
