from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crm.clients.models import Client  # Импортируем модель клиента из базы данных
from crm.clients.schemas import ClientCreateSchema  # Импортируем схему для создания клиента
from exceptions import ClientNotFoundException  # Исключение, если клиент не найден


@dataclass
class ClientLogic:
    """
    Логика работы с клиентами в CRM.
    Использует асинхронные SQLAlchemy-сессии для работы с базой данных.
    """
    db_session: AsyncSession  # Асинхронная сессия для работы с БД

    async def create_client(self, data: ClientCreateSchema) -> Client:
        """
        Создает нового клиента в базе данных.
        :param data: Данные для создания клиента (имя, фамилия, телефон, ИНН).
        :return: Объект созданного клиента.
        """
        async with self.db_session as session:  # Открываем сессию
            client = Client(
                name=data.name,
                surname=data.surname,
                phone_number=data.phone_number,
                inn=data.inn
            )  # Создаем объект клиента

            session.add(client)  # Добавляем клиента в сессию
            await session.commit()  # Фиксируем изменения в БД
            return client  # Возвращаем созданного клиента

    async def get_all_clients(self) -> Sequence[Client]:
        """
        Получает список всех клиентов из базы данных.
        :return: Список клиентов.
        """
        async with self.db_session as session:
            query = select(Client)  # Запрос на выборку всех клиентов
            result = await session.execute(query)  # Выполняем запрос
            return result.scalars().all()  # Возвращаем список объектов клиентов

    async def get_client_by_id(self, client_id: int):
        """
        Получает клиента по его ID.
        :param client_id: Уникальный идентификатор клиента.
        :return: Объект клиента или None, если клиент не найден.
        """
        async with self.db_session as session:
            query = select(Client).where(Client.id == client_id)  # Фильтруем клиентов по ID
            result = await session.execute(query)  # Выполняем запрос
            return result.scalar()  # Возвращаем одного клиента или None

    async def delete_client(self, client_id: int):
        """
        Удаляет клиента по его ID.
        :param client_id: Уникальный идентификатор клиента.
        :raises ClientNotFoundException: Если клиент не найден.
        """
        client = await self.get_client_by_id(client_id)  # Проверяем, существует ли клиент
        if not client:
            raise ClientNotFoundException  # Если клиент не найден, выбрасываем исключение

        if client.id == client_id:  # Проверяем ID перед удалением
            async with self.db_session as session:
                user = await session.scalar(select(Client).where(Client.id == client_id))  # Получаем клиента из БД
                await session.delete(user)  # Удаляем клиента
                await session.commit()  # Фиксируем изменения
