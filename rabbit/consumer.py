import aio_pika
import logging
import asyncio

logger = logging.getLogger("uvicorn")
logging.basicConfig(level=logging.INFO)


async def callback(message: aio_pika.IncomingMessage):
    try:
        async with message.process():
            body = message.body.decode()
            logger.info(f"📩 Получено: {body}")
            logger.info("✅ Обработано")
    except Exception as e:
        logger.error(f"⚠️ Ошибка: {e}")
        await message.reject(requeue=False)


async def consume():
    logger.info("🔄 Запуск Consumer")
    try:
        connection = await aio_pika.connect_robust("amqp://localhost/")
        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=1)

            # Создаем очередь, если её нет
            queue = await channel.declare_queue(
                'my_queue',
                durable=True,
                arguments={
                    'x-message-ttl': 86400000,  # Время жизни сообщений (1 день)
                    'x-max-length': 10000       # Максимальное количество сообщений в очереди
                }
            )

            await queue.consume(callback)
            logger.info("👂 Ожидание сообщений...")
            await asyncio.Future()  # Бесконечное ожидание сообщений

    except Exception as e:
        logger.error(f"🔥 Ошибка: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(consume())
    except KeyboardInterrupt:
        logger.info("🛑 Остановлен")
