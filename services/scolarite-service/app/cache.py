from __future__ import annotations

import json
from typing import Any

from fastapi.encoders import jsonable_encoder
from redis.exceptions import RedisError

from app.redis_client import redis_client


async def cache_get_json(key: str) -> Any | None:
    try:
        cached = await redis_client.get(key)
    except RedisError:
        return None
    if cached is None:
        return None
    return json.loads(cached)


async def cache_set_json(key: str, value: Any, ttl_seconds: int) -> None:
    try:
        await redis_client.set(key, json.dumps(jsonable_encoder(value)), ex=ttl_seconds)
    except RedisError:
        return


async def cache_delete(*keys: str) -> None:
    if not keys:
        return
    try:
        await redis_client.delete(*keys)
    except RedisError:
        return


async def cache_delete_pattern(pattern: str) -> None:
    try:
        keys = [key async for key in redis_client.scan_iter(match=pattern, count=100)]
        if keys:
            await redis_client.delete(*keys)
    except RedisError:
        return
