from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
import uuid
import logging

from infrastructure.database.config import get_db_session
from messages.models import Message, Session as UserSession, Lead, MessageRole
from messages.schemas import MessageCreate, MessageResponse
from sqlalchemy.orm import selectinload  # ✅ Используем selectinload
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from messages.schemas import SessionCreate, SessionResponse  # Импорт схем

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import uuid
import logging
import aio_pika
import json
from datetime import timedelta

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

SESSION_LIFETIME = timedelta(minutes=2) # Длительность активности сессии


# ✅ Функция для получения или создания сессии пользователя
async def get_or_create_session(user_id: str, db: AsyncSession) -> str:
    """
    Проверяет активную сессию для `user_id`. Если её нет или она устарела (более 2 минут),
    создаёт новую.
    """
    async with db.begin():
        result = await db.execute(select(UserSession).filter(UserSession.user_id == user_id))
        existing_session = result.scalars().first()

        if existing_session:
            # Проверяем, не истекла ли сессия (больше 2 минут)
            if datetime.utcnow() - existing_session.last_active > SESSION_LIFETIME:
                # Если сессия устарела, создаём новую
                logger.info(f"⏳ Сессия {existing_session.session_id} для пользователя {user_id} истекла, создаём новую...")
                return await create_new_session(user_id, db)
            else:
                # Обновляем `last_active` и возвращаем текущую сессию
                existing_session.last_active = datetime.utcnow()
                await db.commit()
                logger.info(f"🔄 Обновлена активная сессия: {existing_session.session_id} для пользователя {user_id}")
                return existing_session.session_id

        # Если нет активной сессии — создаём новую
        return await create_new_session(user_id, db)

async def create_new_session(user_id: str, db: AsyncSession) -> str:
    """
    Создаёт новую сессию для пользователя.
    """
    session_id = str(uuid.uuid4())
    new_session = UserSession(
        session_id=session_id,
        user_id=user_id,
        created_at=datetime.utcnow(),
        last_active=datetime.utcnow(),
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    logger.info(f"✅ Создана новая сессия: {new_session.session_id} для пользователя {user_id}")
    return new_session.session_id


# ✅ Получение всех сообщений по `session_id`
@router.get("/history/")
async def get_message_history(session_id: str, db: AsyncSession = Depends(get_db_session)):
    """
    Получает все сообщения, привязанные к `session_id`.
    """
    result = await db.execute(
        select(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.id.asc())  # Сообщения по порядку
    )
    messages = result.scalars().all()

    if not messages:
        raise HTTPException(status_code=404, detail="История сообщений не найдена")

    return {
        "messages": [{"text": msg.text, "sender": msg.sender} for msg in messages]
    }

@router.get("/leads/with-last-message")
async def get_chats_with_last_message(db: AsyncSession = Depends(get_db_session)):
    """
    Получает список сессий (чатов) с последним сообщением.
    """
    result = await db.execute(
        select(UserSession)
        .options(
            selectinload(UserSession.messages),  # ✅ Используем selectinload для коллекций
            selectinload(UserSession.lead)  # ✅ Загружаем лида
        )
    )

    sessions = result.unique().scalars().all()  # ✅ Добавляем .unique(), чтобы избежать проблемы с дублированием

    if not sessions:
        raise HTTPException(status_code=404, detail="Чаты не найдены")

    chats = []
    for session in sessions:
        last_message = session.messages[-1].text if session.messages else "Сообщений пока нет"
        last_message_time = session.messages[
            -1].created_at if session.messages else None  # Добавляем время последнего сообщения

        chats.append({
            "session_id": session.session_id,
            "lead": {
                "first_name": session.lead.first_name if session.lead else None,
                "last_name": session.lead.last_name if session.lead else None,
            },
            "last_message": last_message,
            "last_message_time": last_message_time.isoformat() if last_message_time else None
        })

    logger.info(f"📤 Отправлено {len(chats)} чатов")
    return chats


async def send_to_rabbitmq(message_data, db_session):
    RABBITMQ_URL = "amqp://localhost/"
    QUEUE_NAME = "message_queue"

    try:
        # 1. Сначала обновляем статус в БД (асинхронно)
        result = await db_session.execute(
            select(Message).where(Message.id == message_data["id"])
        )
        message = result.scalars().first()

        if not message:
            logger.error(f"❌ Сообщение {message_data['id']} не найдено в БД")
            return

        message.is_sent_to_rabbitmq = True
        await db_session.commit()
        logger.info(f"🔄 Статус сообщения {message_data['id']} обновлен на 'отправляется'")

        # 2. Затем отправляем в RabbitMQ
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=1)

            queue = await channel.declare_queue(QUEUE_NAME, durable=True)

            message_body = json.dumps(message_data)
            logger.info(f"📤 Отправляем сообщение в RabbitMQ: {message_body}")

            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=message_body.encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=QUEUE_NAME
            )

            logger.info(f"✅ Сообщение успешно отправлено в RabbitMQ: {message_body}")

    except Exception as e:
        # 3. Если ошибка - откатываем статус
        await db_session.rollback()
        logger.error(f"❌ Ошибка при отправке сообщения в RabbitMQ: {e}. Статус сообщения сброшен.")
        raise


# ✅ Получение или создание сессии + сохранение сообщения
@router.post("/", response_model=MessageResponse)
async def receive_message(message_data: MessageCreate, db: AsyncSession = Depends(get_db_session)):
    """
    Получает сообщение от пользователя, бота или менеджера, проверяет его сессию и сохраняет в БД.
    """

    if not message_data.session_id:
        raise HTTPException(status_code=400, detail="session_id обязателен")

    # Проверяем, существует ли сессия
    result = await db.execute(select(UserSession).filter(UserSession.session_id == message_data.session_id))
    session = result.scalars().first()

    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    # Создаем новое сообщение
    new_message = Message(
        text=message_data.text,
        sender=message_data.sender,
        role=message_data.role,
        session_id=message_data.session_id,
        created_at=datetime.utcnow()
    )

    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)

    # Отправляем в RabbitMQ только если не BOT
    if message_data.role != "BOT":
        message_data_for_rabbitmq = {
            "session_id": new_message.session_id,
            "id": new_message.id,
            "text": new_message.text,
            "sender": new_message.sender,
            "created_at": new_message.created_at.isoformat() if new_message.created_at else None
        }
        await send_to_rabbitmq(message_data_for_rabbitmq, db)
    else:
        logger.info(f"📦 Сообщение от бота не отправляется в RabbitMQ, id={new_message.id}")

    return {"message": "Сообщение принято", "session_id": message_data.session_id}


@router.get("/messages/by-session/{session_id}")
async def get_lead_and_bot_messages(session_id: str, db: AsyncSession = Depends(get_db_session)):
    """
    Получить все сообщения с ролями LEAD и BOT по session_id,
    отсортированные по времени создания.
    """
    result = await db.execute(
        select(Message)
        .filter(
            Message.session_id == session_id,
            Message.role.in_(["LEAD", "BOT"])
        )
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()

    if not messages:
        raise HTTPException(status_code=404, detail="Сообщения для данной сессии не найдены")

    return {
        "session_id": session_id,
        "messages": [
            {
                "id": msg.id,
                "text": msg.text,
                "sender": msg.sender,
                "role": msg.role.value if hasattr(msg.role, "value") else msg.role,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            }
            for msg in messages
        ]
    }


async def cleanup_expired_sessions(db: AsyncSession):
    """
    Очищает устаревшие сессии, которые не активировались более 2 минут.
    """
    cutoff_time = datetime.utcnow() - SESSION_LIFETIME
    result = await db.execute(select(UserSession).filter(UserSession.last_active < cutoff_time))
    expired_sessions = result.scalars().all()

    for session in expired_sessions:
        await db.delete(session)
        await db.commit()
        logger.info(f"❌ Сессия {session.session_id} для пользователя {session.user_id} была удалена (истекла)")


