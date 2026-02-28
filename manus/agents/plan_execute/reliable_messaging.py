import redis
import json
import os
import time
import logging
from typing import Optional
from contextlib import contextmanager
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MessageState:
    message_id: str
    status: str
    processed_at: float = 0
    error: str = ""


class ReliableMessaging:
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._client = None
        self._lock_timeout = 300
        self._dedup_ttl = 86400

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
        return self._client

    def is_duplicate(self, message_id: str) -> bool:
        try:
            key = f"msg:dedup:{message_id}"
            exists = self.client.exists(key)
            if exists:
                logger.info(f"Duplicate message detected: {message_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to check duplicate: {e}")
            return False

    def mark_processing(self, message_id: str) -> bool:
        try:
            key = f"msg:dedup:{message_id}"
            self.client.setex(key, self._dedup_ttl, "processing")
            return True
        except Exception as e:
            logger.error(f"Failed to mark processing: {e}")
            return False

    def mark_completed(self, message_id: str):
        try:
            key = f"msg:dedup:{message_id}"
            self.client.setex(key, self._dedup_ttl, "completed")
        except Exception as e:
            logger.error(f"Failed to mark completed: {e}")

    def mark_failed(self, message_id: str, error: str = ""):
        try:
            key = f"msg:dedup:{message_id}"
            self.client.setex(key, self._dedup_ttl, f"failed:{error}")
        except Exception as e:
            logger.error(f"Failed to mark failed: {e}")

    @contextmanager
    def distributed_lock(self, lock_key: str, timeout: int = None):
        lock_timeout = timeout or self._lock_timeout
        lock_id = f"{lock_key}:{os.getpid()}"
        acquired = False

        try:
            acquired = self.client.set(
                f"lock:{lock_key}",
                lock_id,
                nx=True,
                ex=lock_timeout,
            )

            if acquired:
                logger.debug(f"Acquired lock: {lock_key}")
                yield True
            else:
                logger.debug(f"Failed to acquire lock: {lock_key}")
                yield False

        except Exception as e:
            logger.error(f"Lock error: {e}")
            yield False
        finally:
            if acquired:
                try:
                    if self.client.get(f"lock:{lock_key}") == lock_id:
                        self.client.delete(f"lock:{lock_key}")
                except Exception as e:
                    logger.error(f"Failed to release lock: {e}")

    def acquire_step_lock(self, plan_id: str, step_index: int, worker_id: str, timeout: int = None) -> bool:
        lock_key = f"plan:{plan_id}:step:{step_index}"
        lock_value = f"{worker_id}:{time.time()}"
        lock_timeout = timeout or self._lock_timeout

        try:
            result = self.client.set(
                lock_key,
                lock_value,
                nx=True,
                ex=lock_timeout,
            )
            if result:
                logger.info(f"Worker {worker_id} acquired lock for step {step_index}")
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to acquire step lock: {e}")
            return False

    def release_step_lock(self, plan_id: str, step_index: int, worker_id: str):
        lock_key = f"plan:{plan_id}:step:{step_index}"

        try:
            self.client.delete(lock_key)
            logger.info(f"Released lock for step {step_index}")
        except Exception as e:
            logger.error(f"Failed to release step lock: {e}")

    def get_processing_tasks(self) -> list[str]:
        try:
            keys = self.client.keys("msg:dedup:*")
            processing_keys = []
            for key in keys:
                status = self.client.get(key)
                if status == "processing":
                    msg_id = key.replace("msg:dedup:", "")
                    processing_keys.append(msg_id)
            return processing_keys
        except Exception as e:
            logger.error(f"Failed to get processing tasks: {e}")
            return []

    def save_message_state(self, message_id: str, state: MessageState):
        try:
            key = f"msg:state:{message_id}"
            data = {
                "message_id": state.message_id,
                "status": state.status,
                "processed_at": state.processed_at,
                "error": state.error,
            }
            self.client.setex(key, self._dedup_ttl, json.dumps(data))
        except Exception as e:
            logger.error(f"Failed to save message state: {e}")

    def get_message_state(self, message_id: str) -> Optional[MessageState]:
        try:
            key = f"msg:state:{message_id}"
            data = self.client.get(key)
            if data:
                obj = json.loads(data)
                return MessageState(**obj)
            return None
        except Exception as e:
            logger.error(f"Failed to get message state: {e}")
            return None


_reliable_messaging: ReliableMessaging | None = None


def get_reliable_messaging(redis_url: str = None) -> ReliableMessaging:
    global _reliable_messaging
    if _reliable_messaging is None:
        _reliable_messaging = ReliableMessaging(redis_url)
    return _reliable_messaging
