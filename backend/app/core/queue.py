from redis import Redis

from app.core.config import get_settings


SCENE_QUEUE_NAME = "scene_runs"


def get_redis_client() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url, decode_responses=True)

