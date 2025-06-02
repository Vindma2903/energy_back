import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from starlette import status
from starlette.responses import JSONResponse



from dependency import get_auth_service, get_user_logic, get_mail_service
from exceptions import UserNotFoundException, UserNotCorrectPasswordException, UserNotConfirmedByAdminException
from infrastructure.mail.service import MailService
from users.auth.service import AuthService
from users.logic import UserLogic
from users.schemas import UserLoginSchema, UserCreateSchema, ResetPasswordRequest
from dotenv import load_dotenv
import os
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from dependency import get_request_user_id
from fastapi import Response  # Добавил Response для `set_cookie`

# Создаём роутер для маршрутов аутентификации
router = APIRouter(prefix='/auth', tags=['auth'])

load_dotenv()

# Получение значений переменных
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default_secret_key")  # Значение по умолчанию, если переменной нет
JWT_ALGORITHM = os.getenv("JWT_DECODE_ALGORITHM", "HS256")

# Логгер для записи информационных сообщений
logger = logging.getLogger(__name__)




@router.post("/login", name="login_post")
async def login_post(
        request: Request,
        response: Response,  # Передаём Response в параметры
        data: UserLoginSchema,
        auth_service: AuthService = Depends(get_auth_service),
):
    """
    Обрабатывает вход пользователя.
    - Проверяет email и пароль.
    - Возвращает токен доступа и данные пользователя при успешной аутентификации.
    """
    try:
        user = await auth_service.login(email=data.email, password=data.password)
        access_token = user.access_token  # Получаем токен

        # Проверяем, есть ли user_id
        user_id = getattr(user, "user_id", None) or getattr(user, "id", None)
        if not user_id:
            raise HTTPException(status_code=500, detail="Ошибка: ID пользователя не найден")

        # 📌 **Правильная установка cookies**
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,  # Защита от XSS
            samesite="None",  # 🔥 ДОЛЖНО БЫТЬ `None`, иначе `cookies` не передаются с фронта
            secure=False,  # 🔥 `False` для localhost, `True` если HTTPS
            max_age=3600,  # Время жизни токена (1 час)
            expires=3600,  # Альтернативное время жизни
            path="/",  # Cookies доступны на всех страницах
        )

        return {
            "status": "authorized",
            "user": {
                "id": user_id,
                "username": user.username,
                "email": user.email,
            },
            "access_token": access_token,  # Дополнительно отправляем токен в JSON
        }

    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=e.detail)
    except UserNotCorrectPasswordException as e:
        raise HTTPException(status_code=404, detail=e.detail)
    except UserNotConfirmedByAdminException as e:
        raise HTTPException(status_code=403, detail=e.detail)


# Для извлечения токена из заголовков
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.get("/check", name="check_auth")
async def check_auth(
        request: Request,
        user_logic: UserLogic = Depends(get_user_logic),
        user_id: int = Depends(get_request_user_id),
):
    """
    Проверяет авторизацию пользователя и возвращает информацию о нём.
    """
    # 🔍 Логируем cookies
    print("🔎 Cookies в запросе:", request.cookies)

    if not user_id:
        print("❌ Ошибка: `user_id` отсутствует!")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Токен отсутствует или недействителен")

    # 🔍 Получаем пользователя по ID
    user = await user_logic.get_user_by_id(user_id=user_id)
    print("🔎 Данные пользователя:", user)

    if not user:
        print(f"❌ Ошибка: Пользователь с ID {user_id} не найден!")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    # ✅ Используем `is_admin`, а не `role`
    is_admin = user.is_admin
    role = "admin" if is_admin else "user"  # Определяем роль

    print(f"✅ Авторизация успешна: ID={user.id}, Username={user.username}, Role={role}, IsAdmin={is_admin}")

    return {
        "status": "authorized",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "status": user.status,
            "role": role,  # ✅ Теперь корректно передаём `role`
            "is_admin": is_admin
        },
    }






@router.get("/home", name="home_page")
async def home_page(token: str = Depends(oauth2_scheme)):
    """
    Защищённый маршрут для доступа к домашней странице.
    - Проверяет токен пользователя.
    - Возвращает доступ, если пользователь авторизован.

    :param token: Токен доступа из заголовков.
    :return: Сообщение о доступе к домашней странице или ошибка авторизации.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Не удалось проверить авторизацию",
            )
        return {"message": "Добро пожаловать на домашнюю страницу!", "user_id": user_id}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
        )

@router.post("/registration")
async def registration_post(
        data: UserCreateSchema,
        user_logic: UserLogic = Depends(get_user_logic),
        background_tasks: BackgroundTasks = BackgroundTasks(),
        mail_service: MailService = Depends(get_mail_service)
):
    """
    Регистрирует нового пользователя.
    - Проверяет наличие email в базе.
    - Создаёт пользователя и отправляет email с подтверждением.

    :param data: Данные для создания пользователя.
    :param user_logic: Логика работы с пользователями.
    :param background_tasks: Фоновые задачи.
    :param mail_service: Сервис отправки писем.
    :return: Сообщение о создании пользователя.
    """
    user = await user_logic.get_user_by_email(email=data.email)
    if user:
        logger.warning(f"Регистрация не удалась. Email {data.email} уже используется.")
        raise HTTPException(status_code=400, detail="Этот email уже используется.")
    new_user = await user_logic.create_user(
        UserCreateSchema(username=data.username, email=data.email, password=data.password))
    background_tasks.add_task(mail_service.send_confirmation_email, new_user)
    return {"message": f"user {new_user.email} created"}

@router.post("/recovery_password")
async def recovery_password_post(
        email: str,
        background_tasks: BackgroundTasks = BackgroundTasks(),
        mail_service: MailService = Depends(get_mail_service),
        user_logic: UserLogic = Depends(get_user_logic),
):
    """
    Восстанавливает пароль пользователя.
    - Отправляет письмо с инструкцией по восстановлению.

    :param email: Email пользователя.
    :param background_tasks: Фоновые задачи.
    :param mail_service: Сервис отправки писем.
    :param user_logic: Логика работы с пользователями.
    :return: Сообщение об успешной отправке или ошибка.
    """
    logger.info(f"Попытка восстановления пароля для email: {email}.")
    user = await user_logic.get_user_by_email(email=email)
    if user:
        logger.info(f"Письмо для восстановления пароля отправлено на {email}.")
        background_tasks.add_task(mail_service.send_reset_password_email, user)
        return {"message": f"Письмо для восстановления пароля отправлено на {email}"}
    logger.warning(f"Восстановление пароля не удалось. Пользователь с email {email} не найден.")
    raise HTTPException(status_code=400, detail="Пользователь с таким email не найден.")

@router.post("/reset_password/{token}")
async def reset_password_post(
        token: str,
        request: ResetPasswordRequest,
        mail_service: MailService = Depends(get_mail_service),
        user_logic: UserLogic = Depends(get_user_logic),
):
    """
    Сбрасывает пароль пользователя.
    - Проверяет токен восстановления.
    - Устанавливает новый пароль для пользователя.

    :param token: Токен восстановления пароля.
    :param request: Запрос с новым паролем.
    :param mail_service: Сервис отправки писем.
    :param user_logic: Логика работы с пользователями.
    :return: Сообщение об успешной смене пароля.
    """
    logger.info("Обработка POST-запроса на смену пароля.")
    user = await mail_service.verify_reset_password_token(token)
    if not user:
        logger.error("Токен восстановления пароля неверный или просрочен.")
        raise HTTPException(status_code=400, detail="Неверный или просроченный токен.")
    await user_logic.change_user_password(user_id=user.id, password=request.password)
    logger.info(f"Пароль пользователя {user.email} успешно изменён.")
    return {'message': f'Пароль пользователя {user.email} успешно изменён.'}

@router.post("/logout", name="logout")
async def logout(request: Request):
    """
    Выход пользователя из системы.
    - Удаляет токен доступа из сессии.

    :param request: Объект HTTP-запроса.
    :return: Сообщение об успешном выходе или об отсутствии активной сессии.
    """
    if "access_token" in request.session:
        request.session.pop("access_token")
        response = JSONResponse(
            {"message": "Logout successful"},
            status_code=200
        )
        response.delete_cookie("my_session")
        return response
    else:
        return JSONResponse(
            {"message": "No active session found"}, status_code=400
        )
