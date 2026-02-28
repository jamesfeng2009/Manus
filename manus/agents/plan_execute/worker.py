import os
import sys
import asyncio
import signal
import logging
import time
from typing import Any

from manus.agents.plan_execute.messaging import get_rabbitmq_client
from manus.agents.plan_execute.reliable_messaging import get_reliable_messaging
from manus.agents.plan_execute.repository import PlanExecuteRepository
from manus.agents.plan_execute.engine import PlanExecuteEngine
from manus.agents.plan_execute.config import PlanExecuteConfig

logger = logging.getLogger(__name__)


class PlanExecuteWorker:
    def __init__(self):
        self.worker_id = os.getenv("WORKER_ID", f"worker-{os.getpid()}")
        self.batch_size = int(os.getenv("BATCH_SIZE", "5"))
        self.flush_interval = int(os.getenv("FLUSH_INTERVAL", "30"))

        self.repository = PlanExecuteRepository()
        self.rabbitmq = get_rabbitmq_client()
        self.reliable = get_reliable_messaging()

        self._buffer = []
        self._running = False
        self._flush_task = None

        self.config = PlanExecuteConfig()
        self.engine = PlanExecuteEngine(config=self.config)

    def _handle_shutdown(self, signum, frame):
        logger.info(f"Worker {self.worker_id} received shutdown signal")
        self._running = False

    async def _process_message(self, message: dict) -> bool:
        message_id = message.get("message_id", "unknown")
        task_id = message.get("task_id", "unknown")

        try:
            if self.reliable.is_duplicate(message_id):
                logger.warning(f"Duplicate message {message_id}, skipping")
                return True

            self.reliable.mark_processing(message_id)

            user_input = message.get("payload", {}).get("original_input", "")
            plan_json = message.get("payload", {}).get("plan_json")
            config_dict = message.get("payload", {}).get("config", {})

            if not user_input:
                logger.error(f"No user_input in message {message_id}")
                self.reliable.mark_failed(message_id, "No user_input")
                return True

            plan_exec = self.repository.create_plan(
                task_id=task_id,
                user_id=message.get("user_id", "default"),
                original_input=user_input,
                plan_json=plan_json,
                mode=config_dict.get("mode", "sequential"),
                max_iterations=config_dict.get("max_iterations", 3),
                enable_verification=config_dict.get("enable_verification", True),
            )

            logger.info(f"Worker {self.worker_id} processing task {task_id}")

            self.repository.update_plan_status(
                plan_exec.id,
                status="running",
                progress=0.0,
            )

            result = await self.engine.execute(
                user_input=user_input,
                task_id=task_id,
                user_id=message.get("user_id", "default"),
                context={"plan_id": plan_exec.id},
            )

            if result.status == "completed":
                self.repository.update_plan_status(
                    plan_exec.id,
                    status="completed",
                    progress=100.0,
                    final_result=result.final_result,
                )
            else:
                self.repository.update_plan_status(
                    plan_exec.id,
                    status=result.status,
                    error=result.error,
                )

            self.reliable.mark_completed(message_id)

            self._buffer.append({
                "message_id": message_id,
                "task_id": task_id,
                "status": "completed",
                "worker_id": self.worker_id,
                "timestamp": time.time(),
            })

            logger.info(f"Task {task_id} completed by {self.worker_id}")
            return True

        except Exception as e:
            logger.error(f"Error processing message {message_id}: {e}")
            self.reliable.mark_failed(message_id, str(e))
            return False

    async def _periodic_flush(self):
        while self._running:
            await asyncio.sleep(self.flush_interval)
            await self._flush_buffer()

    async def _flush_buffer(self):
        if not self._buffer:
            return

        logger.info(f"Flushing {len(self._buffer)} buffered items")
        self._buffer.clear()

    async def start(self):
        logger.info(f"Worker {self.worker_id} starting...")

        self._running = True

        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        if not self.rabbitmq.connect():
            logger.error("Failed to connect to RabbitMQ")
            return

        self._flush_task = asyncio.create_task(self._periodic_flush())

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self.rabbitmq.consume,
            self._process_message,
        )

    async def stop(self):
        logger.info(f"Worker {self.worker_id} stopping...")
        self._running = False

        if self._flush_task:
            self._flush_task.cancel()

        await self._flush_buffer()

        self.rabbitmq.close()
        logger.info(f"Worker {self.worker_id} stopped")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    worker = PlanExecuteWorker()

    try:
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    finally:
        asyncio.run(worker.stop())


if __name__ == "__main__":
    main()
