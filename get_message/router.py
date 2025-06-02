import logging
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from database.database import get_db
from get_message.schemas import MessageCreate
from sqlalchemy import select, desc
from messages.models import Message, Session, Lead
from get_message.crud import (
    create_message,
    get_all_messages,
    get_session,
    update_last_active,
    create_session,
)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("messages_router")

# Создаем роутер для работы с сообщениями
router = APIRouter(
    prefix="/messages",
    tags=["Messages"]
)

SESSION_TIMEOUT = timedelta(hours=1)  # Длительность сессии — 1 час

# Проверка и обновление или создание новой сессии
async def get_or_create_session(session_id: str, db: AsyncSession) -> str:
    """
    Проверяет существование сессии. Если сессия активна, обновляет время последней активности.
    Если сессия устарела или не существует, создаёт новую.

    Параметры:
    - session_id: Уникальный идентификатор текущей сессии.
    - db: Асинхронная сессия базы данных.

    Возвращает:
    - Идентификатор активной или новой сессии.
    """
    logger.info(f"Checking session: {session_id}")
    session = await get_session(db, session_id)
    now = datetime.utcnow()

    if session and now - session.last_active < SESSION_TIMEOUT:
        logger.info(f"Session {session_id} is active. Updating last active time.")
        await update_last_active(db, session_id)
        return session_id
    else:
        if session:
            logger.warning(f"Session {session_id} is expired. Creating a new session.")
        else:
            logger.info(f"Session {session_id} not found. Creating a new session.")
        new_session_id = await create_session(db)
        logger.info(f"New session created: {new_session_id}")
        return new_session_id

# Маршрут для добавления нового сообщения
@router.post("/")
async def add_message(message: MessageCreate, db: AsyncSession = Depends(get_db)):
    """
    Добавляет новое сообщение в базу данных. Если у пользователя нет активной сессии, создаёт новую.
    """
    try:
        session_id = await get_or_create_session(db, message.session_id)
        message.session_id = session_id  # Обновляем session_id

        saved_message = await create_message(db, message)
        return saved_message
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Маршрут для получения всех сообщений для конкретной сессии
@router.get("/session/{session_id}")
async def list_messages_for_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    Извлекает список сообщений для указанной сессии.

    Параметры:
    - session_id: Уникальный идентификатор сессии.
    - db: Асинхронная сессия базы данных.

    Возвращает:
    - Список сообщений (JSON-массив) для указанной сессии.
    """
    try:
        logger.info(f"Fetching messages for session: {session_id}")
        # Проверяем корректность session_id как UUID
        try:
            UUID(session_id, version=4)
        except ValueError:
            logger.warning(f"Invalid session_id format: {session_id}")
            raise HTTPException(status_code=400, detail="Invalid session_id format")

        # Проверяем существование сессии в базе данных
        session = await get_session(db, session_id)
        if not session:
            logger.warning(f"Session not found: {session_id}")
            raise HTTPException(status_code=404, detail="Session not found")

        # Извлекаем сообщения, связанные с указанной сессией
        messages = await get_all_messages(db, session_id=session_id)
        logger.info(f"Retrieved {len(messages)} messages for session: {session_id}")
        return messages
    except Exception as e:
        logger.error(f"Error while fetching messages for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Маршрут для получения всех сообщений (не рекомендуется для больших данных)
@router.get("/")
async def list_all_messages(db: AsyncSession = Depends(get_db)):
    """
    Извлекает список всех сообщений из базы данных (без фильтрации).

    Параметры:
    - db: Асинхронная сессия базы данных.

    Возвращает:
    - Список всех сообщений (JSON-массив).
    """
    try:
        logger.info("Fetching all messages from the database")
        messages = await get_all_messages(db)
        logger.info(f"Retrieved {len(messages)} messages from the database")
        return messages
    except Exception as e:
        logger.error(f"Error while fetching all messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leads/with-last-message")
async def get_leads_with_last_message(db: AsyncSession = Depends(get_db)):
    """
    Возвращает список сессий с лидами и их последними сообщениями.
    """
    try:
        query = (
            select(
                Session.session_id,
                Lead.first_name,
                Lead.last_name,
            )
            .outerjoin(Lead, Lead.session_id == Session.session_id)
        )
        results = await db.execute(query)
        sessions = results.fetchall()

        leads_with_messages = []
        for session in sessions:
            # Подзапрос для последнего сообщения
            last_message_query = (
                select(Message.text)
                .where(Message.session_id == session.session_id)
                .order_by(desc(Message.id))
                .limit(1)
            )
            last_message_result = await db.execute(last_message_query)
            last_message = last_message_result.scalar()

            leads_with_messages.append(
                {
                    "session_id": session.session_id,
                    "lead": {"first_name": session.first_name, "last_name": session.last_name},
                    "last_message": last_message or "Сообщений пока нет",
                }
            )
        return leads_with_messages

    except Exception as e:
        logger.error(f"Error fetching leads with last messages: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch leads with last messages")


@router.get("/user/{user_id}")
async def get_messages_by_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """
    Извлекает список сообщений для указанного пользователя.

    Параметры:
    - user_id: Идентификатор пользователя.
    - db: Асинхронная сессия базы данных.

    Возвращает:
    - Список сообщений (JSON-массив) для указанного пользователя.
    """
    try:
        logger.info(f"Fetching messages for user: {user_id}")

        # Проверяем наличие сообщений для данного пользователя
        query = (
            select(Message)
            .where(Message.user_id == user_id)
            .order_by(desc(Message.created_at))
        )
        result = await db.execute(query)
        messages = result.scalars().all()

        if not messages:
            logger.warning(f"No messages found for user: {user_id}")
            raise HTTPException(status_code=404, detail="Messages not found")

        return [{"id": msg.id, "text": msg.text, "sender": msg.sender, "created_at": msg.created_at} for msg in messages]

    except Exception as e:
        logger.error(f"Error fetching messages for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch messages for user")