from dataclasses import dataclass
from typing import List

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from users.auth.utils import pwd_context  # Утилита для работы с хешированием паролей
from users.models import User  # SQLAlchemy модель пользователя
from users.schemas import UserCreateSchema, UserUpdateSchema  # Схемы для валидации данных пользователя


@dataclass
class UserLogic:
    """Логика работы с пользователями в базе данных."""
    db_session: AsyncSession

    async def get_user_by_email(self, email: str) -> User | None:
        """
        Получить пользователя по email.

        :param email: Email пользователя.
        :return: Объект пользователя или None, если пользователь не найден.
        """
        query = select(User).where(User.email == email)
        async with self.db_session as session:
            result = (await session.execute(query)).scalar_one_or_none()
            return result

    async def get_all_users(self) -> List[User]:
        """
        Получить всех пользователей.

        :return: Список всех пользователей.
        """
        async with self.db_session as session:
            result = (await session.execute(select(User))).scalars().all()
            return result

    async def get_user_by_id(self, user_id: int) -> User | None:
        """
        Получить пользователя по ID.

        :param user_id: ID пользователя.
        :return: Объект пользователя или None, если пользователь не найден.
        """
        query = select(User).where(User.id == user_id)
        async with self.db_session as session:
            result = (await session.execute(query)).scalar_one_or_none()
            return result

    async def create_user(self, data: UserCreateSchema) -> User:
        """
        Создать нового пользователя.

        :param data: Данные для создания пользователя (схема UserCreateSchema).
        :return: Объект созданного пользователя.
        """
        query = (
            insert(User)
            .values(
                username=data.username,
                email=data.email,
                password=pwd_context.hash(data.password),  # Хешируем пароль перед сохранением
            )
            .returning(User)  # Возвращаем созданного пользователя
        )

        async with self.db_session as session:
            new_user = (await session.execute(query)).scalar()
            await session.commit()  # Подтверждаем изменения в базе данных
            return new_user

    async def change_user_password(self, user_id: int, password: str) -> User:
        """
        Изменить пароль пользователя.

        :param user_id: ID пользователя.
        :param password: Новый пароль.
        :return: Обновлённый объект пользователя.
        """
        query = select(User).where(User.id == user_id)
        async with self.db_session as session:
            user = (await session.execute(query)).scalar_one_or_none()
            if not user:
                raise ValueError("Пользователь не найден")
            user.password = pwd_context.hash(password)  # Хешируем новый пароль
            await session.commit()
            return user

    async def update_user(self, user_id: int, data: UserUpdateSchema) -> User:
        """
        Обновить данные пользователя.

        :param user_id: ID пользователя.
        :param data: Данные для обновления (схема UserUpdateSchema).
        :return: Обновлённый объект пользователя.
        """
        query = select(User).where(User.id == user_id)
        async with self.db_session as session:
            user = (await session.execute(query)).scalar_one_or_none()
            if not user:
                raise ValueError("Пользователь не найден")

            # Обновляем только переданные поля
            if data.name:
                user.name = data.name
            if data.surname:
                user.surname = data.surname
            if data.phone_number:
                user.phone_number = data.phone_number
            if data.email:
                user.email = data.email
            await session.commit()
            return user
