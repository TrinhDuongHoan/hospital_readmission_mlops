import json
import os

import redis


REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))


class FeatureService:
    def __init__(self):
        self.client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True,
        )

    def save_prediction_log(self, key: str, value: dict) -> None:
        self.client.set(
            key,
            json.dumps(value),
        )

    def get_prediction_log(self, key: str):
        value = self.client.get(key)

        if value is None:
            return None

        return json.loads(value)


feature_service = FeatureService()