import logging

from fastapi import APIRouter, Depends
from starlette.requests import Request

from admin.logic import AdminLogic
from admin.schemas import ChangeUserStatusSchema
from admin.service import AdminService
from dependency import get_user_logic, get_admin_logic, get_admin_service
from users.logic import UserLogic
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.requests import Request

from dependency import get_user_logic, get_admin_service
from dependency import get_db_session as get_db

from users.logic import UserLogic
from admin.service import AdminService

# Создание маршрутизатора с префиксом "/admin" и тегом "admin"
router = APIRouter(prefix='/admin', tags=['admin'])
logger = logging.getLogger(__name__)

@router.get('/get_user/{user_id}')
async def get_user(request: Request,
                   user_id: int,
                   admin_service: AdminService = Depends(get_admin_service),
                   user_logic: UserLogic = Depends(get_user_logic)):
    """
    Получить данные пользователя по ID.
    - Проверяет административные привилегии текущего пользователя.
    - Возвращает данные пользователя по указанному user_id.

    :param request: Объект HTTP-запроса.
    :param user_id: ID пользователя, которого нужно получить.
    :param admin_service: Сервис для проверки прав администратора.
    :param user_logic: Логика работы с пользователями.
    :return: Данные пользователя.
    """
    admin_service.check_admin_privileges(request)  # Проверяем, что пользователь — администратор
    return await user_logic.get_user_by_id(user_id)  # Получаем данные пользователя




@router.get('/get_all_users')
async def get_all_users(
    request: Request,
    db: Session = Depends(get_db),
    admin_service: AdminService = Depends(get_admin_service),
    user_logic: UserLogic = Depends(get_user_logic)
):
    """
    Получить список всех пользователей.
    - Проверяет административные привилегии текущего пользователя.
    - Возвращает список всех пользователей.

    :param request: Объект HTTP-запроса.
    :param db: Сессия базы данных.
    :param admin_service: Сервис для проверки прав администратора.
    :param user_logic: Логика работы с пользователями.
    :return: Список всех пользователей.
    """
    try:
        # 🔐 Проверяем, является ли пользователь администратором
        admin_service.check_admin_privileges(request)

        logger.info("✅ Пользователь авторизован как администратор.")

        # 🔍 Получаем список пользователей
        users = await user_logic.get_all_users()
        if not users:
            logger.warning("⚠️ В базе данных нет пользователей!")
            raise HTTPException(status_code=404, detail="Пользователи не найдены.")

        logger.info("📋 Получен список пользователей:")

        # Подготавливаем список пользователей с логированием
        user_list = []
        for user in users:
            user_info = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "registrationDate": user.registration_date.isoformat(),
                "role": "admin" if user.is_admin else "user",
                "status": user.status.name
            }
            user_list.append(user_info)

            # Выводим в лог каждого пользователя
            logger.info(f"👤 {user.username} | Email: {user.email} | Админ: {user.is_admin}")

        return {"users": user_list, "last_updated": "now"}

    except HTTPException as http_exc:
        logger.error(f"❌ Ошибка: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception("💥 Внутренняя ошибка сервера при получении пользователей.")
        raise HTTPException(status_code=500, detail="Ошибка сервера")



@router.post('/change_user_status')
async def block_user(request: Request,
                     data: ChangeUserStatusSchema,
                     admin_logic: AdminLogic = Depends(get_admin_logic),
                     admin_service: AdminService = Depends(get_admin_service)):
    """
    Изменить статус пользователя.
    - Проверяет административные привилегии текущего пользователя.
    - Изменяет статус указанного пользователя (например, блокировка).

    :param request: Объект HTTP-запроса.
    :param data: Схема с данными для изменения статуса пользователя (user_id и новый статус).
    :param admin_logic: Логика работы администратора.
    :param admin_service: Сервис для проверки прав администратора.
    :return: Обновлённый статус пользователя.
    """
    admin_service.check_admin_privileges(request)  # Проверяем, что пользователь — администратор
    data = await admin_logic.change_user_status(data.user_id, data.status)  # Изменяем статус пользователя
    return data
