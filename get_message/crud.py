from sqlalchemy import select, update, insert
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from uuid import uuid4
from messages.models import Message, Session, Lead
from get_message.schemas import MessageCreate
from logging_config import logger

# ✅ Создание нового сообщения
async def create_message(db: AsyncSession, message: MessageCreate):
    """
    Создаёт новое сообщение в базе данных. Если у пользователя нет активной сессии, создаёт новую.
    """
    logger.info(f"📩 Получено сообщение от {message.sender} в session_id: {message.session_id}")

    try:
        # ✅ Проверяем существующую сессию
        session = await get_session(db, message.session_id)
        if not session:
            logger.warning(f"⚠️ Сессия {message.session_id} не найдена. Создаём новую.")
            message.session_id = await create_session(db)

        # ✅ Обновляем время активности сессии
        await update_last_active(db, message.session_id)

        # ✅ Проверяем наличие лида (пользователя) в этой сессии
        lead = await get_lead_by_session(db, message.session_id)
        if not lead:
            logger.warning(f"⚠️ Лид для session_id {message.session_id} отсутствует! Создаём нового.")
            lead = await create_lead(db, message.session_id)

        # ✅ Сохраняем сообщение в БД
        db_message = Message(
            text=message.text,
            sender=message.sender,
            session_id=message.session_id,  # Привязываем к session_id
        )

        db.add(db_message)
        await db.commit()
        await db.refresh(db_message)

        logger.info(f"✅ Сообщение (ID: {db_message.id}) успешно создано для session_id: {message.session_id}")

        return {
            "id": db_message.id,
            "text": db_message.text,
            "sender": db_message.sender,
            "session_id": db_message.session_id,
            "lead": {
                "id": lead.id if lead else None,
                "first_name": lead.first_name if lead else "Неизвестный",
                "last_name": lead.last_name if lead else "",
            },
        }

    except Exception as e:
        logger.exception(f"❌ Ошибка при создании сообщения: {str(e)}")
        raise


# ✅ Получение лида по session_id
async def get_lead_by_session(db: AsyncSession, session_id: str):
    """
    Проверяет, существует ли лидер (пользователь) для данной сессии.
    """
    try:
        query = select(Lead).where(Lead.session_id == session_id)
        result = await db.execute(query)
        lead = result.scalars().first()

        if lead:
            logger.info(f"✅ Найден лид для session_id: {session_id} (ID: {lead.id})")
        else:
            logger.warning(f"⚠️ Лид для session_id: {session_id} не найден.")

        return lead
    except Exception as e:
        logger.exception(f"❌ Ошибка при получении лида для session_id {session_id}: {str(e)}")
        return None


# ✅ Создание нового лида
async def create_lead(db: AsyncSession, session_id: str):
    """
    Создаёт нового лида (пользователя), если он не был найден.
    """
    try:
        new_lead = Lead(
            first_name="Новый",
            last_name="Лид",
            session_id=session_id,
        )
        db.add(new_lead)
        await db.commit()
        await db.refresh(new_lead)
        logger.info(f"✅ Новый лид создан для session_id: {session_id}")
        return new_lead
    except Exception as e:
        logger.error(f"❌ Ошибка при создании лида: {str(e)}")
        raise


# ✅ Получение сообщений для session_id
async def get_messages_for_user(db: AsyncSession, session_id: str):
    """
    Возвращает список сообщений для конкретного пользователя (по session_id).
    """
    try:
        logger.info(f"📩 Извлечение сообщений для session_id: {session_id}")

        query = select(Message).where(Message.session_id == session_id)
        result = await db.execute(query)
        messages = result.scalars().all()

        logger.info(f"📦 Найдено {len(messages)} сообщений для session_id: {session_id}")
        return messages
    except Exception as e:
        logger.error(f"❌ Ошибка при извлечении сообщений: {str(e)}")
        raise


# ✅ Получение или создание новой сессии
async def get_or_create_session(db: AsyncSession, session_id: str) -> str:
    """
    Проверяет существование сессии. Если её нет, создаёт новую.
    """
    try:
        session = await get_session(db, session_id)
        if session:
            await update_last_active(db, session_id)
            return session_id
        else:
            return await create_session(db)
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке или создании сессии: {str(e)}")
        raise


# ✅ Получение сессии по session_id
async def get_session(db: AsyncSession, session_id: str):
    """
    Извлекает информацию о сессии из базы данных по session_id.
    """
    try:
        logger.info(f"🔍 Проверка сессии с session_id: {session_id}")
        query = select(Session).where(Session.session_id == session_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if session:
            logger.info(f"✅ Сессия найдена: {session_id}")
        else:
            logger.warning(f"⚠️ Сессия не найдена: {session_id}")

        return session
    except Exception as e:
        logger.error(f"❌ Ошибка при извлечении сессии: {str(e)}")
        raise


# ✅ Обновление времени последней активности сессии
async def update_last_active(db: AsyncSession, session_id: str):
    """
    Обновляет время последней активности сессии.
    """
    try:
        logger.info(f"⏳ Обновление времени активности для session_id: {session_id}")
        query = (
            update(Session)
            .where(Session.session_id == session_id)
            .values(last_active=datetime.utcnow())
        )
        await db.execute(query)
        await db.commit()
        logger.info(f"✅ Время активности обновлено для session_id: {session_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении активности: {str(e)}")
        raise


# ✅ Создание новой сессии
async def create_session(db: AsyncSession) -> str:
    """
    Создаёт новую сессию в базе данных.
    """
    try:
        new_session_id = str(uuid4())
        logger.info(f"🆕 Создание новой сессии: {new_session_id}")

        query = insert(Session).values(
            session_id=new_session_id,
            created_at=datetime.utcnow(),
            last_active=datetime.utcnow()
        )

        await db.execute(query)
        await db.commit()
        logger.info(f"✅ Новая сессия создана: {new_session_id}")
        return new_session_id
    except Exception as e:
        logger.error(f"❌ Ошибка при создании сессии: {str(e)}")
        raise
