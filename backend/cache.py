import hashlib
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis.asyncio as aioredis
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = aioredis.from_url(url, decode_responses=True)
        logger.info("Redis cache connected: %s", url)
    except Exception as e:
        logger.warning("Redis unavailable (%s); caching disabled", e)
        _redis_client = None
    return _redis_client


def _make_key(features: dict) -> str:
    payload = json.dumps(features, sort_keys=True)
    return "pred:" + hashlib.sha256(payload.encode()).hexdigest()


async def get_cached_prediction(features: dict) -> Optional[dict]:
    r = _get_redis()
    if r is None:
        return None
    try:
        key = _make_key(features)
        raw = await r.get(key)
        if raw:
            logger.debug("Cache hit for key %s", key[:16])
            return json.loads(raw)
    except Exception as e:
        logger.warning("Cache get failed: %s", e)
    return None


async def set_cached_prediction(features: dict, value: dict, ttl: int = 300) -> None:
    r = _get_redis()
    if r is None:
        return
    try:
        key = _make_key(features)
        await r.setex(key, ttl, json.dumps(value))
    except Exception as e:
        logger.warning("Cache set failed: %s", e)
