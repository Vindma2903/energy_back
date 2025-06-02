from pydantic import BaseModel, EmailStr


class UserLoginSchema(BaseModel):
    email: str
    password: str


class UserAuthSchema(BaseModel):
    user_id: int
    email: str


class UserAuthenticatedSchema(BaseModel):
    user_id: int
    username: str  # Добавлено
    email: str  # Добавлено
    access_token: str


class UserCreateSchema(BaseModel):
    username: str
    email: EmailStr  # Проверка, что это валидный email
    password: str


class UserUpdateSchema(BaseModel):
    name: str | None = None
    surname: str | None = None
    phone_number: str | None = None
    email: str | None = None


class ResetPasswordRequest(BaseModel):
    password: str


class UserStatusChangeSchema(BaseModel):
    user_id: int
    status: str
