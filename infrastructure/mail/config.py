from fastapi_mail import ConnectionConfig

from exceptions import MailConfigError
from settings import Settings

settings = Settings()

try:
    mail_config = ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
        USE_CREDENTIALS=settings.MAIL_USE_CREDENTIALS,
        MAIL_STARTTLS=settings.MAIL_USE_TLS
    )

except Exception as e:
    raise MailConfigError
