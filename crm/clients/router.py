from fastapi import APIRouter, Depends, HTTPException  # Импортируем FastAPI роутер, зависимости и исключения
from starlette import status  # Импортируем HTTP-статусы

from crm.clients.logic import ClientLogic  # Импортируем логику работы с клиентами
from crm.clients.schemas import ClientCreateSchema  # Импортируем схему для валидации данных клиента
from dependency import get_client_logic  # Функция для получения зависимости `ClientLogic`
from exceptions import ClientNotFoundException  # Исключение, если клиент не найден

# Создаём API роутер с префиксом `/clients` и тегом `clients`
router = APIRouter(prefix='/clients', tags=['clients'])


@router.post('/')
async def create_client(
    data: ClientCreateSchema,  # Входные данные в формате схемы `ClientCreateSchema`
    client_logic: ClientLogic = Depends(get_client_logic)  # Внедряем зависимость для работы с клиентами
):
    """
    Создаёт нового клиента.
    :param data: Данные клиента (имя, фамилия, телефон, ИНН).
    :param client_logic: Объект бизнес-логики для работы с клиентами.
    :return: Созданный клиент.
    """
    return await client_logic.create_client(data)  # Вызываем метод создания клиента


@router.get('/')
async def get_all_clients(client_logic: ClientLogic = Depends(get_client_logic)):
    """
    Получает список всех клиентов.
    :param client_logic: Объект бизнес-логики для работы с клиентами.
    :return: Список клиентов.
    """
    return await client_logic.get_all_clients()  # Вызываем метод для получения всех клиентов


@router.get('/{client_id}')
async def get_client_by_id(
    client_id: int,  # ID клиента, передаваемый в URL
    client_logic: ClientLogic = Depends(get_client_logic)
):
    """
    Получает клиента по его ID.
    :param client_id: Уникальный идентификатор клиента.
    :param client_logic: Объект бизнес-логики для работы с клиентами.
    :return: Объект клиента или None, если клиент не найден.
    """
    return await client_logic.get_client_by_id(client_id)  # Вызываем метод получения клиента по ID


@router.delete('/{client_id}')
async def delete_client(
    client_id: int,  # ID клиента, передаваемый в URL
    client_logic: ClientLogic = Depends(get_client_logic)
):
    """
    Удаляет клиента по его ID.
    :param client_id: Уникальный идентификатор клиента.
    :param client_logic: Объект бизнес-логики для работы с клиентами.
    :raises HTTPException 404: Если клиент не найден.
    :return: None.
    """
    try:
        await client_logic.delete_client(client_id)  # Пытаемся удалить клиента
    except ClientNotFoundException as e:
        # Если клиент не найден, выбрасываем HTTP-исключение 404
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
