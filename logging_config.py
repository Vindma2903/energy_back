import logging

# Конфигурация логов
logging.basicConfig(
    level=logging.INFO,  # Отображать INFO и выше (WARNING, ERROR, CRITICAL)
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),  # Логировать в файл
        logging.StreamHandler()  # Логировать в консоль
    ]
)

# Экспортируем логгер для других модулей
logger = logging.getLogger("messages_crud")
