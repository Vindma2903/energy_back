from fastapi import Depends, security, Security, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from admin.logic import AdminLogic
from admin.service import AdminService
from crm.clients.logic import ClientLogic
from crm.orders.logic import OrderLogic
from exceptions import TokenExpiredException, TokenNotCorrectException
from infrastructure.database.config import get_db_session
from infrastructure.mail.service import MailService
from settings import Settings
from users.auth.service import AuthService
from users.logic import UserLogic

from fastapi import Depends, Request, Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import logging  # ✅ Добавляем импорт
from fastapi import WebSocketException
from fastapi import WebSocket

from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.database.config import get_db_session

async def get_db() -> AsyncSession:
    """Генерирует асинхронную сессию базы данных."""
    async for session in get_db_session():
        yield session



def get_settings():
    """
    Возвращает объект с настройками приложения.
    Используется для получения конфигурации приложения из `.env` файла.
    """
    return Settings()


def get_orders_logic(db_session: AsyncSession = Depends(get_db_session)) -> OrderLogic:
    """
    Возвращает объект логики работы с заказами.
    :param db_session: Асинхронная сессия подключения к базе данных.
    :return: Объект OrderLogic.
    """
    return OrderLogic(db_session=db_session)


def get_client_logic(db_session: AsyncSession = Depends(get_db_session)) -> ClientLogic:
    """
    Возвращает объект логики работы с клиентами.
    :param db_session: Асинхронная сессия подключения к базе данных.
    :return: Объект ClientLogic.
    """
    return ClientLogic(db_session=db_session)


def get_user_logic(db_session: AsyncSession = Depends(get_db_session)) -> UserLogic:
    """
    Возвращает объект логики работы с пользователями.
    :param db_session: Асинхронная сессия подключения к базе данных.
    :return: Объект UserLogic.
    """
    return UserLogic(db_session=db_session)


def get_mail_service(settings: Settings = Depends(get_settings),
                     user_logic: UserLogic = Depends(get_user_logic)) -> MailService:
    """
    Возвращает объект сервиса для работы с отправкой писем.
    :param settings: Объект настроек приложения.
    :param user_logic: Логика работы с пользователями.
    :return: Объект MailService.
    """
    return MailService(settings=settings, user_logic=user_logic)


def get_auth_service(user_logic: UserLogic = Depends(get_user_logic),
                     settings: Settings = Depends(get_settings)):
    """
    Возвращает объект сервиса аутентификации.
    :param user_logic: Логика работы с пользователями.
    :param settings: Объект настроек приложения.
    :return: Объект AuthService.
    """
    return AuthService(user_logic=user_logic, settings=settings)


reusable_oauth2 = security.HTTPBearer()


async def get_request_user_id(
    request: Request = None,
    websocket: WebSocket = None,
    auth_service: AuthService = Security(get_auth_service),
    token: HTTPAuthorizationCredentials = Security(reusable_oauth2),
    settings: Settings = Depends(get_settings),
) -> int:
    try:
        logging.info("🔍 [AUTH] Начинаем проверку токена...")
        if websocket:
            ws_token = websocket.query_params.get("token") or websocket.headers.get("Sec-WebSocket-Protocol")
            logging.info(f"🛂 [WebSocket] Проверка токена: {ws_token}")
            if not ws_token:
                logging.error("❌ [WebSocket] Токен не передан!")
                await websocket.close(code=1008)
                raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Токен не передан")
            try:
                user_id = auth_service.get_user_id_from_token(ws_token)
                logging.info(f"✅ [WebSocket] Авторизован user_id={user_id}")
                return user_id
            except JWTError as e:
                logging.error(f"❌ [WebSocket] Ошибка декодирования токена: {e}")
                await websocket.close(code=1008)
                raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Неверный токен")

        if token:
            token_str = token.credentials
            logging.info(f"🛂 [HTTP] Проверка токена: {token_str}")
            try:
                user_id = auth_service.get_user_id_from_token(token_str)
                logging.info(f"✅ [HTTP] Авторизован user_id={user_id}")
                return user_id
            except JWTError as e:
                logging.error(f"❌ [HTTP] Ошибка декодирования токена: {e}")
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Неверный токен")

        logging.error("❌ [AUTH] Токен не передан ни в WebSocket, ни в HTTP-запросе!")
        raise Exception("Токен не передан ни в WebSocket-запросе, ни в HTTP-запросе!")
    except Exception as e:
        logging.error(f"❌ [AUTH] Неожиданная ошибка: {e}")
        raise e





def get_admin_service(auth_service: AuthService = Depends(get_auth_service)):
    """
    Возвращает объект сервиса для работы с администраторами.
    :param auth_service: Сервис аутентификации.
    :return: Объект AdminService.
    """
    return AdminService(auth_service)


def get_admin_logic(db_session: AsyncSession = Depends(get_db_session),
                    user_logic: UserLogic = Depends(get_user_logic)):
    """
    Возвращает объект логики работы с администраторами.
    :param db_session: Асинхронная сессия подключения к базе данных.
    :param user_logic: Логика работы с пользователями.
    :return: Объект AdminLogic.
    """
    return AdminLogic(db_session=db_session, user_logic=user_logic)