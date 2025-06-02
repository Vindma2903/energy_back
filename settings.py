import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv(".env")


class Settings(BaseSettings):
    DATABASE_NAME: str = os.getenv('DATABASE_NAME')
    DATABASE_HOST: str = os.getenv('DATABASE_HOST')
    DATABASE_USER: str = os.getenv('DATABASE_USER')
    DATABASE_PASSWORD: str = os.getenv('DATABASE_PASSWORD')
    DATABASE_PORT: str = os.getenv('DATABASE_PORT')

    SESSION_SECRET_KEY: str = os.getenv('SESSION_SECRET_KEY')

    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD")
    MAIL_FROM: str = os.getenv("MAIL_FROM")
    MAIL_PORT: str = os.getenv("MAIL_PORT")
    MAIL_SERVER: str = os.getenv("MAIL_SERVER")
    MAIL_USE_TLS: bool = False
    MAIL_SSL_TLS: bool = os.getenv("MAIL_SSL_TLS", "true").lower() in ("true", "1", "yes")
    MAIL_USE_CREDENTIALS: bool = os.getenv("MAIL_USE_CREDENTIALS", "true").lower() in ("true", "1", "yes")
    MAIL_SECRET_KEY: str = os.getenv('SECRET_KEY', 'secret1')

    JWT_SECRET_KEY: str = os.getenv('JWT_SECRET_KEY')
    JWT_DECODE_ALGORITHM: str = os.getenv('JWT_DECODE_ALGORITHM')


    @property
    def db_path(self):
        return f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
