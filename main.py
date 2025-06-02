from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import JSONResponse
import logging
from rabbit.producer import send_message  # Импортируем функцию для отправки сообщений
from rabbit.consumer import consume  # Импортируем функцию для обработки сообщений (если нужно)
import asyncio
from rabbit.schemas import MessageRequest  # Импортируем модель

# Импортируем роутеры
from admin.router import router as admin_router
from crm.clients.router import router as client_router
from users.auth.router import router as auth_router  # ✅ Роутер аутентификации
from crm.kanban.router import router as kanban_router

from connect_ai.router import router as connect_ai_router
from settings import Settings
from messages.router import send_to_rabbitmq
from messages.router import router as messages_router

# ✅ Создаем экземпляр FastAPI
app = FastAPI(openapi_url="/openapi.json", docs_url="/docs", redoc_url="/redoc")

# ✅ Загружаем настройки
settings = Settings()

# ✅ Подключаем маршруты
app.include_router(client_router)
app.include_router(auth_router)  # /auth маршруты (включая /home и /check)
app.include_router(admin_router)
app.include_router(kanban_router)
app.include_router(messages_router, prefix="/messages", tags=["Messages"])  # ✅ Подключаем роутер сообщений
app.include_router(messages_router)

app.include_router(connect_ai_router, prefix="/connect_ai", tags=["ConnectAI"])

# ✅ Middleware для разрешения CORS (должен быть первым!)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],  # Разрешенные заголовки
    allow_credentials=True,  # Разрешить отправку cookies/credentials
)

# ✅ Middleware для сессий
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    session_cookie="session",
)

# ✅ Логирование запросов
logger = logging.getLogger("uvicorn")
logging.basicConfig(level=logging.INFO)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"📥 Запрос: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"📤 Ответ: {response.status_code}")
    return response

# ✅ Пример маршрута для проверки работы сервера
@app.get("/")
async def read_root():
    return {"message": "Сервер работает!"}

# ✅ Проверка CORS
@app.get("/test-cors")
async def test_cors():
    response = JSONResponse(content={"message": "CORS работает!"})
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

# ✅ Пример маршрута для отправки сообщений в RabbitMQ

@app.post("/send-message/")
async def send_message_endpoint(data: MessageRequest):
    # Отправка сообщения пользователя в очередь RabbitMQ
    await send_to_rabbitmq(data.dict())
    return {"message": "Сообщение отправлено в RabbitMQ!"}

# ✅ Запускаем Consumer в фоновом режиме при старте приложения
@app.on_event("startup")
async def startup_event():
    # Запускаем обработку сообщений (consume) в фоновом режиме
    asyncio.create_task(consume())  # Запускаем consume асинхронно

