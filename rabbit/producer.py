import aio_pika
import logging
import asyncio

logger = logging.getLogger("uvicorn")
logging.basicConfig(level=logging.DEBUG)


async def send_message(message: str):
    try:
        connection = await aio_pika.connect_robust("amqp://localhost/")
        async with connection:
            channel = await connection.channel()

            # Используем пассивное объявление (только подключение к существующей очереди)
            try:
                queue = await channel.declare_queue(
                    "my_queue",
                    passive=True  # Ключевое изменение!
                )
            except aio_pika.exceptions.ChannelClosed as e:
                logger.error(f"Очередь не существует: {e}")
                return

            logger.debug(f"Отправка сообщения: {message}")
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=message.encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key='my_queue'
            )
            logger.debug("Сообщение отправлено")
    except Exception as e:
        logger.error(f"Ошибка: {e}")


async def main():
    await send_message("Тестовое сообщение")


if __name__ == "__main__":
    asyncio.run(main())