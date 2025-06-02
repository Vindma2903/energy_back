import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager  # Управляет жизненным циклом FastAPI
from fastapi import status
from main import app  # Импорт приложения FastAPI
from dependency import get_user_logic, get_request_user_id  # Импортируем зависимости для авторизации
from unittest.mock import AsyncMock

# Определяем простой класс для фиктивного пользователя (успешный сценарий)
class FakeUser:
    def __init__(self, id, username, email, status, is_admin):
        self.id = id
        self.username = username
        self.email = email
        self.status = status
        self.is_admin = is_admin

# Фикстура для тестового клиента FastAPI (без запуска сервера)
@pytest_asyncio.fixture
async def client():
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

# Фикстура для успешного сценария проверки авторизации.
# Здесь переопределяем зависимости:
# - get_user_logic: возвращает мок, у которого метод get_user_by_id возвращает фиктивного пользователя.
# - get_request_user_id: возвращает корректный user_id (например, 1).
@pytest.fixture
def override_check_auth_success():
    fake_logic = AsyncMock()
    fake_user = FakeUser(
        id=1,
        username="testuser",
        email="test@example.com",
        status="active",
        is_admin=False  # Для пользователя без прав администратора
    )
    fake_logic.get_user_by_id.return_value = fake_user
    app.dependency_overrides[get_user_logic] = lambda: fake_logic
    app.dependency_overrides[get_request_user_id] = lambda: 1
    yield fake_logic
    app.dependency_overrides.pop(get_user_logic, None)
    app.dependency_overrides.pop(get_request_user_id, None)

# Фикстура для сценария, когда user_id отсутствует.
@pytest.fixture
def override_check_auth_missing_user_id():
    # Переопределяем только get_request_user_id, возвращая None
    app.dependency_overrides[get_request_user_id] = lambda: None
    yield
    app.dependency_overrides.pop(get_request_user_id, None)

# Фикстура для сценария, когда пользователь не найден.
@pytest.fixture
def override_check_auth_user_not_found():
    fake_logic = AsyncMock()
    fake_logic.get_user_by_id.return_value = None  # Пользователь не найден
    app.dependency_overrides[get_user_logic] = lambda: fake_logic
    app.dependency_overrides[get_request_user_id] = lambda: 999  # Некоторый user_id
    yield fake_logic
    app.dependency_overrides.pop(get_user_logic, None)
    app.dependency_overrides.pop(get_request_user_id, None)

# Тест успешной авторизации
@pytest.mark.asyncio
async def test_check_auth_success(client, override_check_auth_success):
    response = await client.get("/auth/check")
    expected_json = {
        "status": "authorized",
        "user": {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "status": "active",
            "role": "user",  # Поскольку is_admin=False
            "is_admin": False,
        },
    }
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == expected_json
    print("✅ Тест 'Проверка авторизации успешна' пройден! (Получены корректные данные пользователя)")

# Тест, когда отсутствует user_id (должен возвращаться 403)
@pytest.mark.asyncio
async def test_check_auth_missing_user_id(client, override_check_auth_missing_user_id):
    response = await client.get("/auth/check")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Токен отсутствует или недействителен"
    print("✅ Тест 'Отсутствует user_id' пройден! (Возвращается 403, если user_id отсутствует)")

# Тест, когда пользователь не найден (должен возвращаться 404)
@pytest.mark.asyncio
async def test_check_auth_user_not_found(client, override_check_auth_user_not_found):
    response = await client.get("/auth/check")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Пользователь не найден"
    print("✅ Тест 'Пользователь не найден' пройден! (Возвращается 404, если пользователь не найден)")


# ❌ Тест: Ошибка выхода (нет активной сессии)
@pytest.mark.asyncio
async def test_logout_no_active_session(client):
    # Пытаемся выйти без `access_token`
    response = await client.post("/auth/logout", cookies={"my_session": "test_session"}, json={})

    # Проверяем, что вернулся статус 400
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"message": "No active session found"}

    print("✅ Тест 'Выход без активной сессии' пройден!")