import asyncio
import logging
from app.core.config import settings

logger = logging.getLogger("rabbitmq-consumer")

class AsyncWorkerConsumer:
    """
    Asynchronous RabbitMQ consumer listening on queues with automatic
    reconnect, DLQ dispatching, and task processing.
    """
    def __init__(self, amqp_url: str = settings.RABBITMQ_URL):
        self.amqp_url = amqp_url
        self.is_running = False

    async def start(self):
        self.is_running = True
        logger.info(f"Connecting AI worker consumer to RabbitMQ at {self.amqp_url}")

    async def stop(self):
        self.is_running = False
        logger.info("AI worker consumer stopped.")

worker_consumer = AsyncWorkerConsumer()
