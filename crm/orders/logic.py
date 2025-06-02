import datetime
from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import select  # SQL-запросы с SQLAlchemy
from sqlalchemy.ext.asyncio import AsyncSession  # Асинхронные сессии SQLAlchemy

from crm.orders.models import Order  # Импорт модели заказа
from crm.orders.schemas import OrderCreateSchema  # Импорт схемы для создания заказа
from exceptions import OrderNotFoundException  # Исключение, если заказ не найден


@dataclass
class OrderLogic:
    """
    Класс, содержащий бизнес-логику для работы с заказами.
    Выполняет CRUD-операции с заказами (создание, получение, удаление).
    """
    db_session: AsyncSession  # Асинхронная сессия базы данных

    async def create_order(self, data: OrderCreateSchema, user_id: int) -> Order:
        """
        Создаёт новый заказ в базе данных.

        :param data: Данные заказа (имя, описание, адрес, метод доставки, цена и т.д.).
        :param user_id: ID пользователя, который создаёт заказ.
        :return: Объект созданного заказа.
        """
        async with self.db_session as session:  # Открываем сессию
            order = Order(
                name=data.name,  # Название заказа
                description=data.description,  # Описание заказа
                date_of_creation=datetime.datetime.utcnow(),  # Дата создания (текущее UTC-время)
                date_of_send=datetime.datetime.utcnow() + datetime.timedelta(days=2),  # Дата отправки (2 дня спустя)
                address=data.address,  # Адрес доставки
                delivery_method=data.delivery_method,  # Метод доставки
                client_id=1,  # Клиент (захардкожен, вероятно, нужно изменить)
                price=data.price,  # Цена заказа
                author_id=user_id,  # Автор заказа (ID пользователя, создавшего заказ)
                responsable_id=user_id,  # Ответственный за заказ (ID пользователя, назначенного ответственным)
            )

            session.add(order)  # Добавляем заказ в сессию
            await session.commit()  # Фиксируем изменения в базе данных
            return order  # Возвращаем созданный заказ

    async def get_all_orders(self) -> Sequence[Order]:
        """
        Получает список всех заказов.

        :return: Список заказов.
        """
        async with self.db_session as session:
            query = select(Order)  # Создаём SQL-запрос на выборку всех заказов
            result = await session.execute(query)  # Выполняем запрос
            return result.scalars().all()  # Возвращаем список заказов

    async def get_order_by_id(self, order_id: int):
        """
        Получает заказ по его ID.

        :param order_id: Уникальный идентификатор заказа.
        :return: Объект заказа или None, если заказ не найден.
        """
        async with self.db_session as session:
            query = select(Order).where(Order.id == order_id)  # Фильтруем заказы по ID
            result = await session.execute(query)  # Выполняем запрос
            return result.scalar()  # Возвращаем один заказ или None, если не найден

    async def delete_order(self, order_id: int):
        """
        Удаляет заказ по его ID.

        :param order_id: Уникальный идентификатор заказа.
        :raises OrderNotFoundException: Если заказ не найден.
        """
        order = await self.get_order_by_id(order_id)  # Проверяем, существует ли заказ
        if not order:
            raise OrderNotFoundException  # Если заказ не найден, выбрасываем исключение

        if order.id == order_id:  # Проверяем ID перед удалением
            async with self.db_session as session:
                user = await session.scalar(select(Order).where(Order.id == order_id))  # Получаем заказ из БД
                await session.delete(user)  # Удаляем заказ
                await session.commit()  # Фиксируем изменения в БД
