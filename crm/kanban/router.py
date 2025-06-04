import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from crm.orders.models import Order
from crm.clients.models import Client
from crm.orders.schemas import OrderCreateSchema
from dependency import get_orders_logic, get_request_user_id, get_db
from sqlalchemy.orm import selectinload

# Логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

router = APIRouter(prefix="/kanban", tags=["kanban"])


class WebSocketManager:
    """Менеджер WebSocket-соединений."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info(f"🔗 WebSocket клиент подключен: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logging.info(f"🔴 Клиент отключился: {websocket.client}")

    async def broadcast(self, message: str):
        logging.info(f"📢 Отправка сообщения всем клиентам: {message}")
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)


manager = WebSocketManager()


@router.post("/orders", response_model=dict)
async def create_order(
    order_data: OrderCreateSchema,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_request_user_id)
):
    """
    Создаёт новый заказ. Если клиента с таким телефоном нет – создаёт нового клиента.
    Если клиент уже есть – обновляет его имя.
    """
    logging.info(f"📌 Создание заказа: user_id={user_id}, column_id={order_data.column_id}")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется авторизация")

    async with db.begin():
        # 🔍 Найти клиента по телефону
        existing_client = await db.execute(
            select(Client).where(Client.phone_number == order_data.client_phone)
        )
        client = existing_client.scalar_one_or_none()

        if client:
            # 🔄 Обновляем имя, если оно отличается
            if client.name != order_data.client_name:
                logging.info(f"🔄 Обновляем имя клиента {client.phone_number} с '{client.name}' на '{order_data.client_name}'")
                client.name = order_data.client_name
                db.add(client)
        else:
            # 🆕 Создаем нового клиента
            client = Client(
                name=order_data.client_name,
                phone_number=order_data.client_phone
            )
            db.add(client)
            await db.flush()  # получаем client.id

        # ✅ Создаем заказ
        new_order = Order(
            name=order_data.name,
            description=order_data.description,
            date_of_creation=order_data.date_of_creation.replace(tzinfo=None),
            date_of_send=order_data.date_of_send.replace(tzinfo=None) if order_data.date_of_send else None,
            address=order_data.address,
            delivery_method=order_data.delivery_method,
            price=order_data.price,
            client_id=client.id,
            column_id=order_data.column_id,
            status="CREATED",
        )
        db.add(new_order)
        await db.flush()
        await db.refresh(new_order)

    return {
        "status": "success",
        "order": {
            "id": new_order.id,
            "name": new_order.name,
            "description": new_order.description,
            "date_of_creation": new_order.date_of_creation.isoformat(),
            "date_of_send": new_order.date_of_send.isoformat() if new_order.date_of_send else None,
            "address": new_order.address,
            "delivery_method": new_order.delivery_method.value,
            "client": {
                "id": client.id,
                "name": client.name,
                "phone": client.phone_number
            },
            "price": new_order.price,
            "status": new_order.status.value,
            "columnId": new_order.column_id,
        },
    }



@router.get("/orders", response_model=list[dict])
async def get_orders(db: AsyncSession = Depends(get_db)):
    """
    Возвращает список всех заказов с привязанными клиентами.
    """
    try:
        async with db.begin():
            result = await db.execute(
                select(Order).options(selectinload(Order.client))  # ✅ Загружаем клиента сразу
            )
            orders = result.scalars().all()

        orders_list = [
            {
                "id": order.id,
                "name": order.name,  # ✅ Название сделки
                "description": order.description,
                "date_of_creation": order.date_of_creation.isoformat(),
                "createdAt": order.date_of_creation.isoformat(),
                "date_of_send": order.date_of_send.isoformat() if order.date_of_send else None,
                "address": order.address,
                "delivery_method": order.delivery_method.value if order.delivery_method else None,
                "client": {
                    "id": order.client.id if order.client else None,
                    "name": order.client.name if order.client else "Не указан",
                    "phone": order.client.phone_number if order.client else "Не указан"
                } if order.client else None,  # ✅ Проверяем, есть ли клиент
                "price": order.price,
                "status": order.status.value if order.status else None,
                "columnId": order.column_id if order.column_id else "column-1"
            }
            for order in orders
        ]

        logging.info(f"📄 Отправляем {len(orders_list)} заказов в ответе")
        return orders_list

    except Exception as e:
        logging.error(f"❌ Ошибка при получении заказов: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении заказов"
        )
