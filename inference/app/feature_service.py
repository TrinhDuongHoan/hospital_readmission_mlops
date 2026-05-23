import json
import logging
import os

import redis


REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

logger = logging.getLogger(__name__)


class FeatureService:
    def __init__(self):
        self.client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True,
        )

    def save_prediction_log(self, key: str, value: dict) -> bool:
        try:
            self.client.set(
                key,
                json.dumps(value),
            )
        except redis.RedisError as exc:
            logger.warning("Could not write prediction cache to Redis: %s", exc)
            return False

        return True

    def get_prediction_log(self, key: str):
        try:
            value = self.client.get(key)
        except redis.RedisError as exc:
            logger.warning("Could not read prediction cache from Redis: %s", exc)
            return None

        if value is None:
            return None

        return json.loads(value)


feature_service = FeatureService()
