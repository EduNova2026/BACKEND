# pyright: reportUnknownMemberType=false

from redis.asyncio import Redis

from .config import settings


redis_client: Redis = Redis.from_url(settings.redis_url, decode_responses=True)


async def get_redis() -> Redis:
    return redis_client


async def close_redis() -> None:
    await redis_client.aclose()
