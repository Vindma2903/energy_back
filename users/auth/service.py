import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from jose import jwt, JWTError
from starlette.requests import Request

from exceptions import UserNotFoundException, UserNotCorrectPasswordException, TokenNotCorrectException, \
    TokenExpiredException, UserNotConfirmedByAdminException, AccessTokenNotFound, UserNotAdminException
from settings import Settings
from users.auth.utils import pwd_context
from users.logic import UserLogic
from users.models import User
from users.schemas import UserAuthenticatedSchema

logger = logging.getLogger(__name__)


@dataclass
class AuthService:
    user_logic: UserLogic
    settings: Settings

    async def login(self, email: str, password: str) -> UserAuthenticatedSchema:
        logger.info(f"Попытка авторизации: {email}")

        user = await self.user_logic.get_user_by_email(email)

        if user:
            logger.info(f"Пользователь найден: {user.email}")
        else:
            logger.error("Пользователь не найден")
            raise UserNotFoundException

        self._validate_user(user, password)
        logger.info("Пароль успешно проверен")

        access_token = self.generate_access_token(user.id, user.is_admin)
        logger.info(f"Токен доступа создан: {access_token}")

        return UserAuthenticatedSchema(
            user_id=user.id,
            username=user.username,  # ✅ Добавлено
            email=user.email,  # ✅ Добавлено
            access_token=access_token
        )

    @staticmethod
    def _validate_user(user: User, password: str):
        if not user:
            logger.error("User not found")
            raise UserNotFoundException
        logger.info("User found, verifying password")
        if not pwd_context.verify(password, user.password):
            logger.error("Password verification failed")
            raise UserNotCorrectPasswordException("Incorrect password.")
        logger.info("Password verified successfully")
        if str(user.status) != "CONFIRMED":
            raise UserNotConfirmedByAdminException

    def generate_access_token(self, user_id: int, is_admin: bool) -> str:
        expire_time_unix = (datetime.utcnow() + timedelta(days=7)).timestamp()
        token = jwt.encode({'user_id': user_id,
                            'is_admin': is_admin,
                            'expire': expire_time_unix},
                           self.settings.JWT_SECRET_KEY,
                           algorithm=self.settings.JWT_DECODE_ALGORITHM)
        return token

    def get_user_id_from_token(self, token: str) -> int:
        try:
            payload = jwt.decode(token, self.settings.JWT_SECRET_KEY, algorithms=[self.settings.JWT_DECODE_ALGORITHM])
        except:
            raise TokenNotCorrectException
        if payload['expire'] > (datetime.utcnow() + timedelta(days=7)).timestamp():
            raise TokenExpiredException
        return payload['user_id']

    def user_is_admin(self, request: Request) -> None:
        try:

            access_token = request.session.get("access_token")
            if not access_token:
                logger.warning("Access token not found in session")
                raise AccessTokenNotFound

            payload = jwt.decode(access_token, self.settings.JWT_SECRET_KEY,
                                 algorithms=[self.settings.JWT_DECODE_ALGORITHM])
            is_admin_flag = payload.get("is_admin")

            if is_admin_flag is None:
                logger.warning("is_admin flag not found in token")
                raise TokenNotCorrectException

            if not is_admin_flag:
                raise UserNotAdminException
            return
        except JWTError as e:
            logger.error(f"JWT decoding error: {str(e)}")
            raise TokenNotCorrectException
