import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional
import aio_pika
from aio_pika import ExchangeType, IncomingMessage, Message
from app.core.config import settings

logger = logging.getLogger("rabbitmq-consumer")

# Topology Constants matching NestJS backend
EXCHANGE_PRIMARY = "meetingos.direct"
EXCHANGE_RETRY = "meetingos.retry.exchange"
EXCHANGE_DLX = "meetingos.dlx"

QUEUE_TRANSCRIPTION = "meetingos.transcription"
QUEUE_INTELLIGENCE = "meetingos.intelligence"
QUEUE_DOCUMENT = "meetingos.document"
QUEUE_RETRY = "meetingos.retry.queue"
QUEUE_DLQ = "meetingos.dlq"

ROUTING_KEY_TRANSCRIPTION = "job.transcription"
ROUTING_KEY_INTELLIGENCE = "job.intelligence"
ROUTING_KEY_DOCUMENT = "job.document"
ROUTING_KEY_DLQ = "dlq.job"

MAX_RETRIES = 3
RETRY_DELAY_MS = 10000  # 10 seconds backoff


class AsyncWorkerConsumer:
    """
    Enterprise-grade asynchronous RabbitMQ consumer powered by aio-pika.
    Features:
      - Resilient auto-reconnect backoff loop
      - Dual Dead-Letter Exchange (Retry Exchange with TTL + DLX for permanent failure)
      - Non-blocking async message consumption
      - Structured retry header tracking ('x-retry-count')
    """

    def __init__(self, amqp_url: str = settings.RABBITMQ_URL):
        self.amqp_url = amqp_url
        self.connection: Optional[aio_pika.RobustConnection] = None
        self.channel: Optional[aio_pika.RobustChannel] = None
        self.is_running = False
        self._consumer_task: Optional[asyncio.Task] = None

    async def start(self):
        """Starts the consumer background loop with resilient connection handling."""
        self.is_running = True
        self._consumer_task = asyncio.create_task(self._run_loop())
        logger.info(f"AI Worker consumer initialized for RabbitMQ at {self.amqp_url}")

    async def stop(self):
        """Gracefully closes AMQP channel and connection."""
        self.is_running = False
        if self._consumer_task:
            self._consumer_task.cancel()
        if self.channel and not self.channel.is_closed:
            await self.channel.close()
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
        logger.info("AI Worker consumer stopped gracefully.")

    async def _run_loop(self):
        """Continuous reconnection loop if broker is disconnected or restarting."""
        while self.is_running:
            try:
                logger.info(f"Connecting to RabbitMQ at {self.amqp_url}...")
                self.connection = await aio_pika.connect_robust(
                    self.amqp_url,
                    timeout=10,
                )
                self.channel = await self.connection.channel()
                await self.channel.set_qos(prefetch_count=5)

                # Assert topology matching backend definitions
                await self._assert_topology()

                logger.info("RabbitMQ topology asserted. Subscribing to work queues...")
                await self._setup_consumers()

                # Keep connection alive while running
                while self.is_running and not self.connection.is_closed:
                    await asyncio.sleep(2)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(
                    f"RabbitMQ connection lost or failed: {str(e)}. Reconnecting in 5s..."
                )
                await asyncio.sleep(5)

    async def _assert_topology(self):
        """Declares direct exchanges, primary queues, delayed retry queue, and DLQ."""
        if not self.channel:
            return

        # 1. Exchanges
        primary_exchange = await self.channel.declare_exchange(
            EXCHANGE_PRIMARY, ExchangeType.DIRECT, durable=True
        )
        retry_exchange = await self.channel.declare_exchange(
            EXCHANGE_RETRY, ExchangeType.DIRECT, durable=True
        )
        dlx_exchange = await self.channel.declare_exchange(
            EXCHANGE_DLX, ExchangeType.DIRECT, durable=True
        )

        # 2. Dead-Letter Queue (DLQ)
        dlq = await self.channel.declare_queue(QUEUE_DLQ, durable=True)
        await dlq.bind(dlx_exchange, routing_key=ROUTING_KEY_DLQ)
        await dlq.bind(dlx_exchange, routing_key=ROUTING_KEY_INTELLIGENCE)
        await dlq.bind(dlx_exchange, routing_key=ROUTING_KEY_TRANSCRIPTION)

        # 3. Delayed Retry Queue (Routes back to Primary Exchange after TTL expiry)
        retry_queue = await self.channel.declare_queue(
            QUEUE_RETRY,
            durable=True,
            arguments={
                "x-message-ttl": RETRY_DELAY_MS,
                "x-dead-letter-exchange": EXCHANGE_PRIMARY,
            },
        )
        await retry_queue.bind(retry_exchange, routing_key=ROUTING_KEY_INTELLIGENCE)
        await retry_queue.bind(retry_exchange, routing_key=ROUTING_KEY_TRANSCRIPTION)
        await retry_queue.bind(retry_exchange, routing_key=ROUTING_KEY_DOCUMENT)

        # 4. Primary Work Queues (Dead-letter points to Retry Exchange)
        queues_to_bind = [
            (QUEUE_INTELLIGENCE, ROUTING_KEY_INTELLIGENCE),
            (QUEUE_TRANSCRIPTION, ROUTING_KEY_TRANSCRIPTION),
            (QUEUE_DOCUMENT, ROUTING_KEY_DOCUMENT),
        ]

        for q_name, r_key in queues_to_bind:
            queue = await self.channel.declare_queue(
                q_name,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": EXCHANGE_RETRY,
                    "x-dead-letter-routing-key": r_key,
                },
            )
            await queue.bind(primary_exchange, routing_key=r_key)

    async def _setup_consumers(self):
        """Attaches handlers to primary queues."""
        if not self.channel:
            return

        intelligence_queue = await self.channel.get_queue(QUEUE_INTELLIGENCE)
        transcription_queue = await self.channel.get_queue(QUEUE_TRANSCRIPTION)

        await intelligence_queue.consume(
            lambda msg: self._process_message_with_retry(
                msg, self._handle_intelligence_job
            )
        )
        await transcription_queue.consume(
            lambda msg: self._process_message_with_retry(
                msg, self._handle_transcription_job
            )
        )
        logger.info(
            f"Active listeners subscribed to [{QUEUE_INTELLIGENCE}] & [{QUEUE_TRANSCRIPTION}]"
        )

    async def _process_message_with_retry(
        self,
        message: IncomingMessage,
        handler: Callable[[Dict[str, Any]], Any],
    ):
        """
        Executes handler within a structured retry envelope.
        - Increments 'x-retry-count' on failure.
        - Routes to Retry Exchange if retries < MAX_RETRIES.
        - Routes to DLX if retries >= MAX_RETRIES or on poison JSON payload.
        """
        headers = dict(message.headers or {})
        current_retries = int(headers.get("x-retry-count", 0))
        routing_key = message.routing_key or ROUTING_KEY_INTELLIGENCE

        # Parse JSON
        try:
            payload = json.loads(message.body.decode("utf-8"))
        except Exception as parse_err:
            logger.error(
                f"Poison message received (Invalid JSON): {str(parse_err)}. Routing directly to DLQ."
            )
            await self._send_to_dlq(
                message.body,
                routing_key,
                f"Invalid JSON: {str(parse_err)}",
                headers,
            )
            await message.ack()
            return

        try:
            # Process job
            logger.info(
                f"Processing job [{routing_key}] (Attempt {current_retries + 1}/{MAX_RETRIES}): {payload.get('id', 'unknown')}"
            )
            await handler(payload)
            await message.ack()
            logger.info(f"Job completed successfully: {payload.get('id', 'unknown')}")

        except Exception as process_err:
            logger.error(
                f"Error processing job [{routing_key}] attempt {current_retries + 1}: {str(process_err)}"
            )

            if current_retries + 1 >= MAX_RETRIES:
                logger.error(
                    f"Job exceeded max retries ({MAX_RETRIES}). Escalating to DLQ [{QUEUE_DLQ}]."
                )
                await self._send_to_dlq(
                    message.body,
                    routing_key,
                    f"Exceeded max retries ({MAX_RETRIES}): {str(process_err)}",
                    {**headers, "x-retry-count": current_retries + 1},
                )
                await message.ack()
            else:
                logger.warning(
                    f"Routing job to [{EXCHANGE_RETRY}] for {RETRY_DELAY_MS // 1000}s backoff delay."
                )
                await self._send_to_retry(
                    message.body,
                    routing_key,
                    current_retries + 1,
                    str(process_err),
                    headers,
                )
                await message.ack()

    async def _send_to_retry(
        self,
        body: bytes,
        routing_key: str,
        new_retry_count: int,
        last_error: str,
        existing_headers: Dict[str, Any],
    ):
        """Publishes failed task to the Retry Exchange with updated retry count header."""
        if not self.channel:
            return

        retry_exchange = await self.channel.get_exchange(EXCHANGE_RETRY)
        updated_headers = {
            **existing_headers,
            "x-retry-count": new_retry_count,
            "x-last-error": last_error,
            "x-original-routing-key": routing_key,
        }

        retry_msg = Message(
            body=body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
            headers=updated_headers,
        )
        await retry_exchange.publish(retry_msg, routing_key=routing_key)

    async def _send_to_dlq(
        self,
        body: bytes,
        routing_key: str,
        reason: str,
        existing_headers: Dict[str, Any],
    ):
        """Publishes dead-lettered message directly to the Dead-Letter Exchange (DLX)."""
        if not self.channel:
            return

        dlx_exchange = await self.channel.get_exchange(EXCHANGE_DLX)
        dlq_headers = {
            **existing_headers,
            "x-death-reason": reason,
            "x-original-routing-key": routing_key,
        }

        dlq_msg = Message(
            body=body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
            headers=dlq_headers,
        )
        await dlx_exchange.publish(dlq_msg, routing_key=routing_key)

    async def _handle_intelligence_job(self, payload: Dict[str, Any]):
        """Handler for meeting summary, action items, and intelligence extraction."""
        meeting_id = payload.get("meetingId") or payload.get("id")
        logger.info(f"AI Intelligence processing pipeline triggered for meeting: {meeting_id}")
        # Processing workflow hook (e.g. Gemini LLM summarization)
        await asyncio.sleep(0.5)

    async def _handle_transcription_job(self, payload: Dict[str, Any]):
        """Handler for audio transcription jobs."""
        meeting_id = payload.get("meetingId") or payload.get("id")
        logger.info(f"Audio transcription pipeline triggered for meeting: {meeting_id}")
        await asyncio.sleep(0.5)


worker_consumer = AsyncWorkerConsumer()
