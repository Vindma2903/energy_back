from dataclasses import dataclass

from fastapi import HTTPException
from fastapi_mail import MessageSchema, FastMail
from itsdangerous import URLSafeTimedSerializer

from exceptions import MailNotSendedException
from infrastructure.mail.config import mail_config
from settings import Settings
from users.logic import UserLogic
from users.models import User


@dataclass
class MailService:
    settings: Settings
    user_logic: UserLogic

    async def send_confirmation_email(self, user: User):
        try:

            subject = "Подтверждение учетной записи"
            body = (
                f"Здравствуйте, {user.username}!\n\n"
                f"Ожидайте подтверждение вашей учетной записи администратором"

            )
            message = MessageSchema(
                subject=subject,
                recipients=[user.email],
                body=body,
                subtype="plain",
            )

            fm = FastMail(mail_config)
            await fm.send_message(message)
        except MailNotSendedException as e:
            raise HTTPException(status_code=500, detail=e.detail)

    def get_reset_password_token(self, email: str) -> str:
        serializer = URLSafeTimedSerializer(self.settings.MAIL_SECRET_KEY)
        token = serializer.dumps(email, salt="password-reset-salt")
        return token

    async def verify_reset_password_token(self, token: str) -> User | None:
        serializer = URLSafeTimedSerializer(self.settings.MAIL_SECRET_KEY)
        try:
            email = serializer.loads(token, salt="password-reset-salt", max_age=600)
        except Exception as e:
            return None
        return await self.user_logic.get_user_by_email(email)

    async def send_reset_password_email(self, user: User):
        try:
            token = self.get_reset_password_token(email=user.email)
            reset_link = f"http://127.0.0.1:8000/auth/reset_password/{token}"

            subject = "Сброс пароля"
            body = f"""
            Здравствуйте, {user.username}!

            Для сброса пароля перейдите по следующей ссылке:
            {reset_link}

            Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.
            """

            message = MessageSchema(
                subject=subject,
                recipients=[user.email],
                body=body,
                subtype="plain",
            )

            fm = FastMail(mail_config)
            await fm.send_message(message)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail="Не удалось отправить письмо для сброса пароля. Обратитесь в поддержку.",
            )

    async def verify_email_confirmation_token(self, token: str) -> User | None:
        serializer = URLSafeTimedSerializer(self.settings.MAIL_SECRET_KEY)
        try:
            email = serializer.loads(token, salt="email-confirm-salt", max_age=3600)
        except Exception as e:
            return None

        return await self.user_logic.confirm_user_by_email(email)
