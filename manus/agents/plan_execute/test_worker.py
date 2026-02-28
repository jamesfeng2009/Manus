import os
import sys
import asyncio
import signal
import logging

from manus.agents.plan_execute.messaging import get_rabbitmq_client
from manus.agents.plan_execute.reliable_messaging import get_reliable_messaging
from manus.agents.plan_execute.repository import PlanExecuteRepository

logger = logging.getLogger(__name__)


class SimpleWorker:
    def __init__(self):
        self.worker_id = os.getenv("WORKER_ID", f"worker-{os.getpid()}")
        self.repository = PlanExecuteRepository()
        self.rabbitmq = get_rabbitmq_client()
        self.reliable = get_reliable_messaging()
        self._running = False

    def _handle_shutdown(self, signum, frame):
        logger.info(f"Worker {self.worker_id} received shutdown signal")
        self._running = False

    def _process_message(self, message: dict) -> bool:
        message_id = message.get("message_id", "unknown")
        task_id = message.get("task_id", "unknown")

        try:
            if self.reliable.is_duplicate(message_id):
                logger.warning(f"Duplicate message {message_id}, skipping")
                return True

            self.reliable.mark_processing(message_id)

            user_input = message.get("payload", {}).get("original_input", "")

            logger.info(f"Worker {self.worker_id} processing task {task_id}: {user_input}")

            result = self.repository.update_plan_status_by_task_id(
                task_id=task_id,
                status="completed",
                progress=100.0,
                final_result=f"Processed by {self.worker_id}",
            )
            logger.info(f"Update result for {task_id}: {result}")

            self.reliable.mark_completed(message_id)

            logger.info(f"Task {task_id} completed by {self.worker_id}")
            return True

        except Exception as e:
            logger.error(f"Error processing message {message_id}: {e}")
            self.reliable.mark_failed(message_id, str(e))
            return False

    def start(self):
        logger.info(f"Worker {self.worker_id} starting...")

        self._running = True

        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        if not self.rabbitmq.connect():
            logger.error("Failed to connect to RabbitMQ")
            return

        logger.info(f"Worker {self.worker_id} consuming messages...")

        self.rabbitmq.consume(self._process_message)

    def stop(self):
        logger.info(f"Worker {self.worker_id} stopping...")
        self._running = False
        self.rabbitmq.close()
        logger.info(f"Worker {self.worker_id} stopped")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    worker = SimpleWorker()

    try:
        worker.start()
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    finally:
        worker.stop()


if __name__ == "__main__":
    main()
