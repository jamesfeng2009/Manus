import pika
import json
import os
import time
import logging
from typing import Callable, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MessageStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


@dataclass
class PublishResult:
    success: bool
    message_id: str = ""
    error: str = ""


class RabbitMQClient:
    def __init__(self, config: dict = None):
        self.config = config or {}
        self._connection = None
        self._channel = None
        self._max_retries = 3
        self._retry_delay = 5

    def _get_connection_params(self) -> pika.ConnectionParameters:
        credentials = pika.PlainCredentials(
            self.config.get("username", os.getenv("RABBITMQ_USER", "guest")),
            self.config.get("password", os.getenv("RABBITMQ_PASS", "guest")),
        )
        return pika.ConnectionParameters(
            host=self.config.get("host", os.getenv("RABBITMQ_HOST", "localhost")),
            port=self.config.get("port", int(os.getenv("RABBITMQ_PORT", "5672"))),
            virtual_host=self.config.get("virtual_host", os.getenv("RABBITMQ_VHOST", "/")),
            credentials=credentials,
            heartbeat=30,
            blocked_connection_timeout=300,
        )

    def connect(self) -> bool:
        try:
            if self._connection and self._connection.is_open:
                return True

            params = self._get_connection_params()
            self._connection = pika.BlockingConnection(params)
            self._channel = self._connection.channel()
            self._channel.confirm_delivery()

            queue_name = self.config.get("queue_name", "plan_execute_tasks")
            self._channel.queue_declare(
                queue=queue_name,
                durable=True,
                arguments={
                    "x-message-ttl": 3600000,
                    "x-dead-letter-exchange": "",
                    "x-dead-letter-routing-key": f"{queue_name}_dlq",
                },
            )

            dlq_name = f"{queue_name}_dlq"
            self._channel.queue_declare(queue=dlq_name, durable=True)

            logger.info(f"RabbitMQ connected successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False

    def _ensure_connection(self):
        if not self._connection or not self._connection.is_open:
            self.connect()

    def publish(self, message: dict, retry: int = 0) -> PublishResult:
        try:
            self._ensure_connection()

            queue_name = self.config.get("queue_name", "plan_execute_tasks")
            message_id = message.get("message_id", f"msg_{time.time()}")

            properties = pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent,
                message_id=message_id,
                content_type="application/json",
            )

            def on_confirm(confirmation):
                pass

            self._channel.basic_publish(
                exchange="",
                routing_key=queue_name,
                body=json.dumps(message, ensure_ascii=False),
                properties=properties,
                mandatory=True,
            )

            return PublishResult(success=True, message_id=message_id)

        except pika.exceptions.UnroutableError as e:
            logger.error(f"Message was returned as unroutable: {e}")
            return PublishResult(success=False, error="Message unroutable")
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            if retry < self._max_retries:
                time.sleep(self._retry_delay)
                return self.publish(message, retry + 1)
            return PublishResult(success=False, error=str(e))

    def consume(self, callback: Callable[[dict], bool], queue_name: str = None):
        queue_name = queue_name or self.config.get("queue_name", "plan_execute_tasks")

        def on_message(channel, method, properties, body):
            try:
                message = json.loads(body)
                message_id = properties.message_id or message.get("message_id", "unknown")

                logger.info(f"Received message: {message_id}")

                success = callback(message)

                if success:
                    channel.basic_ack(delivery_tag=method.delivery_tag)
                    logger.info(f"Message {message_id} acknowledged")
                else:
                    channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                    logger.warning(f"Message {message_id} nack, requeued")

            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode message: {e}")
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        self._channel.basic_qos(prefetch_count=1)
        self._channel.basic_consume(queue=queue_name, on_message_callback=on_message)

        logger.info(f"Started consuming from queue: {queue_name}")
        self._channel.start_consuming()

    def close(self):
        if self._connection and self._connection.is_open:
            self._connection.close()
            logger.info("RabbitMQ connection closed")

    def get_queue_status(self) -> dict:
        try:
            self._ensure_connection()
            queue_name = self.config.get("queue_name", "plan_execute_tasks")
            queue = self._channel.queue_declare(queue=queue_name, passive=True)
            return {
                "message_count": queue.method.message_count,
                "consumer_count": queue.method.consumer_count,
            }
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            return {"error": str(e)}


_client: RabbitMQClient | None = None


def get_rabbitmq_client(config: dict = None) -> RabbitMQClient:
    global _client
    if _client is None:
        _client = RabbitMQClient(config)
    return _client
