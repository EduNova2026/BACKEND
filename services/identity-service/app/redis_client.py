# pyright: reportUnknownMemberType=false

from redis.asyncio import ConnectionPool, Redis

from .config import settings


redis_pool = ConnectionPool.from_url(
    settings.redis_url,
    decode_responses=True,
    health_check_interval=30,
    max_connections=50,
    socket_connect_timeout=2,
    socket_timeout=2,
)
redis_client: Redis = Redis(connection_pool=redis_pool)


async def get_redis() -> Redis:
    return redis_client


async def close_redis() -> None:
    await redis_client.aclose(close_connection_pool=True)
